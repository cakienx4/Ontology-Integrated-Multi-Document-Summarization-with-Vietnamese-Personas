from fastapi import HTTPException

from pipeline.civilian.community import determine_community
from pipeline.civilian.worlds import build_worlds
from pipeline.content_classifier import classify_content
from pipeline.relevance import score_text_relevance
from pipeline.civilian.prompt_builder import build_neutral_prompt, build_brief_prompt
from pipeline.civilian.generation import generate_with_length_limit, generate_specific_with_length_limit

from api.dependencies import app_state, get_persona_row
from api.engines import ENGINES, build_generate_fn_kwargs
from api.timeout_utils import call_with_timeout


def _build_combined(primary_id: str, primary_summary: str, others_meta: list[dict]) -> str:
    lines = [f"[Nội dung chính — {primary_id}]", primary_summary, ""]
    if others_meta:
        lines.append("[Nội dung khác được nhắc qua]")
        for item in others_meta:
            lines.append(f"- {item['text_id']}: {item['brief']}")
    return "\n".join(lines)


async def run_multi_summarize(uuid: str, texts: dict[str, str], ratio: float = 0.7, engine: str = "gemini") -> dict:
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

    # 1. Chấm điểm + xếp hạng tất cả văn bản
    scored = []
    for text_id, text in texts.items():
        content_meta = classify_content(text)
        score = score_text_relevance(row, community, content_meta)
        scored.append({"text_id": text_id, "text": text, "content_meta": content_meta, "score": score})
    scored.sort(key=lambda x: x["score"], reverse=True)

    primary = scored[0]
    others = scored[1:]

    # 2. Tóm tắt "Chung" cho TỪNG văn bản — không ưu tiên ai
    general_summaries: dict[str, str] = {}
    general_meta_all: dict[str, dict] = {}
    for item in scored:
        neutral_prompt = build_neutral_prompt(item["text"])
        generate_fn, base_kwargs = build_generate_fn_kwargs(engine, client, cfg["model_name"], neutral_prompt)
        g_summary, g_meta = await call_with_timeout(
            generate_with_length_limit, generate_fn, cfg["retry_fn"], item["text"], base_kwargs, "contents", ratio,
        )
        general_summaries[item["text_id"]] = g_summary
        general_meta_all[item["text_id"]] = g_meta

    # 3. Tóm tắt "Riêng" đầy đủ cho văn bản phù hợp nhất
    primary_result, primary_meta = await call_with_timeout(
        generate_specific_with_length_limit,
        cfg["summarize_fn"], cfg["retry_fn"], row, primary["text"], g, client, ratio,
    )

    # 4. Tóm tắt cực ngắn cho các văn bản còn lại
    others_meta = []
    for item in others:
        brief_prompt = build_brief_prompt(item["text"])
        generate_fn, base_kwargs = build_generate_fn_kwargs(engine, client, cfg["model_name"], brief_prompt)
        response = await call_with_timeout(cfg["retry_fn"], generate_fn, **base_kwargs)
        others_meta.append({"text_id": item["text_id"], "brief": response.text.strip()})

    combined = _build_combined(primary["text_id"], primary_result["summary"], others_meta)

    return {
        "uuid": row.get("uuid", uuid),
        "engine": engine,
        "ranking": [{"text_id": s["text_id"], "score": s["score"], "content_classification": s["content_meta"]}
                    for s in scored],
        "primary_text_id": primary["text_id"],
        "general_summaries": general_summaries,
        "specific_summary": primary_result["summary"],
        "brief_mentions": others_meta,
        "combined": combined,
        "community": community,
        "worlds": worlds,
        "length_check": {"general": general_meta_all, "specific_primary": primary_meta},
    }
