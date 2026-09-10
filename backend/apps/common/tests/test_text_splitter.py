"""文本分块器单元测试"""
from django.test import SimpleTestCase

from apps.common.text_splitter import TextSplitter


class TestTextSplitter(SimpleTestCase):
    """不依赖数据库的纯函数测试"""

    def test_empty_text_returns_empty(self):
        splitter = TextSplitter(chunk_size=100, chunk_overlap=10)
        self.assertEqual(splitter.split_text(""), [])
        self.assertEqual(splitter.split_text("   "), [])
        self.assertEqual(splitter.split_text(None), [])

    def test_short_text_returns_single_chunk(self):
        splitter = TextSplitter(chunk_size=100, chunk_overlap=10)
        text = "这是一段简短的文本。"
        chunks = splitter.split_text(text)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], text)

    def test_long_text_splits_into_multiple_chunks(self):
        splitter = TextSplitter(chunk_size=50, chunk_overlap=5)
        text = "第一段内容。" * 40
        chunks = splitter.split_text(text)
        self.assertGreater(len(chunks), 1)
        for c in chunks:
            self.assertLess(len(c), 70)
        combined = "".join(chunks)
        self.assertIn("第一段内容", combined)

    def test_chinese_punctuation_splitting(self):
        splitter = TextSplitter(chunk_size=30, chunk_overlap=0,
                                 separators=["\n\n", "\n", "。", "；", " "])
        text = "第一句话。第二句话。第三句话。第四句话。"
        chunks = splitter.split_text(text)
        self.assertGreaterEqual(len(chunks), 2)

    def test_separator_fallback_to_char_split(self):
        splitter = TextSplitter(chunk_size=10, chunk_overlap=0, separators=[""])
        text = "A" * 25
        chunks = splitter.split_text(text)
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0], "A" * 10)
        self.assertEqual(chunks[2], "A" * 5)

    def test_default_chunk_size_and_overlap(self):
        splitter = TextSplitter()
        self.assertEqual(splitter.chunk_size, 500)
        self.assertEqual(splitter.chunk_overlap, 50)
