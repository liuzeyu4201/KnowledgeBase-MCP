from __future__ import annotations

from io import BytesIO

from docx import Document as DocxDocument

from knowledgebase.domain.exceptions import AppError
from knowledgebase.integrations.parser.common import sanitize_document_text


class DocxParser:
    """DOCX 文本解析器。"""

    def parse(self, content: bytes) -> list[dict[str, int | str]]:
        """解析 DOCX 文本，按逻辑单页内容返回。"""

        try:
            document = DocxDocument(BytesIO(content))
        except Exception as exc:  # noqa: BLE001
            raise AppError(
                code="DOCUMENT_PARSE_FAILED",
                message="failed to parse docx",
                error_type="system_error",
            ) from exc

        paragraphs = [
            sanitize_document_text(paragraph.text).strip()
            for paragraph in document.paragraphs
        ]
        text = "\n\n".join([paragraph for paragraph in paragraphs if paragraph]).strip()
        if not text:
            raise AppError(
                code="DOCUMENT_PARSE_FAILED",
                message="no extractable text found in docx",
                error_type="system_error",
            )

        return [{"page_no": 1, "content": text}]
