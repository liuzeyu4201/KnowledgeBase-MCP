from __future__ import annotations

from knowledgebase.domain.exceptions import AppError
from knowledgebase.integrations.parser.common import sanitize_document_text


class MarkdownParser:
    """Markdown 文本解析器。"""

    def parse(self, content: bytes) -> list[dict[str, int | str]]:
        """解析 Markdown 文本，作为单页逻辑内容返回。"""

        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AppError(
                code="DOCUMENT_PARSE_FAILED",
                message="failed to decode markdown",
                error_type="system_error",
            ) from exc

        sanitized = sanitize_document_text(text).strip()
        if not sanitized:
            raise AppError(
                code="DOCUMENT_PARSE_FAILED",
                message="no extractable text found in markdown",
                error_type="system_error",
            )

        return [{"page_no": 1, "content": sanitized}]
