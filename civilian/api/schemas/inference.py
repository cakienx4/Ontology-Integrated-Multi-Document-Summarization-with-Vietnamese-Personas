from typing import Any
from pydantic import BaseModel

class InferenceResponse(BaseModel):
    uuid: str
    worlds: dict[str, Any]   # {"xac_nhan": {...}, "gia_tuong": {...}}