from __future__ import annotations

SUPPORTED_DOCUMENT_MIME_TYPES: dict[str, str] = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/markdown": "md",
    "text/x-markdown": "md",
}


def normalize_document_mime_type(value: str) -> str:
    """标准化文档 MIME 类型，统一小写并去掉首尾空白。"""

    return value.strip().lower()


def is_supported_document_mime_type(value: str) -> bool:
    """判断 MIME 类型是否在当前支持范围内。"""

    return normalize_document_mime_type(value) in SUPPORTED_DOCUMENT_MIME_TYPES


def resolve_document_source_type(mime_type: str) -> str:
    """根据 MIME 类型解析文档来源类型。"""

    normalized = normalize_document_mime_type(mime_type)
    return SUPPORTED_DOCUMENT_MIME_TYPES.get(normalized, "unknown")


def supported_document_mime_type_message() -> str:
    """生成统一的支持类型提示文案。"""

    return (
        "仅支持 application/pdf, "
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document, "
        "text/markdown, text/x-markdown"
    )
