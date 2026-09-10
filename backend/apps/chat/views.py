import json
import uuid
import logging
import io
import os

from django.http import StreamingHttpResponse, HttpResponse
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.application.models import Application
from apps.chat.models import ChatMessage
from apps.chat.serializers import ChatRequestSerializer, ChatHistorySerializer
from apps.common.utils import get_request_tenant, ok, fail
from apps.knowledge.search import hybrid_search
from apps.model_provider.llm_adapter import chat_completion_stream, chat_limiter

logger = logging.getLogger(__name__)


def _build_context(app, query, top_k=3, max_refs=6):
    refs = []
    seen = set()
    vector_weight = getattr(app, 'vector_weight', 0.7)
    for kb in app.kbs.all():
        try:
            results = hybrid_search(kb, query, top_k=top_k, vector_weight=vector_weight)
        except Exception as e:
            logger.warning("对话检索失败: app=%s, kb=%s, error=%s", app.id, kb.id, e)
            results = []
        for r in results:
            content = r['paragraph'].content.strip()
            key = content[:60]
            if key in seen:
                continue
            seen.add(key)
            refs.append({
                'content': content,
                'doc_name': r['doc_name'],
                'page_no': r['page_no'],
            })
            if len(refs) >= max_refs:
                break
        if len(refs) >= max_refs:
            break
    return refs


def _format_context(refs):
    if not refs:
        return "（未检索到相关知识库内容）"
    lines = []
    for i, r in enumerate(refs, 1):
        page = f" 第{r['page_no']}页" if r['page_no'] else ""
        lines.append(f"[参考{i}] 来源《{r['doc_name']}》{page}：\n{r['content']}")
    return "\n\n".join(lines)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chat(request):
    s = ChatRequestSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    data = s.validated_data
    try:
        app = Application.objects.get(id=data['app_id'])
    except Application.DoesNotExist:
        return fail('应用不存在', code=404)
    tenant = get_request_tenant(request)
    if tenant and app.tenant_id != tenant.id:
        return fail('无权限', code=403)
    if not chat_limiter.allow(str(request.user.id)):
        return fail('调用过于频繁，请稍后再试（限制 20 次/分钟）', code=429)
    session_id = data.get('session_id') or str(uuid.uuid4())
    query = data['query']
    ChatMessage.objects.create(session_id=session_id, app=app,
                               user=request.user, role='user', content=query)
    refs = _build_context(app, query)
    context_text = _format_context(refs)
    messages = [
        {"role": "system", "content": app.system_prompt},
        {"role": "system", "content": f"以下是可供参考的知识库资料：\n{context_text}"},
        {"role": "user", "content": query},
    ]
    def event(payload):
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
    def generator():
        answer = []
        try:
            for chunk in chat_completion_stream(
                messages, temperature=app.temperature, max_tokens=app.max_tokens,
                user_id=request.user.id, app_id=app.id
            ):
                answer.append(chunk)
                yield event({"type": "token", "content": chunk})
            full = "".join(answer)
            assistant_msg = ChatMessage.objects.create(session_id=session_id, app=app,
                                       user=request.user, role='assistant', content=full)
            yield event({
                "type": "done", "message_id": assistant_msg.id, "session_id": session_id,
                "sources": [{"doc_name": r['doc_name'], "page_no": r['page_no']} for r in refs],
            })
        except Exception as e:
            logger.error("对话生成失败: app=%s, session=%s, error=%s", app.id, session_id, e, exc_info=True)
            yield event({"type": "error", "message": str(e)})
    return StreamingHttpResponse(generator(), content_type='text/event-stream')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def history(request):
    session_id = request.query_params.get('session_id')
    if not session_id:
        return fail('session_id 必填', code=400)
    msgs = ChatMessage.objects.filter(session_id=session_id).order_by('create_time')
    return Response(ChatHistorySerializer(msgs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_session(request):
    """导出会话为 Markdown 文件。"""
    session_id = request.query_params.get('session_id')
    if not session_id:
        return fail('session_id 必填', code=400)
    msgs = ChatMessage.objects.filter(session_id=session_id, user=request.user).order_by('create_time')
    if not msgs.exists():
        return fail('会话不存在或无权限', code=404)
    app_name = msgs.first().app.name if msgs.first().app else '对话'
    lines = [f'# 对话导出：{app_name}', '',
             f'> 会话ID：{session_id}',
             f'> 导出时间：{timezone.now().strftime("%Y-%m-%d %H:%M:%S")}',
             f'> 消息数：{msgs.count()}', '', '---', '']
    for msg in msgs:
        role_label = '用户' if msg.role == 'user' else '助手'
        lines.append(f'## {role_label}')
        lines.append('')
        lines.append(msg.content)
        lines.append('')
        if msg.role == 'assistant' and msg.feedback:
            fb = '有用' if msg.feedback == 'like' else '无用'
            lines.append(f'*用户反馈：{fb}*')
            if msg.feedback_comment:
                lines.append(f'*备注：{msg.feedback_comment}*')
            lines.append('')
        lines.append('---')
        lines.append('')
    md_content = '\n'.join(lines)
    response = HttpResponse(md_content, content_type='text/markdown; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="chat_{session_id[:8]}.md"'
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_pdf(request):
    """导出会话为 PDF 文件。query: session_id"""
    session_id = request.query_params.get('session_id')
    if not session_id:
        return fail('session_id 必填', code=400)
    msgs = ChatMessage.objects.filter(session_id=session_id, user=request.user).order_by('create_time')
    if not msgs.exists():
        return fail('会话不存在或无权限', code=404)
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        font_name = 'Helvetica'
        for fp in [r'C:\Windows\Fonts\msyh.ttc', r'C:\Windows\Fonts\simhei.ttf',
                   '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc']:
            if os.path.exists(fp):
                try:
                    pdfmetrics.registerFont(TTFont('ChineseFont', fp))
                    font_name = 'ChineseFont'
                    break
                except Exception:
                    continue
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                                 topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('TCN', parent=styles['Title'], fontName=font_name, fontSize=18, spaceAfter=12)
        meta_style = ParagraphStyle('MCN', parent=styles['Normal'], fontName=font_name, fontSize=10, textColor=colors.grey)
        body_style = ParagraphStyle('BCN', parent=styles['Normal'], fontName=font_name, fontSize=11, spaceAfter=6)
        role_style = ParagraphStyle('RCN', parent=styles['Normal'], fontName=font_name, fontSize=11, spaceAfter=4, textColor=colors.HexColor('#409eff'))
        app_name = msgs.first().app.name if msgs.first().app else '对话'
        story = [Paragraph(f'对话导出：{app_name}', title_style),
                 Paragraph(f'会话ID：{session_id[:8]} | 导出时间：{timezone.now().strftime("%Y-%m-%d %H:%M")} | 消息数：{msgs.count()}', meta_style),
                 Spacer(1, 12), HRFlowable(width="100%", thickness=1, color=colors.lightgrey), Spacer(1, 12)]
        for msg in msgs:
            role_label = '用户' if msg.role == 'user' else '助手'
            story.append(Paragraph(role_label, role_style))
            safe = msg.content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br/>')
            story.append(Paragraph(safe, body_style))
            story.append(Spacer(1, 8))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
            story.append(Spacer(1, 8))
        doc.build(story)
        pdf_content = buf.getvalue()
        buf.close()
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="chat_{session_id[:8]}.pdf"'
        return response
    except ImportError:
        return fail('PDF 导出需要 reportlab，请安装：pip install reportlab', code=500)
    except Exception as e:
        logger.error("PDF 导出失败: %s", e, exc_info=True)
        return fail(f'PDF 导出失败: {str(e)}', code=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def session_list(request):
    app_id = request.query_params.get('app_id')
    qs = ChatMessage.objects.filter(user=request.user)
    if app_id:
        qs = qs.filter(app_id=app_id)
    sessions = {}
    for msg in qs.select_related('app').order_by('create_time'):
        sid = msg.session_id
        if sid not in sessions:
            sessions[sid] = {'session_id': sid, 'app_id': msg.app_id,
                              'app_name': msg.app.name if msg.app else '',
                              'msg_count': 0, 'last_content': '', 'last_time': None}
        s = sessions[sid]
        s['msg_count'] += 1
        s['last_content'] = msg.content
        s['last_time'] = msg.create_time
    result = sorted(sessions.values(), key=lambda x: x['last_time'], reverse=True)
    return ok(result)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def session_delete(request):
    session_id = request.data.get('session_id')
    if not session_id:
        return fail('session_id 必填', code=400)
    deleted, _ = ChatMessage.objects.filter(session_id=session_id, user=request.user).delete()
    if deleted == 0:
        return fail('会话不存在或无权限', code=404)
    return ok({'deleted': deleted}, message='会话已删除')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def feedback(request):
    msg_id = request.data.get('message_id')
    fb = request.data.get('feedback')
    comment = request.data.get('comment', '') or ''
    if not msg_id or fb not in ('like', 'dislike'):
        return fail('message_id 和 feedback(like/dislike) 必填', code=400)
    try:
        msg = ChatMessage.objects.get(id=msg_id, user=request.user, role='assistant')
    except ChatMessage.DoesNotExist:
        return fail('消息不存在或无权限', code=404)
    msg.feedback = fb
    msg.feedback_comment = str(comment)[:500]
    msg.save(update_fields=['feedback', 'feedback_comment'])
    logger.info("用户反馈: msg=%s, feedback=%s, user=%s", msg_id, fb, request.user)
    return ok({'message_id': msg_id, 'feedback': fb}, message='反馈已提交')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def stats(request):
    from django.db.models import Count, Q
    from datetime import timedelta
    days = int(request.query_params.get('days', 7))
    app_id = request.query_params.get('app_id')
    since = timezone.now() - timedelta(days=days)
    qs = ChatMessage.objects.filter(create_time__gte=since)
    if request.user.role != 'admin':
        qs = qs.filter(user=request.user)
    if app_id:
        qs = qs.filter(app_id=app_id)
    total_assistant = qs.filter(role='assistant').count()
    liked = qs.filter(role='assistant', feedback='like').count()
    disliked = qs.filter(role='assistant', feedback='dislike').count()
    total_user = qs.filter(role='user').count()
    sessions = qs.values('session_id').distinct().count()
    daily = list(qs.filter(role='assistant').extra(select={'day': 'DATE(create_time)'}).values('day')
        .annotate(total=Count('id'), liked=Count('id', filter=Q(feedback='like')),
                  disliked=Count('id', filter=Q(feedback='dislike'))).order_by('day'))
    by_app = list(qs.filter(role='assistant', app__isnull=False).values('app_id', 'app__name')
        .annotate(total=Count('id'), liked=Count('id', filter=Q(feedback='like')),
                  disliked=Count('id', filter=Q(feedback='dislike'))).order_by('-total')[:10])
    return ok({'period_days': days, 'total_sessions': sessions, 'total_user_messages': total_user,
               'total_assistant_messages': total_assistant, 'liked': liked, 'disliked': disliked,
               'like_rate': round(liked / total_assistant, 4) if total_assistant else 0,
               'dislike_rate': round(disliked / total_assistant, 4) if total_assistant else 0,
               'feedback_rate': round((liked + disliked) / total_assistant, 4) if total_assistant else 0,
               'daily': daily, 'by_app': by_app})
