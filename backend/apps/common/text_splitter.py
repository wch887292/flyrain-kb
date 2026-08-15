"""文本分块器：递归按分隔符切片，尽量保持语义完整。"""
from typing import List


class TextSplitter:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50,
                 separators: List[str] = None):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", "。", "；", "；", " ", ""]

    def split_text(self, text: str) -> List[str]:
        text = text or ""
        text = text.strip()
        if not text:
            return []
        return self._split(text, self.separators)

    def _split(self, text: str, separators: List[str]) -> List[str]:
        # 单段已满足，直接返回（不再切）
        if len(text) <= self.chunk_size:
            return [text] if text else []

        sep = separators[0] if separators else ""
        rest = separators[1:] if separators else [""]

        if sep == "":
            # 兜底：按字符硬切
            return [
                text[i:i + self.chunk_size]
                for i in range(0, len(text), max(1, self.chunk_size - self.chunk_overlap))
            ]

        pieces = text.split(sep)
        # 用分隔符重新拼回，保持分隔符
        merged = []
        buf = ""
        for p in pieces:
            candidate = p + sep if p else ""
            if len(buf) + len(candidate) <= self.chunk_size:
                buf += candidate
            else:
                if buf:
                    merged.append(buf)
                buf = candidate
        if buf:
            merged.append(buf)

        # 若仍有超长段，继续用下一个分隔符切
        result = []
        for m in merged:
            if len(m) > self.chunk_size and len(rest) > 0:
                result.extend(self._split(m, rest))
            else:
                result.append(m)
        return [r.strip() for r in result if r.strip()]
