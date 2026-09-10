"""检索逻辑：向量检索 / 关键词检索 / 混合检索"""
import logging
from typing import List, Dict, Any

from django.conf import settings
from django.db.models import Q
from django.contrib.postgres.search import SearchQuery, SearchRank
from pgvector.django import CosineDistance

from apps.knowledge.models import Paragraph, KnowledgeBase
from apps.model_provider.llm_adapter import embed_texts

logger = logging.getLogger(__name__)


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
    """PostgreSQL 全文检索：基于 search_vector (tsvector) + GIN 索引。

    使用 settings.SEARCH_CONFIG 配置的分词器（simple / jieba），
    多词之间为 OR 关系，按 SearchRank 相关性排序。
    """
    config = getattr(settings, 'SEARCH_CONFIG', 'simple')
    terms = [t for t in query.replace('，', ' ').replace(',', ' ').split() if len(t) > 1]
    if not terms:
        terms = [query]

    # 构建多词 OR 查询
    search_query = SearchQuery(terms[0], config=config)
    for t in terms[1:]:
        search_query |= SearchQuery(t, config=config)

    qs = (Paragraph.objects
          .filter(doc__kb=kb, search_vector=search_query)
          .annotate(rank=SearchRank('search_vector', search_query))
          .order_by('-rank')[:top_k])

    return [{
        'paragraph': p,
        'score': min(1.0, float(p.rank)),  # SearchRank 归一化到 0~1
        'doc_name': p.doc.name,
        'page_no': p.page_no,
    } for p in qs]


def hybrid_search(kb: KnowledgeBase, query: str, top_k: int = 5,
                  vector_weight: float = 0.7) -> List[Dict[str, Any]]:
    """混合检索：向量(默认0.7权重) + 关键词(0.3)。返回归一化融合分数。"""
    # 向量检索
    try:
        q_vec = embed_texts([query])[0]
        v_results = vector_search(kb, q_vec, top_k=top_k * 2)
    except Exception as e:
        logger.warning("混合检索-向量检索失败，回退纯关键词检索: kb=%s, error=%s", kb.id, e)
        v_results = []
    try:
        k_results = keyword_search(kb, query, top_k=top_k * 2)
    except Exception as e:
        logger.warning("混合检索-关键词检索失败: kb=%s, error=%s", kb.id, e)
        k_results = []

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
