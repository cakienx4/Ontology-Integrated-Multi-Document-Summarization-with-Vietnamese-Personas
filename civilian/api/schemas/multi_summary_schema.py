from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator

MAX_TEXTS_PER_REQUEST = 8  # giới hạn để endpoint real-time không kéo dài vô hạn (N*LLM call tuần tự)


class MultiSummarizeRequest(BaseModel):
    uuid: str = Field(..., min_length=1)
    texts: dict[str, str] = Field(..., description="{text_id: nội dung văn bản}, tối thiểu 1, tối đa 8")
    ratio: float = Field(0.7, gt=0, le=1)
    engine: Literal["gemini", "gpt_oss"] = "gemini"

    @field_validator("texts")
    @classmethod
    def validate_texts(cls, v: dict[str, str]) -> dict[str, str]:
        if not v:
            raise ValueError("texts không được rỗng — cần ít nhất 1 văn bản")
        if len(v) > MAX_TEXTS_PER_REQUEST:
            raise ValueError(
                f"texts có {len(v)} văn bản, vượt giới hạn {MAX_TEXTS_PER_REQUEST} cho 1 request "
                f"(endpoint chạy tuần tự N lệnh gọi LLM, quá nhiều sẽ timeout)."
            )
        for text_id, text in v.items():
            if not text or not text.strip():
                raise ValueError(f"text_id '{text_id}' có nội dung rỗng")
        return v


class RankingItem(BaseModel):
    text_id: str
    score: float
    content_classification: dict[str, Any]


class BriefMention(BaseModel):
    text_id: str
    brief: str


class MultiSummarizeResponse(BaseModel):
    uuid: str
    engine: str
    ranking: list[RankingItem]
    primary_text_id: str
    general_summaries: dict[str, str]      # {text_id: tóm tắt Chung}
    specific_summary: str                   # tóm tắt Riêng đầy đủ cho văn bản ưu tiên nhất
    brief_mentions: list[BriefMention]      # tóm tắt cực ngắn cho các văn bản còn lại
    combined: str                           # bản ghép giống file .md của CLI
    community: dict[str, Any]
    worlds: dict[str, Any]
    length_check: dict[str, Any]
