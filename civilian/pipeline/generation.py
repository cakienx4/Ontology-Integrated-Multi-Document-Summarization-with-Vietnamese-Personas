"""
pipeline/generation.py

Các hàm sinh tóm tắt có kiểm soát độ dài (retry nếu vượt tỉ lệ cho phép).
KHÔNG hardcode provider cụ thể (Gemini/gpt-oss) — generate_fn/summarize_fn/retry_fn
được truyền vào từ nơi gọi (main.py, main_gpt.py, api/services/summary_service.py),
để dùng chung được cho cả 2 model, tránh duplicate logic ở nhiều nơi.
"""

MAX_LENGTH_RETRIES = 2


def check_length(summary: str, source: str, ratio: float = 0.7) -> tuple[bool, int, int]:
    src_words = len(source.split())
    sum_words = len(summary.split())
    return sum_words <= ratio * src_words, sum_words, int(ratio * src_words)


def generate_with_length_limit(generate_fn, retry_fn, source_text: str, base_kwargs: dict,
                                 prompt_key: str, ratio: float = 0.7):
    """
    generate_fn: hàm gọi model — vd client.models.generate_content (Gemini)
                 hoặc generate_content_gpt (gpt-oss, xem summarizer_gpt.py)
    retry_fn: hàm retry TƯƠNG ỨNG cùng provider với generate_fn — retry_generate
              của summarizer_gemini.py hoặc summarizer_gpt.py
    base_kwargs: kwargs truyền vào generate_fn, PHẢI chứa prompt_key (vd "contents")
                 để hàm này sửa lại prompt ở các lần retry
    """
    attempt = 0
    feedback = ""
    last_summary = None
    last_count = None
    max_words = None

    while attempt <= MAX_LENGTH_RETRIES:
        kwargs = dict(base_kwargs)
        if feedback:
            kwargs[prompt_key] = kwargs[prompt_key] + f"\n\n[YÊU CẦU BỔ SUNG DO VI PHẠM ĐỘ DÀI]\n{feedback}"

        response = retry_fn(generate_fn, **kwargs)
        summary = response.text.strip() if hasattr(response, "text") else response["summary"].strip()

        ok, sum_words, max_words = check_length(summary, source_text, ratio)
        last_summary, last_count = summary, sum_words

        if ok:
            return summary, {"length_ok": True, "words": sum_words, "max_words": max_words, "attempts": attempt + 1}

        feedback = (f"Bản tóm tắt trước có {sum_words} từ, vượt quá giới hạn {max_words} từ "
                    f"(tối đa {int(ratio*100)}% số từ bản gốc). Hãy viết lại NGẮN HƠN, "
                    f"cắt bớt chi tiết phụ, không thêm câu mới.")
        attempt += 1

    return last_summary, {"length_ok": False, "words": last_count, "max_words": max_words, "attempts": attempt}


def generate_specific_with_length_limit(summarize_fn, retry_fn, row, text, g, client, ratio: float = 0.7):
    """
    summarize_fn: summarize_person của summarizer_gemini.py hoặc summarizer_gpt.py
    retry_fn: retry_generate TƯƠNG ỨNG cùng provider với summarize_fn
    """
    attempt = 0
    feedback = ""
    result = None
    sum_words = None
    max_words = None

    while attempt <= MAX_LENGTH_RETRIES:
        result = retry_fn(summarize_fn, row, text, g, client, extra_instruction=feedback)
        ok, sum_words, max_words = check_length(result["summary"], text, ratio)

        if ok:
            return result, {"length_ok": True, "words": sum_words, "max_words": max_words, "attempts": attempt + 1}

        feedback = (f"Bản tóm tắt trước có {sum_words} từ, vượt quá giới hạn {max_words} từ. "
                    f"Viết lại ngắn hơn, cắt chi tiết phụ, không thêm câu mới.")
        attempt += 1

    return result, {"length_ok": False, "words": sum_words, "max_words": max_words, "attempts": attempt}
