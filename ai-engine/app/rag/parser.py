# ai-engine/app/rag/parser.py
import pymupdf as fitz  # PyMuPDF
from docx import Document as DocxDocument
from bs4 import BeautifulSoup
from pathlib import Path


class DocumentParser:
    """根据文件类型路由到对应的解析器"""

    def parse(self, file_path: str) -> str:
        path = Path(file_path)
        suffix = path.suffix.lower()

        parsers = {
            ".pdf": self._parse_pdf,
            ".txt": self._parse_text,
            ".md": self._parse_text,
            ".docx": self._parse_docx,
            ".html": self._parse_html,
        }

        parser = parsers.get(suffix)
        if not parser:
            raise ValueError(f"不支持的文件类型: {suffix}")
        return parser(file_path)

    def _parse_pdf(self, file_path: str) -> str:
        doc = fitz.open(file_path)
        text_parts = []
        for page_num, page in enumerate(doc, 1):
            text = page.get_text()
            if text.strip():
                text_parts.append(f"--- 第 {page_num} 页 ---\n{text}")
        doc.close()
        return "\n\n".join(text_parts)

    def _parse_docx(self, file_path: str) -> str:
        doc = DocxDocument(file_path)
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())

    def _parse_html(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        # 移除 script 和 style
        for tag in soup(["script", "style"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)

    def _parse_text(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
