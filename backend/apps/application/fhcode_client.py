"""fhcode 底层执行引擎 API 客户端。

职责：
- MaxKB（flyrain-kb）作为上层应用，通过本客户端调用 fhcode 底层架构的执行能力。
- 封装「提交任务 → 轮询状态 → 获取结果」全流程，对 agent_engine 暴露同步接口。

fhcode API 鉴权（三层中的应用层）：
1. Bearer Token：Authorization: Bearer <FH_WEB_TOKEN>
2. 写请求（POST/PUT/PATCH/DELETE）还需 HMAC-SHA256 请求签名（防篡改/防重放）：
   - x-fh-ts    毫秒时间戳（±5 分钟窗口）
   - x-fh-nonce 随机数（12 字节 hex）
   - x-fh-sig   HMAC-SHA256(secret, f"{ts}|{nonce}|{bodyRaw}") 的 hex
   - secret 取 fhcode 侧 FH_SIGN_SECRET；未配置签名密钥时回退用 Token。

fhcode API：
- POST /api/tasks          提交任务
- GET  /api/tasks/:id      查询任务状态与结果
- POST /api/tasks/:id/stop 停止任务

任务状态：queued（排队）→ running（执行中）→ done（完成）/ failed（失败）

环境变量：
- FHCODE_BASE_URL：    fhcode 服务地址（默认 http://127.0.0.1:8080）
- FHCODE_TOKEN：       访问令牌（FH_WEB_TOKEN）
- FHCODE_SIGN_SECRET： 写请求签名密钥（FH_SIGN_SECRET，可选，缺省回退 Token）
- FHCODE_TIMEOUT：     单次任务最大等待秒数（默认 300）
- FHCODE_AGENT_TYPE：  默认智能体类型（可选：write-code / fix-code / exec-command）
"""
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from typing import Dict, Optional

import requests

logger = logging.getLogger(__name__)

# 任务终态
_TERMINAL_STATUSES = {'done', 'failed'}
# 可识别的智能体类型
_AGENT_TYPES = {'write-code', 'fix-code', 'exec-command', 'code-review', 'general'}


class FhcodeError(Exception):
    """fhcode 调用异常。"""


class FhcodeNotConfigured(FhcodeError):
    """fhcode 未配置（未设置 FHCODE_TOKEN）。"""


class FhcodeTaskFailed(FhcodeError):
    """fhcode 任务执行失败。"""


class FhcodeTimeout(FhcodeError):
    """fhcode 任务等待超时。"""


def _base_url() -> str:
    return os.environ.get('FHCODE_BASE_URL', 'http://127.0.0.1:8080').rstrip('/')


def _token() -> str:
    token = os.environ.get('FHCODE_TOKEN', '').strip()
    if not token:
        raise FhcodeNotConfigured(
            '未配置 FHCODE_TOKEN 环境变量，无法调用 fhcode 底层服务'
        )
    return token


def _sign_secret() -> str:
    """签名密钥：优先 FH_SIGN_SECRET，回退 Token（与服务端逻辑一致）。"""
    return os.environ.get('FHCODE_SIGN_SECRET', '').strip() or _token()


def _base_headers() -> Dict[str, str]:
    return {
        'Authorization': f'Bearer {_token()}',
        'Content-Type': 'application/json',
    }


def _sign_headers(body_raw: str) -> Dict[str, str]:
    """为写请求生成 Bearer + 签名头。"""
    ts = str(int(time.time() * 1000))
    nonce = secrets.token_hex(12)
    message = f'{ts}|{nonce}|{body_raw}'.encode('utf-8')
    sig = hmac.new(_sign_secret().encode('utf-8'), message, hashlib.sha256).hexdigest()
    return {
        'Authorization': f'Bearer {_token()}',
        'Content-Type': 'application/json',
        'x-fh-ts': ts,
        'x-fh-nonce': nonce,
        'x-fh-sig': sig,
    }


def _request(method: str, path: str, payload: Optional[Dict] = None,
             timeout: float = 15.0) -> requests.Response:
    """统一请求封装：GET 仅 Bearer；写请求附加 HMAC 签名。"""
    url = f'{_base_url()}{path}'
    method = method.upper()
    try:
        if method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            # 序列化 body，签名串与实际发送体必须完全一致
            body_raw = json.dumps(payload or {}, ensure_ascii=False)
            resp = requests.request(
                method, url,
                headers=_sign_headers(body_raw),
                data=body_raw.encode('utf-8'),
                timeout=timeout,
            )
        else:
            resp = requests.request(
                method, url,
                headers=_base_headers(),
                timeout=timeout,
            )
    except requests.RequestException as e:
        raise FhcodeError(f'连接 fhcode 失败: {e}') from e
    return resp


def _raise_for_status(resp: requests.Response, action: str) -> None:
    """统一错误处理。"""
    if resp.status_code in (401, 403):
        try:
            detail = (resp.json() or {}).get('error', '')
        except Exception:
            detail = resp.text[:200]
        raise FhcodeError(
            f'fhcode 鉴权失败（HTTP {resp.status_code}）{detail}。'
            '请检查 FHCODE_TOKEN 与 FHCODE_SIGN_SECRET（写请求）是否正确'
        )
    if not resp.ok:
        raise FhcodeError(f'fhcode {action}失败（HTTP {resp.status_code}）: {resp.text[:500]}')


def is_configured() -> bool:
    """fhcode 是否已配置（用于 Agent 工具注册判断）。"""
    return bool(os.environ.get('FHCODE_TOKEN', '').strip())


def health_check(timeout: float = 5.0) -> bool:
    """健康检查：fhcode 服务是否可达。"""
    try:
        resp = requests.get(
            f'{_base_url()}/api/health',
            headers=_base_headers(),
            timeout=timeout,
        )
        return resp.status_code == 200
    except FhcodeNotConfigured:
        return False
    except requests.RequestException as e:
        logger.warning('fhcode 健康检查失败: %s', e)
        return False


def submit_task(goal: str,
                agent_type: Optional[str] = None,
                permissions: Optional[Dict] = None,
                workspace_dir: Optional[str] = None,
                model_id: Optional[str] = None,
                timeout: float = 15.0) -> str:
    """提交任务到 fhcode，返回任务 ID。

    :param goal: 任务目标（自然语言描述）
    :param agent_type: 智能体类型（write-code/fix-code/exec-command）
    :param permissions: 权限配置（如 {"allowShell": false}）
    :param workspace_dir: 工作目录
    :param model_id: 模型 ID
    :return: 任务 ID
    """
    payload: Dict[str, object] = {'goal': goal}
    if agent_type:
        if agent_type not in _AGENT_TYPES:
            logger.warning('未知 fhcode agent_type: %s，将使用默认类型', agent_type)
        payload['agentType'] = agent_type
    if permissions:
        payload['permissions'] = permissions
    if workspace_dir:
        payload['workspaceDir'] = workspace_dir
    if model_id:
        payload['modelId'] = model_id

    resp = _request('POST', '/api/tasks', payload, timeout=timeout)
    _raise_for_status(resp, '任务提交')

    data = resp.json()
    task = data.get('task') or {}
    task_id = task.get('id')
    if not task_id:
        raise FhcodeError(f'fhcode 未返回任务 ID: {json.dumps(data, ensure_ascii=False)[:500]}')

    logger.info('fhcode 任务已提交: id=%s, goal=%s', task_id, goal[:80])
    return task_id


def get_task(task_id: str, timeout: float = 10.0) -> Dict:
    """查询任务状态与结果。"""
    resp = _request('GET', f'/api/tasks/{task_id}', timeout=timeout)
    if resp.status_code == 404:
        raise FhcodeError(f'fhcode 任务不存在: {task_id}')
    _raise_for_status(resp, '查询任务')
    return (resp.json() or {}).get('task') or {}


def wait_for_task(task_id: str,
                  timeout: Optional[float] = None,
                  poll_interval: float = 2.0) -> Dict:
    """轮询等待任务到达终态（done/failed）。

    :param task_id: 任务 ID
    :param timeout: 最大等待秒数（默认取 FHCODE_TIMEOUT 或 300）
    :param poll_interval: 轮询间隔秒数
    """
    if timeout is None:
        timeout = float(os.environ.get('FHCODE_TIMEOUT', '300'))

    deadline = time.time() + timeout
    last_status = ''
    while time.time() < deadline:
        task = get_task(task_id)
        status = task.get('status', '')
        if status != last_status:
            logger.info('fhcode 任务状态: id=%s status=%s', task_id, status)
            last_status = status

        if status in _TERMINAL_STATUSES:
            return task

        time.sleep(poll_interval)

    raise FhcodeTimeout(f'fhcode 任务 {task_id} 等待超时（{timeout}s）')


def run_task(goal: str,
             agent_type: Optional[str] = None,
             permissions: Optional[Dict] = None,
             workspace_dir: Optional[str] = None,
             timeout: Optional[float] = None) -> str:
    """一步到位：提交任务并等待完成，返回最终答案文本。

    供 agent_engine 的工具执行直接调用。
    """
    # 未显式指定类型时，从环境变量取默认类型
    if agent_type is None:
        agent_type = os.environ.get('FHCODE_AGENT_TYPE', '').strip() or None

    task_id = submit_task(
        goal, agent_type=agent_type,
        permissions=permissions, workspace_dir=workspace_dir,
    )
    task = wait_for_task(task_id, timeout=timeout)

    status = task.get('status')
    if status == 'failed':
        err = task.get('error') or '未知错误'
        raise FhcodeTaskFailed(f'fhcode 任务执行失败: {err}')

    result = task.get('result') or {}
    answer = result.get('finalAnswer') or ''
    if not answer:
        # 兜底：从对话中提取最后一条助手消息
        for msg in reversed(task.get('conversation') or []):
            if msg.get('role') == 'assistant' and msg.get('content'):
                answer = msg['content']
                break
    if not answer:
        answer = f'fhcode 任务已完成（{task_id}），但未返回文本结果。'

    # 附加执行摘要（迭代轮数、成本）
    iterations = result.get('iterations')
    cost = result.get('costUsd')
    meta_parts = []
    if iterations is not None:
        meta_parts.append(f'迭代 {iterations} 轮')
    if cost:
        meta_parts.append(f'成本 ${cost:.4f}')
    if meta_parts:
        answer = f'{answer}\n\n（fhcode 执行摘要：{"，".join(meta_parts)}，任务ID {task_id}）'
    return answer


def stop_task(task_id: str) -> bool:
    """停止任务。"""
    try:
        resp = _request('POST', f'/api/tasks/{task_id}/stop', {})
        return resp.status_code == 200
    except FhcodeError as e:
        logger.warning('停止 fhcode 任务失败: %s', e)
        return False
