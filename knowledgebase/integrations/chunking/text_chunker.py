from __future__ import annotations

from dataclasses import dataclass

from knowledgebase.app.config import get_settings


@dataclass
class ChunkPayload:
    page_no: int
    chunk_no: int
    char_start: int
    char_end: int
    token_count: int
    content: str


class TextChunker:
    """简单文本切片器。"""

    def __init__(self) -> None:
        settings = get_settings()
        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap

    def chunk_pages(self, pages: list[dict[str, int | str]]) -> list[ChunkPayload]:
        """按页执行滑动窗口切片。"""

        chunks: list[ChunkPayload] = []
        global_chunk_no = 0

        for page in pages:
            page_no = int(page["page_no"])
            content = str(page["content"]).strip()
            start = 0

            while start < len(content):
                end = min(start + self.chunk_size, len(content))
                chunk_text = content[start:end].strip()
                if chunk_text:
                    chunks.append(
                        ChunkPayload(
                            page_no=page_no,
                            chunk_no=global_chunk_no,
                            char_start=start,
                            char_end=end,
                            token_count=max(1, len(chunk_text) // 2),
                            content=chunk_text,
                        )
                    )
                    global_chunk_no += 1

                if end >= len(content):
                    break

                start = max(0, end - self.chunk_overlap)

        return chunks
