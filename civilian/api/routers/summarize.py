from fastapi import APIRouter, HTTPException

from api.schemas.summary import SummarizeRequest, SummarizeResponse
from api.schemas.multi_summary_schema import MultiSummarizeRequest, MultiSummarizeResponse
from api.services.summary_service import run_summarize
from api.services.multi_summary_service import run_multi_summarize

router = APIRouter()


def _map_errors(e: Exception) -> HTTPException:
    msg = str(e)
    if any(k in msg for k in ("API_KEY_INVALID", "PERMISSION_DENIED", "UNAUTHENTICATED", "401")):
        return HTTPException(
            status_code=502,
            detail=f"Xác thực với model thất bại (kiểm tra GEMINI_API_KEY hoặc endpoint RunAI): {msg}",
        )
    if "RESOURCE_EXHAUSTED" in msg or "429" in msg or "rate" in msg.lower():
        return HTTPException(status_code=429, detail=f"Model quota/rate limit: {msg}")
    return HTTPException(status_code=502, detail=f"Lỗi khi sinh tóm tắt: {msg}")


@router.post("", response_model=SummarizeResponse)
async def summarize(req: SummarizeRequest):
    try:
        return await run_summarize(req.uuid, req.text, req.ratio, req.engine)
    except HTTPException:
        raise
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except Exception as e:
        raise _map_errors(e)


@router.post("/multi", response_model=MultiSummarizeResponse)
async def summarize_multi(req: MultiSummarizeRequest):
    try:
        return await run_multi_summarize(req.uuid, req.texts, req.ratio, req.engine)
    except HTTPException:
        raise
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise _map_errors(e)