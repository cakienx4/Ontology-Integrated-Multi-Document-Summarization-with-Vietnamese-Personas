from typing import Any
from pydantic import BaseModel

class ProfileResponse(BaseModel):
    uuid: str
    raw_fields: dict[str, Any]
    community: dict[str, Any]
    worlds: dict[str, Any]