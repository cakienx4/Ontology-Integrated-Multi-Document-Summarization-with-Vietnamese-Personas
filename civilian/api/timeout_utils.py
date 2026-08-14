"""
api/timeout_utils.py

Wrapper timeout dùng chung cho mọi lệnh gọi model chạy trong threadpool
(retry_generate nội bộ đã bị giới hạn số lần, nhưng vẫn cần lớp bảo vệ này
vì SDK không phải lúc nào cũng tôn trọng timeout của chính nó).
"""

import asyncio

from fastapi.concurrency import run_in_threadpool

STEP_TIMEOUT_SECONDS = 90


async def call_with_timeout(func, *args, _timeout: float = STEP_TIMEOUT_SECONDS, **kwargs):
    try:
        return await asyncio.wait_for(run_in_threadpool(func, *args, **kwargs), timeout=_timeout)
    except asyncio.TimeoutError:
        raise TimeoutError(f"Model không phản hồi sau {_timeout}s (có thể do quota/kết nối).")
