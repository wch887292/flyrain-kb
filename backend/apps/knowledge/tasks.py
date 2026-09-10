"""Celery 异步任务：文档解析、分块、向量化入库"""
import os
import logging

from celery import shared_task
from django.conf import settings
from django.contrib.postgres.search import SearchVector

from apps.knowledge.models import Document, Paragraph
from apps.common.parsers import parse_file
from apps.common.text_splitter import TextSplitter
from apps.model_provider.llm_adapter import embed_texts

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=1)
def process_document(self, document_id: int):
    try:
        doc = Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        return {'error': 'document not found'}

    doc.status = 'parsing'
    doc.save(update_fields=['status'])

    try:
        blocks = parse_file(doc.file_path)
        splitter = TextSplitter(chunk_size=500, chunk_overlap=50)

        paragraphs = []
        total_chars = 0
        idx = 0
        image_count = 0
        table_count = 0
        for block in blocks:
            block_type = block.get('block_type', 'text')
            if block_type == 'image':
                image_count += 1
            elif block_type == 'table':
                table_count += 1
            chunks = splitter.split_text(block['content'])
            for chunk in chunks:
                if not chunk.strip():
                    continue
                paragraphs.append(Paragraph(
                    doc=doc, content=chunk, page_no=block.get('page_no', 0),
                    index=idx, block_type=block_type
                ))
                total_chars += len(chunk)
                idx += 1

        # 批量向量化（避免超长，分批 32）
        batch = 32
        created_ids = []
        for i in range(0, len(paragraphs), batch):
            sub = paragraphs[i:i + batch]
            texts = [p.content for p in sub]
            vectors = embed_texts(texts)
            for p, vec in zip(sub, vectors):
                p.vector = vec
            # bulk_create 不触发 post_save 信号，需手动回填 search_vector
            created = Paragraph.objects.bulk_create(sub)
            created_ids.extend([p.pk for p in created])

        # 批量回填全文检索向量（GIN 索引依赖此字段）
        if created_ids:
            config = getattr(settings, 'SEARCH_CONFIG', 'simple')
            Paragraph.objects.filter(pk__in=created_ids).update(
                search_vector=SearchVector('content', config=config)
            )
            logger.info("文档 %s 回填 search_vector 完成，共 %d 段", doc.id, len(created_ids))

        doc.char_count = total_chars
        doc.has_images = image_count > 0
        doc.has_tables = table_count > 0
        doc.image_count = image_count
        doc.table_count = table_count
        doc.status = 'success'
        doc.save(update_fields=['char_count', 'has_images', 'has_tables',
                                'image_count', 'table_count', 'status'])
        return {'doc_id': document_id, 'paragraphs': len(paragraphs)}
    except Exception as e:
        logger.error("文档解析失败: doc_id=%s, name=%s, error=%s",
                     document_id, doc.name if doc else 'unknown', e, exc_info=True)
        doc.status = 'fail'
        doc.error_msg = str(e)[:500]
        doc.save(update_fields=['status', 'error_msg'])
        # 可选重试
        # raise self.retry(exc=e, countdown=5)
        return {'error': str(e)}
