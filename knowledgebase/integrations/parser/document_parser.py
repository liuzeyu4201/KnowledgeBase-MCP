from __future__ import annotations

from knowledgebase.domain.document_types import normalize_document_mime_type
from knowledgebase.domain.exceptions import AppError
from knowledgebase.integrations.parser.docx_parser import DocxParser
from knowledgebase.integrations.parser.markdown_parser import MarkdownParser
from knowledgebase.integrations.parser.pdf_parser import PDFParser


class DocumentParser:
    """通用文档解析入口，按 MIME 类型分发到底层解析器。"""

    def __init__(self) -> None:
        self.pdf_parser = PDFParser()
        self.docx_parser = DocxParser()
        self.markdown_parser = MarkdownParser()

    def parse(self, *, mime_type: str, content: bytes) -> list[dict[str, int | str]]:
        """按 MIME 类型解析文档，返回统一的逻辑页结构。"""

        normalized_mime_type = normalize_document_mime_type(mime_type)
        if normalized_mime_type == "application/pdf":
            return self.pdf_parser.parse(content)
        if normalized_mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            return self.docx_parser.parse(content)
        if normalized_mime_type in {"text/markdown", "text/x-markdown"}:
            return self.markdown_parser.parse(content)
        raise AppError(
            code="INVALID_ARGUMENT",
            message="unsupported mime_type",
            error_type="validation_error",
            details={"mime_type": mime_type},
        )
