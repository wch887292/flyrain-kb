"""检索逻辑：向量检索 / 关键词检索 / 混合检索"""
from typing import List, Dict, Any

from django.db.models import Q
from pgvector.django import CosineDistance

from apps.knowledge.models import Paragraph, KnowledgeBase
from apps.model_provider.llm_adapter import embed_texts


def vector_search(kb: KnowledgeBase, query_vector: List[float],
                  top_k: int = 5) -> List[Dict[str, Any]]:
    qs = (Paragraph.objects
          .filter(doc__kb=kb, vector__isnull=False)
          .annotate(distance=CosineDistance('vector', query_vector))
          .order_by('distance')[:top_k])
    # cosine 距离越小越相似 -> 转为相似度分数
    return [{
        'paragraph': p,
        'score': 1 - float(p.distance),  # 近似相似度 0~1
        'doc_name': p.doc.name,
        'page_no': p.page_no,
    } for p in qs]


def keyword_search(kb: KnowledgeBase, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    terms = [t for t in query.replace('，', ' ').replace(',', ' ').split() if len(t) > 1]
    if not terms:
        terms = [query]
    q = Q()
    for t in terms:
        q |= Q(content__icontains=t)
    qs = (Paragraph.objects
          .filter(doc__kb=kb)
          .filter(q)
          .order_by('index')[:top_k * 2])
    scored = []
    for p in qs:
        hit = sum(p.content.count(t) for t in terms)
        if hit == 0:
            continue
        scored.append({
            'paragraph': p,
            'score': min(1.0, hit / 10.0),
            'doc_name': p.doc.name,
            'page_no': p.page_no,
        })
    scored.sort(key=lambda x: x['score'], reverse=True)
    return scored[:top_k]


def hybrid_search(kb: KnowledgeBase, query: str, top_k: int = 5,
                  vector_weight: float = 0.7) -> List[Dict[str, Any]]:
    """混合检索：向量(默认0.7权重) + 关键词(0.3)。返回归一化融合分数。"""
    # 向量检索
    try:
        q_vec = embed_texts([query])[0]
        v_results = vector_search(kb, q_vec, top_k=top_k * 2)
    except Exception:  # noqa
        v_results = []
    k_results = keyword_search(kb, query, top_k=top_k * 2)

    merged = {}
    for r in v_results:
        merged[r['paragraph'].id] = {'meta': r, 'v': r['score'], 'k': 0.0}
    for r in k_results:
        pid = r['paragraph'].id
        if pid in merged:
            merged[pid]['k'] = r['score']
        else:
            merged[pid] = {'meta': r, 'v': 0.0, 'k': r['score']}

    final = []
    for pid, item in merged.items():
        score = vector_weight * item['v'] + (1 - vector_weight) * item['k']
        meta = item['meta']
        final.append({
            'paragraph': meta['paragraph'],
            'score': round(score, 4),
            'doc_name': meta['doc_name'],
            'page_no': meta['page_no'],
        })
    final.sort(key=lambda x: x['score'], reverse=True)
    return final[:top_k]
