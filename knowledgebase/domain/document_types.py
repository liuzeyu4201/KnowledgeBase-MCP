from __future__ import annotations

SUPPORTED_DOCUMENT_MIME_TYPES: dict[str, str] = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/markdown": "md",
    "text/x-markdown": "md",
}

SUPPORTED_DOCUMENT_SUFFIX_MIME_TYPES: dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
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


def infer_document_mime_type(*, file_name: str, provided_mime_type: str | None) -> str:
    """优先使用显式 MIME 类型，缺失或为通用类型时再按文件后缀推断。"""

    if provided_mime_type:
        normalized = normalize_document_mime_type(provided_mime_type)
        if normalized not in {"application/octet-stream", "binary/octet-stream"}:
            return normalized

    lowered_name = file_name.strip().lower()
    for suffix, mime_type in SUPPORTED_DOCUMENT_SUFFIX_MIME_TYPES.items():
        if lowered_name.endswith(suffix):
            return mime_type
    return normalize_document_mime_type(provided_mime_type or "")
