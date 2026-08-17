# ai-engine/app/rag/splitter.py
from langchain.text_splitter import RecursiveCharacterTextSplitter


class TextSplitter:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "\u3002", ".", "\uff01", "!", "\uff1f", "?", " ", ""],
            length_function=len,
        )

    def split(self, text: str) -> list[dict]:
        """
        返回 [{"index": 0, "content": "...", "metadata": {}}, ...]
        """
        chunks = self.splitter.split_text(text)
        return [
            {"index": i, "content": chunk, "metadata": {}}
            for i, chunk in enumerate(chunks)
        ]
