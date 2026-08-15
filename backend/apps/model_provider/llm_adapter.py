"""统一大模型调用层：兼容 OpenAI 协议。
优先读取数据库 ModelProvider 配置（is_default），回退到环境变量默认值。
"""
import os
from typing import Dict, List, Iterator

from django.conf import settings


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


def chat_completion(messages: List[Dict], temperature: float = 0.7,
                    max_tokens: int = 1024) -> str:
    """非流式对话，返回完整文本。"""
    cfg = get_llm_config()
    client = _client(cfg['base_url'], cfg['api_key'])
    resp = client.chat.completions.create(
        model=cfg['model'],
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=False,
    )
    return resp.choices[0].message.content or ""


def chat_completion_stream(messages: List[Dict], temperature: float = 0.7,
                           max_tokens: int = 1024) -> Iterator[str]:
    """流式对话，逐块产出文本增量。"""
    cfg = get_llm_config()
    client = _client(cfg['base_url'], cfg['api_key'])
    stream = client.chat.completions.create(
        model=cfg['model'],
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta and delta.content:
            yield delta.content


def embed_texts(texts: List[str]) -> List[List[float]]:
    """批量向量化，返回与输入等长的向量列表。"""
    cfg = get_embedding_config()
    client = _client(cfg['base_url'], cfg['api_key'])
    # OpenAI 批量接口
    resp = client.embeddings.create(model=cfg['model'], input=texts)
    return [item.embedding for item in resp.data]
