from fastapi import APIRouter

from api.schemas.profile import ProfileResponse
from api.services.profile_service import get_profile

router = APIRouter()

@router.get("/{uuid}", response_model=ProfileResponse)
def read_profile(uuid: str):
    return get_profile(uuid)