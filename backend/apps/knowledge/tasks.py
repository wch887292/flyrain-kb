"""Celery 异步任务：文档解析、分块、向量化入库"""
import os

from celery import shared_task

from apps.knowledge.models import Document, Paragraph
from apps.common.parsers import parse_file
from apps.common.text_splitter import TextSplitter
from apps.model_provider.llm_adapter import embed_texts


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
        for block in blocks:
            chunks = splitter.split_text(block['content'])
            for chunk in chunks:
                if not chunk.strip():
                    continue
                paragraphs.append(Paragraph(
                    doc=doc, content=chunk, page_no=block.get('page_no', 0), index=idx
                ))
                total_chars += len(chunk)
                idx += 1

        # 批量向量化（避免超长，分批 32）
        batch = 32
        for i in range(0, len(paragraphs), batch):
            sub = paragraphs[i:i + batch]
            texts = [p.content for p in sub]
            vectors = embed_texts(texts)
            for p, vec in zip(sub, vectors):
                p.vector = vec
            Paragraph.objects.bulk_create(sub)

        doc.char_count = total_chars
        doc.status = 'success'
        doc.save(update_fields=['char_count', 'status'])
        return {'doc_id': document_id, 'paragraphs': len(paragraphs)}
    except Exception as e:  # noqa
        doc.status = 'fail'
        doc.error_msg = str(e)[:500]
        doc.save(update_fields=['status', 'error_msg'])
        # 可选重试
        # raise self.retry(exc=e, countdown=5)
        return {'error': str(e)}
