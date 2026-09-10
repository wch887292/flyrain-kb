"""智能体执行引擎：ReAct 模式（思考→工具调用→观察→回答）。

工具调用协议：
- 系统提示词中定义可用工具列表和输出格式
- LLM 输出 JSON：{"thought": "思考", "action": "工具名|final", "action_input": "输入", "answer": "最终答案"}
- 解析后执行工具（HTTP 插件 / 知识库检索 / 代码执行），将观察结果加入上下文
- 循环直到 LLM 输出 final 或达到最大轮次
"""
import json
import re
import logging
from typing import List, Dict, Optional, Tuple, Generator

from apps.application.models import Agent, Plugin
from apps.application.code_interpreter import execute_code, format_code_result
from apps.application.mcp_client import get_all_tools as get_mcp_tools, call_mcp_tool
from apps.knowledge.search import hybrid_search
from apps.model_provider.llm_adapter import chat_completion

logger = logging.getLogger(__name__)


def _build_tool_definitions(agent: Agent) -> List[Dict]:
    """从插件、MCP、子智能体和内置能力生成工具定义列表。"""
    tools = []
    for plugin in agent.tools.filter(is_active=True):
        tools.append({
            'name': f'tool_{plugin.id}',
            'display_name': plugin.name,
            'description': plugin.description or f'调用工具：{plugin.name}',
            'plugin_id': plugin.id,
        })
    # MCP 工具
    try:
        mcp_tools = get_mcp_tools(agent)
        tools.extend(mcp_tools)
    except Exception as e:
        logger.warning("MCP 工具获取失败: agent=%s, error=%s", agent.id, e)
    # 子智能体工具
    for sub in agent.sub_agents.filter(is_active=True):
        tools.append({
            'name': f'agent_{sub.id}',
            'display_name': f'智能体: {sub.name}',
            'description': f'调用子智能体「{sub.name}」处理任务。角色：{sub.role or "未设定"}。输入：任务描述',
            'sub_agent_id': sub.id,
            'sub_agent': True,
        })
    # 知识库检索作为内置工具
    if agent.kbs.exists():
        tools.append({
            'name': 'search_knowledge',
            'display_name': '知识库检索',
            'description': '从关联知识库中检索相关信息。输入：检索关键词',
            'builtin': True,
        })
    # Code Interpreter 作为内置工具
    if agent.enable_code_interpreter:
        tools.append({
            'name': 'code_interpreter',
            'display_name': '代码执行',
            'description': '执行 Python 代码进行计算、数据分析、图表生成。输入：完整的 Python 代码，支持 print 输出和 matplotlib 图表。注意：禁止文件操作、网络请求、导入 os/sys/subprocess 等模块。',
            'builtin': True,
            'code': True,
        })
    return tools


def _build_system_prompt(agent: Agent, tools: List[Dict]) -> str:
    """构建系统提示词，包含角色、工具定义和输出格式。"""
    tool_descriptions = []
    for t in tools:
        tool_descriptions.append(f"- {t['name']} ({t['display_name']}): {t['description']}")

    tools_text = '\n'.join(tool_descriptions) if tool_descriptions else '（无可用工具）'

    role_text = f"你的角色是：{agent.role}\n" if agent.role else ""

    code_hint = ""
    if agent.enable_code_interpreter:
        code_hint = """
## 代码执行提示
当需要计算、数据分析、生成图表时，使用 code_interpreter 工具。
- 输入完整的 Python 代码
- 用 print() 输出结果
- 用 matplotlib.pyplot 生成图表（会自动保存并展示）
- 可用库：numpy, pandas, matplotlib, math, statistics, random, datetime, json, re, collections, itertools
- 禁止：文件操作、网络请求、导入 os/sys/subprocess/socket 等模块
"""

    return f"""{agent.system_prompt}

{role_text}
## 可用工具
{tools_text}
{code_hint}
## 输出格式
你必须严格按照以下 JSON 格式输出，不要输出其他内容：

如果需要调用工具：
{{"thought": "你的思考过程", "action": "工具名称", "action_input": "调用工具的输入参数"}}

如果已经有足够信息，可以直接回答：
{{"thought": "你的思考过程", "action": "final", "answer": "你的最终回答"}}

注意：
1. 每次只调用一个工具
2. 工具返回结果后，根据结果决定继续调用工具还是给出最终答案
3. 最终答案要完整、准确，基于工具返回的信息
4. 使用 code_interpreter 时，action_input 必须是完整可执行的 Python 代码
"""


def _parse_llm_output(text: str) -> Dict:
    """解析 LLM 输出的 JSON。尝试多种方式提取 JSON。"""
    text = text.strip()
    # 直接尝试解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 提取 ```json ... ``` 块
    match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # 提取 ```python ... ``` 块（代码执行场景）
    match = re.search(r'```python\s*(.*?)\s*```', text, re.DOTALL)
    if match:
        return {'thought': '', 'action': 'code_interpreter', 'action_input': match.group(1)}
    # 提取第一个 { 到最后一个 }
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    # 无法解析，当作最终答案
    return {'thought': '', 'action': 'final', 'answer': text}


def _execute_tool(agent: Agent, tool_name: str, action_input: str,
                  tools: List[Dict]) -> Tuple[str, str, List[str]]:
    """执行工具，返回 (工具显示名, 观察结果, 图片base64列表)。"""
    tool = next((t for t in tools if t['name'] == tool_name), None)
    if not tool:
        return tool_name, f'错误：工具 {tool_name} 不存在', []

    # 子智能体调用
    if tool.get('sub_agent'):
        try:
            sub_agent = Agent.objects.get(id=tool['sub_agent_id'], is_active=True)
            result = _run_sub_agent(sub_agent, action_input)
            return tool['display_name'], result[:3000], []
        except Agent.DoesNotExist:
            return tool['display_name'], '子智能体不存在或未启用', []
        except Exception as e:
            return tool['display_name'], f'子智能体调用失败: {str(e)}', []

    # MCP 工具
    if tool.get('mcp'):
        try:
            # 尝试解析 action_input 为 JSON 参数
            try:
                arguments = json.loads(action_input)
                if not isinstance(arguments, dict):
                    arguments = {'input': action_input}
            except (json.JSONDecodeError, TypeError):
                arguments = {'input': action_input}
            result = call_mcp_tool(tool['server_id'], tool['mcp_tool_name'], arguments)
            return tool['display_name'], result, []
        except Exception as e:
            return tool['display_name'], f'MCP 工具调用失败: {str(e)}', []

    if tool.get('builtin') and tool_name == 'search_knowledge':
        # 内置知识库检索
        results = []
        for kb in agent.kbs.all():
            try:
                kb_results = hybrid_search(kb, action_input, top_k=3, vector_weight=0.7)
                for r in kb_results:
                    results.append({
                        'content': r['paragraph'].content,
                        'doc_name': r['doc_name'],
                        'page_no': r['page_no'],
                    })
            except Exception as e:
                logger.warning("知识库检索失败: kb=%s, error=%s", kb.id, e)
        if not results:
            return '知识库检索', '未检索到相关信息', []
        obs = '\n\n'.join([
            f"[来源《{r['doc_name']}》第{r['page_no']}页]\n{r['content']}" for r in results[:5]
        ])
        return '知识库检索', obs, []

    if tool.get('code') and tool_name == 'code_interpreter':
        # 代码执行
        result = execute_code(action_input, timeout=30)
        obs = format_code_result(result)
        images = result.get('images', [])
        return '代码执行', obs, images

    # HTTP 插件工具
    try:
        plugin = Plugin.objects.get(id=tool.get('plugin_id'))
        config = plugin.config or {}
        url = config.get('url', '')
        method = (config.get('method', 'POST') or 'POST').upper()
        headers = config.get('headers', {}) or {}
        body_template = config.get('body_template', '{{input}}')
        timeout = config.get('timeout', 30)

        body = body_template.replace('{{input}}', action_input)
        try:
            json_body = json.loads(body)
        except (json.JSONDecodeError, TypeError):
            json_body = body

        import requests as http_requests
        if method == 'GET':
            resp = http_requests.get(url, headers=headers, params={'input': action_input}, timeout=timeout)
        else:
            resp = http_requests.request(method, url, headers=headers, json=json_body, timeout=timeout)
        resp.raise_for_status()
        try:
            data = resp.json()
            result = json.dumps(data, ensure_ascii=False, indent=2)
        except Exception:
            result = resp.text
        return tool['display_name'], result[:2000], []
    except Exception as e:
        return tool.get('display_name', tool_name), f'工具调用失败：{str(e)}', []


def _run_sub_agent(sub_agent: Agent, query: str) -> str:
    """执行子智能体，返回最终答案文本（非流式）。"""
    sub_tools = _build_tool_definitions(sub_agent)
    system_prompt = _build_system_prompt(sub_agent, sub_tools)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query},
    ]

    for iteration in range(min(sub_agent.max_iterations, 3)):
        response = chat_completion(
            messages, temperature=sub_agent.temperature,
            max_tokens=sub_agent.max_tokens,
        )
        parsed = _parse_llm_output(response)
        action = parsed.get('action', 'final')
        action_input = parsed.get('action_input', '')
        answer = parsed.get('answer', '')

        if action == 'final' or answer:
            return answer or response

        # 子智能体调用工具
        tool_name, observation, _ = _execute_tool(sub_agent, action, action_input, sub_tools)
        messages.append({"role": "assistant", "content": response})
        messages.append({"role": "user",
                         "content": f"工具 {tool_name} 返回结果：\n{observation}\n\n请根据结果继续。"})

    return "（子智能体达到最大轮次）"


def run_agent(agent: Agent, query: str, history: Optional[List[Dict]] = None,
              user_id: Optional[int] = None) -> Generator[Dict, None, None]:
    """执行智能体，生成器逐块产出事件。

    产出事件类型：
    - {"type": "reasoning", "content": "思考内容"}
    - {"type": "tool_call", "tool": "工具名", "input": "输入", "code": true/false}
    - {"type": "tool_result", "tool": "工具名", "result": "结果", "images": [...]}
    - {"type": "token", "content": "最终答案增量"}
    - {"type": "done", "answer": "完整答案"}
    - {"type": "error", "message": "错误信息"}
    """
    tools = _build_tool_definitions(agent)
    system_prompt = _build_system_prompt(agent, tools)

    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": query})

    full_answer = ""
    tool_call_history = []

    for iteration in range(agent.max_iterations):
        try:
            # 调用 LLM（非流式，获取完整思考）
            response = chat_completion(
                messages, temperature=agent.temperature, max_tokens=agent.max_tokens,
                user_id=user_id,
            )
            parsed = _parse_llm_output(response)
            thought = parsed.get('thought', '')
            action = parsed.get('action', 'final')
            action_input = parsed.get('action_input', '')
            answer = parsed.get('answer', '')

            if thought:
                yield {"type": "reasoning", "content": thought, "iteration": iteration + 1}

            if action == 'final' or answer:
                # 最终答案，流式输出
                full_answer = answer or response
                # 模拟流式输出（按字符分块）
                for i in range(0, len(full_answer), 20):
                    yield {"type": "token", "content": full_answer[i:i+20]}
                yield {"type": "done", "answer": full_answer, "iterations": iteration + 1}
                return

            # 工具调用
            tool_display = action
            is_code = False
            for t in tools:
                if t['name'] == action:
                    tool_display = t['display_name']
                    is_code = t.get('code', False)
                    break

            yield {"type": "tool_call", "tool": tool_display, "input": action_input,
                   "code": is_code, "iteration": iteration + 1}

            # 执行工具
            tool_name, observation, images = _execute_tool(agent, action, action_input, tools)
            yield {"type": "tool_result", "tool": tool_name, "result": observation,
                   "images": images, "iteration": iteration + 1}

            # 将工具调用和结果加入上下文
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user",
                             "content": f"工具 {tool_name} 返回结果：\n{observation}\n\n请根据结果继续。如果信息足够，请输出最终答案。"})
            tool_call_history.append({"tool": tool_name, "input": action_input, "result": observation})

        except Exception as e:
            logger.error("智能体执行失败: agent=%s, iteration=%s, error=%s",
                         agent.id, iteration, e, exc_info=True)
            yield {"type": "error", "message": str(e)}
            return

    # 达到最大轮次，输出最后一次的回答
    yield {"type": "done", "answer": full_answer or "（已达到最大推理轮次）",
           "iterations": agent.max_iterations, "truncated": True}
