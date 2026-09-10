"""文档解析器：支持 PDF / DOCX / TXT / Markdown / XLSX。
返回结构：[{"content": str, "page_no": int, "block_type": "text"|"table"|"image"}, ...]

多模态说明：
- PDF：优先用 pymupdf 提取文本+图片，图片优先调用视觉 LLM 理解，其次 OCR（pytesseract）
- DOCX：提取段落文本 + 表格（转为 Markdown）
- XLSX：每个 sheet 转为 Markdown 表格
- 图片内容：标注为 [图片: page=X, index=Y] + 视觉理解/OCR文本（如有）
"""
import os
import io
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def _vision_understand(image_bytes: bytes) -> str:
    """优先调用支持视觉的 LLM 理解图片内容，失败返回空字符串。"""
    try:
        from apps.model_provider.llm_adapter import vision_completion, get_vision_config
        if not get_vision_config():
            return ''  # 没有配置视觉模型
        result = vision_completion(image_bytes)
        return result or ''
    except Exception as e:
        logger.debug("视觉理解失败: %s", e)
        return ''


def _ocr_image(image_bytes: bytes) -> str:
    """尝试用 pytesseract 对图片做 OCR，失败返回空字符串。"""
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(img, lang='chi_sim+eng')
        return text.strip()
    except ImportError:
        return ''
    except Exception as e:
        logger.debug("OCR 失败: %s", e)
        return ''


def _understand_image(image_bytes: bytes) -> str:
    """图片理解：优先视觉 LLM，其次 OCR，都不可用返回空字符串。"""
    vision_text = _vision_understand(image_bytes)
    if vision_text:
        return f'视觉理解：\n{vision_text}'
    ocr_text = _ocr_image(image_bytes)
    if ocr_text:
        return f'OCR识别内容：\n{ocr_text}'
    return ''


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
    """PDF 解析：优先 pymupdf（文本+图片），回退 pypdf（纯文本）。"""
    try:
        import fitz  # pymupdf
        doc = fitz.open(file_path)
        results = []
        for page_no, page in enumerate(doc, start=1):
            text = page.get_text().strip()
            if text:
                results.append({'content': text, 'page_no': page_no, 'block_type': 'text'})
            image_list = page.get_images(full=True)
            for img_idx, img in enumerate(image_list, start=1):
                content = f'[图片: 第{page_no}页 第{img_idx}张图]'
                try:
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    understood = _understand_image(image_bytes)
                    if understood:
                        content += f'\n{understood}'
                except Exception as e:
                    logger.debug("图片提取/理解失败: page=%s, idx=%s, error=%s", page_no, img_idx, e)
                results.append({
                    'content': content,
                    'page_no': page_no,
                    'block_type': 'image',
                })
        doc.close()
        if results:
            return results
    except ImportError:
        pass
    except Exception:
        pass

    try:
        from pypdf import PdfReader
    except ImportError:
        raise RuntimeError('缺少依赖 pypdf 或 pymupdf，请安装')
    reader = PdfReader(file_path)
    results = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            results.append({'content': text, 'page_no': i, 'block_type': 'text'})
    return results


def _table_to_markdown(rows: List[List[str]]) -> str:
    """将二维表格转为 Markdown 格式。"""
    if not rows:
        return ''
    max_cols = max(len(r) for r in rows)
    rows = [r + [''] * (max_cols - len(r)) for r in rows]
    header = rows[0]
    body = rows[1:] if len(rows) > 1 else []
    lines = ['| ' + ' | '.join(str(c) for c in header) + ' |']
    lines.append('| ' + ' | '.join(['---'] * max_cols) + ' |')
    for row in body:
        lines.append('| ' + ' | '.join(str(c) for c in row) + ' |')
    return '\n'.join(lines)


def _parse_docx(file_path: str) -> List[Dict]:
    """DOCX 解析：段落文本 + 表格（Markdown）。"""
    try:
        from docx import Document
    except ImportError:
        raise RuntimeError('缺少依赖 python-docx，请安装')
    doc = Document(file_path)
    results = []

    from docx.oxml.ns import qn
    body = doc.element.body
    para_idx = 0
    table_idx = 0
    paragraphs = doc.paragraphs
    tables = doc.tables

    for child in body.iterchildren():
        if child.tag == qn('w:p'):
            if para_idx < len(paragraphs):
                text = paragraphs[para_idx].text.strip()
                if text:
                    results.append({'content': text, 'page_no': 0, 'block_type': 'text'})
                para_idx += 1
        elif child.tag == qn('w:tbl'):
            if table_idx < len(tables):
                table = tables[table_idx]
                rows = []
                for row in table.rows:
                    cells = [cell.text.strip() for cell in row.cells]
                    if any(cells):
                        rows.append(cells)
                if rows:
                    md = _table_to_markdown(rows)
                    if md:
                        results.append({'content': md, 'page_no': 0, 'block_type': 'table'})
                table_idx += 1

    if not results:
        texts = [p.text for p in doc.paragraphs if p.text.strip()]
        if texts:
            results.append({'content': "\n".join(texts), 'page_no': 0, 'block_type': 'text'})
        for table in doc.tables:
            rows = [[cell.text.strip() for cell in row.cells] for row in table.rows]
            md = _table_to_markdown([r for r in rows if any(r)])
            if md:
                results.append({'content': md, 'page_no': 0, 'block_type': 'table'})
    return results


def _parse_text(file_path: str) -> List[Dict]:
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()
    blocks = [b.strip() for b in text.split('\n\n') if b.strip()]
    if not blocks:
        blocks = [text.strip()] if text.strip() else []
    return [{'content': b, 'page_no': 0, 'block_type': 'text'} for b in blocks]


def _parse_xlsx(file_path: str) -> List[Dict]:
    """XLSX 解析：每个 sheet 转为 Markdown 表格。"""
    try:
        from openpyxl import load_workbook
    except ImportError:
        raise RuntimeError('缺少依赖 openpyxl，请安装')
    wb = load_workbook(file_path, read_only=True, data_only=True)
    results = []
    for sheet in wb.worksheets:
        rows = []
        for row in sheet.iter_rows(values_only=True):
            cells = [str(c) if c is not None else '' for c in row]
            if any(cells):
                rows.append(cells)
        if rows:
            md = _table_to_markdown(rows)
            if md:
                results.append({
                    'content': f'### Sheet: {sheet.title}\n\n{md}',
                    'page_no': 0,
                    'block_type': 'table',
                })
    wb.close()
    return results
