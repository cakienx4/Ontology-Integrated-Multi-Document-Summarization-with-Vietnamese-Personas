from typing import Any, Literal
from pydantic import BaseModel, Field

class SummarizeRequest(BaseModel):
    uuid: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1, description="Văn bản đầu vào cần tóm tắt")
    ratio: float = Field(0.7, gt=0, le=1, description="Tỉ lệ độ dài tối đa so với bản gốc")
    engine: Literal["gemini", "gpt_oss"] = Field(
        "gemini", description="Model dùng để sinh tóm tắt: gemini hoặc gpt_oss (gpt-oss-120b qua RunAI)"
    )

class LengthMeta(BaseModel):
    length_ok: bool
    words: int
    max_words: int
    attempts: int

class SummarizeResponse(BaseModel):
    uuid: str
    engine: str
    general_summary: str
    specific_summary: str
    community: dict[str, Any]
    worlds: dict[str, Any]
    length_check: dict[str, LengthMeta]