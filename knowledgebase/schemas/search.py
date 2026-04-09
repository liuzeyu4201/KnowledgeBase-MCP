from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


def _strip_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class SearchRetrieveInput(BaseModel):
    request_id: str | None = None
    operator: str | None = None
    trace_id: str | None = None
    query: str = Field(min_length=1, max_length=2048)
    alpha: float = Field(default=0.0, ge=0.0, le=1.0)
    limit: int = Field(default=10, ge=1, le=20)
    category_id: int | None = Field(default=None, gt=0)
    document_id: int | None = Field(default=None, gt=0)

    @field_validator("query", mode="before")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        stripped = _strip_or_none(value)
        if stripped is None:
            raise ValueError("query 不能为空")
        return stripped


class SearchCategoryOutput(BaseModel):
    id: int
    category_code: str
    name: str


class SearchDocumentOutput(BaseModel):
    id: int
    document_uid: str
    title: str
    file_name: str
    category_id: int
    version: int


class SearchHitOutput(BaseModel):
    chunk_id: int
    chunk_uid: str
    chunk_no: int
    page_no: int | None
    score: float | None
    content: str
    document: SearchDocumentOutput
    category: SearchCategoryOutput


class SearchRetrieveOutput(BaseModel):
    query: str
    alpha: float
    retrieval_mode: str
    total: int
    items: list[SearchHitOutput]
