from fastapi import APIRouter

from api.schemas.inference import InferenceResponse
from api.services.inference_service import get_inference

router = APIRouter()

@router.get("/{uuid}", response_model=InferenceResponse)
def read_inference(uuid: str):
    return get_inference(uuid)