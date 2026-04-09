from __future__ import annotations

import unicodedata


def sanitize_document_text(text: str) -> str:
    """清理文档文本中的非法控制字符，统一换行格式。"""

    normalized = unicodedata.normalize("NFKC", text).replace("\r\n", "\n").replace("\r", "\n")
    cleaned_chars: list[str] = []
    for char in normalized:
        if char in {"\n", "\t"} or unicodedata.category(char) != "Cc":
            cleaned_chars.append(char)
    return "".join(cleaned_chars)
