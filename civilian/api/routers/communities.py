from fastapi import APIRouter

from api.schemas.community import CommunityResponse
from api.services.community_service import get_community

router = APIRouter()

@router.get("/{uuid}", response_model=CommunityResponse)
def read_community(uuid: str):
    return get_community(uuid)