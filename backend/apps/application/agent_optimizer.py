"""智能体对话评价与自动优化引擎。

对话结束后，自动分析对话质量，生成评价和优化建议，
包括改进的系统提示词，用户可一键应用。
"""
import json
import logging
from typing import Dict, Optional

from apps.application.models import Agent, AgentConversation, AgentEvaluation, AgentMessage
from apps.model_provider.llm_adapter import chat_completion

logger = logging.getLogger(__name__)


EVALUATION_PROMPT = """你是一位专业的 AI 助手质量评估专家。请评估以下智能体对话的质量，并给出优化建议。

## 智能体信息
- 名称：{agent_name}
- 角色：{agent_role}
- 系统提示词：
{system_prompt}

## 对话内容
{conversation}

## 评估维度
请从以下维度评估（1-5分）：
1. 相关性：回答是否与用户问题相关
2. 准确性：回答内容是否准确、有无错误
3. 完整性：回答是否完整、有无遗漏
4. 工具使用：是否合理使用工具，工具调用是否正确
5. 表达质量：语言是否清晰、有条理

## 输出格式
严格按照以下 JSON 格式输出：
{{
  "score": 综合评分(1-5),
  "relevance_score": 相关性评分,
  "accuracy_score": 准确性评分,
  "completeness_score": 完整性评分,
  "feedback": "评价内容，指出优点和不足",
  "suggestion": "具体的优化建议",
  "suggested_prompt": "优化后的系统提示词（如果需要改进），不需要改进则留空"
}}
"""


def build_conversation_text(conversation: AgentConversation, max_messages: int = 20) -> str:
    """构建对话文本。"""
    messages = conversation.messages.all().order_by('create_time')[:max_messages]
    lines = []
    for m in messages:
        role_label = {'user': '用户', 'assistant': '助手', 'tool': '工具'}.get(m.role, m.role)
        content = m.content[:500]
        if m.reasoning:
            content = f"[思考: {m.reasoning[:200]}]\n{content}"
        lines.append(f"【{role_label}】\n{content}")
    return "\n\n".join(lines)


def evaluate_conversation(conversation: AgentConversation, user_id: int = None) -> Optional[AgentEvaluation]:
    """自动评价对话，生成优化建议。"""
    agent = conversation.agent

    # 至少需要 2 条消息（一问一答）
    msg_count = conversation.messages.count()
    if msg_count < 2:
        return None

    conv_text = build_conversation_text(conversation)
    prompt = EVALUATION_PROMPT.format(
        agent_name=agent.name,
        agent_role=agent.role or '未设定',
        system_prompt=agent.system_prompt[:1000],
        conversation=conv_text,
    )

    try:
        response = chat_completion(
            [{"role": "user", "content": prompt}],
            temperature=0.3, max_tokens=2000, user_id=user_id,
        )
        # 解析 JSON
        result = _parse_json(response)
        if not result:
            return None

        evaluation = AgentEvaluation.objects.create(
            conversation=conversation,
            agent=agent,
            score=result.get('score', 3),
            relevance_score=result.get('relevance_score', 3),
            accuracy_score=result.get('accuracy_score', 3),
            completeness_score=result.get('completeness_score', 3),
            feedback=result.get('feedback', ''),
            suggestion=result.get('suggestion', ''),
            suggested_prompt=result.get('suggested_prompt', ''),
        )
        return evaluation
    except Exception as e:
        logger.error("对话评价失败: conversation=%s, error=%s", conversation.id, e, exc_info=True)
        return None


def apply_optimization(evaluation: AgentEvaluation) -> bool:
    """应用优化建议，更新智能体的系统提示词。"""
    if not evaluation.suggested_prompt or evaluation.applied:
        return False
    agent = evaluation.agent
    agent.system_prompt = evaluation.suggested_prompt
    agent.save(update_fields=['system_prompt', 'update_time'])
    evaluation.applied = True
    evaluation.save(update_fields=['applied'])
    return True


def _parse_json(text: str) -> Optional[Dict]:
    """从 LLM 输出中解析 JSON。"""
    import re
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None
