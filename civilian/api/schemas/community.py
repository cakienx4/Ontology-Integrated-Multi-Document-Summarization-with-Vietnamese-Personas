from typing import Any
from pydantic import BaseModel

class CommunityResponse(BaseModel):
    uuid: str
    community: dict[str, Any]   # {"Language", "Topic", "Domain", "Cultural", "Prototype"}