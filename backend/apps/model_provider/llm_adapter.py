"""统一大模型调用层：兼容 OpenAI 协议。
优先读取数据库 ModelProvider 配置（is_default），回退到环境变量默认值。
自动记录每次调用的 Token 消耗、耗时和状态到 ModelUsage。
"""
import os
import time
import logging
from typing import Dict, List, Iterator, Optional

from django.conf import settings

logger = logging.getLogger(__name__)


def _provider_from_db(p_type: str) -> Dict:
    from apps.model_provider.models import ModelProvider
    p = ModelProvider.objects.filter(type=p_type, is_default=True).first()
    if p:
        return {
            'base_url': p.base_url,
            'api_key': p.api_key,
            'model': p.model_name,
            'dimensions': p.dimensions,
        }
    return {}


def get_llm_config() -> Dict:
    p = _provider_from_db('llm')
    return {
        'base_url': p.get('base_url') or getattr(settings, 'DEFAULT_LLM_BASE_URL'),
        'api_key': p.get('api_key') or getattr(settings, 'DEFAULT_LLM_API_KEY'),
        'model': p.get('model') or getattr(settings, 'DEFAULT_LLM_MODEL'),
    }


def get_embedding_config() -> Dict:
    p = _provider_from_db('embedding')
    return {
        'base_url': p.get('base_url') or getattr(settings, 'DEFAULT_LLM_BASE_URL'),
        'api_key': p.get('api_key') or getattr(settings, 'DEFAULT_LLM_API_KEY'),
        'model': p.get('model') or getattr(settings, 'DEFAULT_EMBEDDING_MODEL'),
        'dimensions': p.get('dimensions') or getattr(settings, 'DEFAULT_EMBEDDING_DIM', 1024),
    }


def _client(base_url: str, api_key: str):
    from openai import OpenAI
    return OpenAI(api_key=api_key, base_url=base_url)


def _record_usage(model_type: str, model_name: str, prompt_tokens: int,
                  completion_tokens: int, total_tokens: int, duration_ms: float,
                  status: str = 'success', error_msg: str = '',
                  user_id: Optional[int] = None, app_id: Optional[int] = None):
    """记录模型调用到 ModelUsage。"""
    try:
        from apps.model_provider.models import ModelUsage
        ModelUsage.objects.create(
            user_id=user_id,
            app_id=app_id,
            model_type=model_type,
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            duration_ms=duration_ms,
            status=status,
            error_msg=error_msg[:500] if error_msg else '',
        )
    except Exception as e:
        logger.warning("记录 ModelUsage 失败: %s", e)


def chat_completion(messages: List[Dict], temperature: float = 0.7,
                    max_tokens: int = 1024, user_id: Optional[int] = None,
                    app_id: Optional[int] = None) -> str:
    """非流式对话，返回完整文本。"""
    cfg = get_llm_config()
    client = _client(cfg['base_url'], cfg['api_key'])
    start = time.time()
    try:
        resp = client.chat.completions.create(
            model=cfg['model'],
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )
        duration = (time.time() - start) * 1000
        usage = getattr(resp, 'usage', None)
        _record_usage(
            'llm', cfg['model'],
            usage.prompt_tokens if usage else 0,
            usage.completion_tokens if usage else 0,
            usage.total_tokens if usage else 0,
            duration, 'success', '', user_id, app_id
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        duration = (time.time() - start) * 1000
        _record_usage('llm', cfg['model'], 0, 0, 0, duration, 'failed', str(e), user_id, app_id)
        logger.error("LLM 调用失败: model=%s, error=%s", cfg['model'], e, exc_info=True)
        raise


def chat_completion_stream(messages: List[Dict], temperature: float = 0.7,
                           max_tokens: int = 1024, user_id: Optional[int] = None,
                           app_id: Optional[int] = None) -> Iterator[str]:
    """流式对话，逐块产出文本增量。"""
    cfg = get_llm_config()
    client = _client(cfg['base_url'], cfg['api_key'])
    start = time.time()
    prompt_tokens = 0
    completion_tokens = 0
    try:
        stream = client.chat.completions.create(
            model=cfg['model'],
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            stream_options={"include_usage": True},
        )
        for chunk in stream:
            if chunk.usage:
                prompt_tokens = chunk.usage.prompt_tokens or 0
                completion_tokens = chunk.usage.completion_tokens or 0
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content
        duration = (time.time() - start) * 1000
        _record_usage(
            'llm', cfg['model'], prompt_tokens, completion_tokens,
            prompt_tokens + completion_tokens, duration, 'success', '', user_id, app_id
        )
    except Exception as e:
        duration = (time.time() - start) * 1000
        _record_usage('llm', cfg['model'], prompt_tokens, completion_tokens,
                      prompt_tokens + completion_tokens, duration, 'failed', str(e), user_id, app_id)
        logger.error("LLM 流式调用失败: model=%s, error=%s", cfg['model'], e, exc_info=True)
        raise


def embed_texts(texts: List[str], user_id: Optional[int] = None,
                 app_id: Optional[int] = None) -> List[List[float]]:
    """批量向量化，返回与输入等长的向量列表。"""
    cfg = get_embedding_config()
    client = _client(cfg['base_url'], cfg['api_key'])
    start = time.time()
    try:
        resp = client.embeddings.create(model=cfg['model'], input=texts)
        duration = (time.time() - start) * 1000
        usage = getattr(resp, 'usage', None)
        total = usage.total_tokens if usage else 0
        _record_usage(
            'embedding', cfg['model'], total, 0, total,
            duration, 'success', '', user_id, app_id
        )
        return [item.embedding for item in resp.data]
    except Exception as e:
        duration = (time.time() - start) * 1000
        _record_usage('embedding', cfg['model'], 0, 0, 0, duration, 'failed', str(e), user_id, app_id)
        logger.error("Embedding 调用失败: model=%s, error=%s", cfg['model'], e, exc_info=True)
        raise


# ============================================================
#  限流工具：基于 Redis 的用户级调用频率限制
# ============================================================

class RateLimiter:
    """简单的滑动窗口限流（基于 Redis）。"""

    def __init__(self, prefix: str, max_calls: int = 10, window_seconds: int = 60):
        self.prefix = prefix
        self.max_calls = max_calls
        self.window_seconds = window_seconds

    def _get_redis(self):
        import redis
        from django.conf import settings
        url = getattr(settings, 'CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0')
        return redis.from_url(url)

    def allow(self, key: str) -> bool:
        """检查是否允许调用，允许则计数+1。"""
        try:
            r = self._get_redis()
            redis_key = f"ratelimit:{self.prefix}:{key}"
            current = r.incr(redis_key)
            if current == 1:
                r.expire(redis_key, self.window_seconds)
            return current <= self.max_calls
        except Exception as e:
            logger.warning("限流检查失败（放行）: %s", e)
            return True


chat_limiter = RateLimiter('chat', max_calls=20, window_seconds=60)
embedding_limiter = RateLimiter('embedding', max_calls=50, window_seconds=60)


# ============================================================
#  视觉理解：支持图片输入的多模态 LLM 调用
# ============================================================

def get_vision_config() -> Optional[Dict]:
    """获取支持视觉理解的模型配置，没有则返回 None。"""
    from apps.model_provider.models import ModelProvider
    p = ModelProvider.objects.filter(type='llm', supports_vision=True, is_default=True).first()
    if not p:
        p = ModelProvider.objects.filter(type='llm', supports_vision=True).first()
    if p:
        return {
            'base_url': p.base_url,
            'api_key': p.api_key,
            'model': p.model_name,
        }
    return None


def vision_completion(image_bytes: bytes,
                      prompt: str = "请详细描述这张图片的内容，包括文字、图表、物体等所有可见信息。",
                      max_tokens: int = 1024, user_id: Optional[int] = None) -> Optional[str]:
    """调用支持视觉的 LLM 理解图片内容。没有视觉模型时返回 None。"""
    import base64
    cfg = get_vision_config()
    if not cfg:
        return None

    start = time.time()
    try:
        img_b64 = base64.b64encode(image_bytes).decode('utf-8')
        if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
            mime = 'image/png'
        elif image_bytes[:3] == b'\xff\xd8\xff':
            mime = 'image/jpeg'
        elif image_bytes[:6] in (b'GIF87a', b'GIF89a'):
            mime = 'image/gif'
        else:
            mime = 'image/png'

        client = _client(cfg['base_url'], cfg['api_key'])
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b64}"}},
            ],
        }]
        resp = client.chat.completions.create(
            model=cfg['model'], messages=messages, max_tokens=max_tokens, temperature=0.3,
        )
        duration = (time.time() - start) * 1000
        usage = getattr(resp, 'usage', None)
        _record_usage(
            'llm', cfg['model'],
            usage.prompt_tokens if usage else 0,
            usage.completion_tokens if usage else 0,
            usage.total_tokens if usage else 0,
            duration, 'success', '', user_id
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        duration = (time.time() - start) * 1000
        _record_usage('llm', cfg.get('model', 'vision'), 0, 0, 0, duration, 'failed', str(e), user_id)
        logger.warning("视觉理解失败: %s", e)
        return None
