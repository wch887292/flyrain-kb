"""文档解析器：支持 PDF / DOCX / TXT / Markdown / XLSX。
返回结构：[{"content": str, "page_no": int}, ...]
"""
import os
from typing import List, Dict


def parse_file(file_path: str) -> List[Dict]:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        return _parse_pdf(file_path)
    if ext in ('.docx',):
        return _parse_docx(file_path)
    if ext in ('.txt', '.md', '.markdown'):
        return _parse_text(file_path)
    if ext in ('.xlsx', '.xls'):
        return _parse_xlsx(file_path)
    raise ValueError(f'不支持的文件类型: {ext}')


def _parse_pdf(file_path: str) -> List[Dict]:
    try:
        from pypdf import PdfReader
    except ImportError:
        raise RuntimeError('缺少依赖 pypdf，请安装')
    reader = PdfReader(file_path)
    results = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            results.append({'content': text, 'page_no': i})
    return results


def _parse_docx(file_path: str) -> List[Dict]:
    try:
        from docx import Document
    except ImportError:
        raise RuntimeError('缺少依赖 python-docx，请安装')
    doc = Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return [{'content': "\n".join(paragraphs), 'page_no': 0}] if paragraphs else []


def _parse_text(file_path: str) -> List[Dict]:
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()
    # 按空行分段
    blocks = [b.strip() for b in text.split('\n\n') if b.strip()]
    if not blocks:
        blocks = [text.strip()] if text.strip() else []
    return [{'content': b, 'page_no': 0} for b in blocks]


def _parse_xlsx(file_path: str) -> List[Dict]:
    try:
        from openpyxl import load_workbook
    except ImportError:
        raise RuntimeError('缺少依赖 openpyxl，请安装')
    wb = load_workbook(file_path, read_only=True, data_only=True)
    results = []
    for sheet in wb.worksheets:
        rows = []
        for row in sheet.iter_rows(values_only=True):
            cells = [str(c) for c in row if c is not None]
            if cells:
                rows.append(" | ".join(cells))
        if rows:
            results.append({'content': "\n".join(rows), 'page_no': 0})
    wb.close()
    return results
