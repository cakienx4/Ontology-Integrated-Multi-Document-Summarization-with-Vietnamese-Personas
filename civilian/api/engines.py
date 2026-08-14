"""
api/engines.py

Bảng cấu hình engine dùng chung cho toàn bộ api/ — tránh duplicate giữa
summary_service.py (1 văn bản) và multi_summary_service.py (nhiều văn bản).
"""

from pipeline.civilian import summarizer_gemini, summarizer_gpt

ENGINES = {
    "gemini": {
        "client_attr": "gemini_client",
        "retry_fn": summarizer_gemini.retry_generate,
        "summarize_fn": summarizer_gemini.summarize_person,
        "model_name": summarizer_gemini.SUMMARY_MODEL_NAME,
    },
    "gpt_oss": {
        "client_attr": "gpt_client",
        "retry_fn": summarizer_gpt.retry_generate,
        "summarize_fn": summarizer_gpt.summarize_person,
        "model_name": summarizer_gpt.SUMMARY_MODEL_NAME,
    },
}


def build_generate_fn_kwargs(engine: str, client, model_name: str, prompt: str) -> tuple:
    """
    Trả về (generate_fn, base_kwargs) đúng dạng generate_with_length_limit() cần,
    khác nhau giữa Gemini (bound method) và gpt-oss (cần truyền client qua kwargs).
    """
    if engine == "gemini":
        return client.models.generate_content, {
            "model": model_name, "contents": prompt, "config": {"temperature": 0.0},
        }
    return summarizer_gpt.generate_content_gpt, {
        "client": client, "model": model_name, "contents": prompt, "config": {"temperature": 0.0},
    }
