from fastapi import HTTPException

from pipeline.civilian.community import determine_community
from pipeline.civilian.worlds import build_worlds
from pipeline.civilian.prompt_builder import build_neutral_prompt
from pipeline.civilian.generation import generate_with_length_limit, generate_specific_with_length_limit

from api.dependencies import app_state, get_persona_row
from api.engines import ENGINES, build_generate_fn_kwargs
from api.timeout_utils import call_with_timeout


async def run_summarize(uuid: str, text: str, ratio: float = 0.7, engine: str = "gemini") -> dict:
    if engine not in ENGINES:
        raise ValueError(f"engine không hợp lệ: {engine} (chỉ chấp nhận 'gemini' hoặc 'gpt_oss')")

    cfg = ENGINES[engine]
    row = get_persona_row(uuid)
    client = getattr(app_state, cfg["client_attr"])

    if client is None:
        raise HTTPException(
            status_code=503,
            detail=f"Engine '{engine}' không khả dụng trên server này "
                   f"(thiếu cấu hình lúc khởi động — xem log server lúc startup).",
        )

    g = app_state.g
    community = determine_community(row)
    worlds = build_worlds(row)

    neutral_prompt = build_neutral_prompt(text)
    generate_fn, base_kwargs = build_generate_fn_kwargs(engine, client, cfg["model_name"], neutral_prompt)

    # Chung — khách quan
    general_summary, general_meta = await call_with_timeout(
        generate_with_length_limit,
        generate_fn,
        cfg["retry_fn"],
        text,
        base_kwargs,
        "contents",
        ratio,
    )

    # Riêng — cá nhân hóa
    result, specific_meta = await call_with_timeout(
        generate_specific_with_length_limit,
        cfg["summarize_fn"],
        cfg["retry_fn"],
        row, text, g, client,
        ratio,
    )

    return {
        "uuid": row.get("uuid", uuid),
        "engine": engine,
        "general_summary": general_summary,
        "specific_summary": result["summary"],
        "community": community,
        "worlds": worlds,
        "length_check": {"general": general_meta, "specific": specific_meta},
    }