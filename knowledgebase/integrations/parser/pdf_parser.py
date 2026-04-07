from __future__ import annotations

from io import BytesIO
import unicodedata

from pypdf import PdfReader

from knowledgebase.domain.exceptions import AppError


class PDFParser:
    """PDF 文本解析器。"""

    def _sanitize_text(self, text: str) -> str:
        """清理 PDF 文本中的非法控制字符，避免数据库与索引写入失败。"""

        normalized = unicodedata.normalize("NFKC", text).replace("\r\n", "\n").replace("\r", "\n")
        cleaned_chars: list[str] = []
        for char in normalized:
            if char in {"\n", "\t"} or unicodedata.category(char) != "Cc":
                cleaned_chars.append(char)
        return "".join(cleaned_chars)

    def parse(self, content: bytes) -> list[dict[str, int | str]]:
        """解析 PDF 文本并返回按页拆分的结果。"""

        try:
            reader = PdfReader(BytesIO(content))
        except Exception as exc:  # noqa: BLE001
            raise AppError(
                code="DOCUMENT_PARSE_FAILED",
                message="failed to parse pdf",
                error_type="system_error",
            ) from exc

        pages: list[dict[str, int | str]] = []
        for index, page in enumerate(reader.pages, start=1):
            text = self._sanitize_text(page.extract_text() or "").strip()
            if not text:
                continue
            pages.append(
                {
                    "page_no": index,
                    "content": text,
                }
            )

        if not pages:
            raise AppError(
                code="DOCUMENT_PARSE_FAILED",
                message="no extractable text found in pdf",
                error_type="system_error",
            )

        return pages
