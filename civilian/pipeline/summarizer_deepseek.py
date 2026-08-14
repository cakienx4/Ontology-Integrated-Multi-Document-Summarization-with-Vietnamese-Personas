"""
pipeline/summarizer_deepseek.py

Module tóm tắt văn bản cá nhân hóa theo persona.
Sử dụng model DeepSeek (deepseek/deepseek-chat hoặc deepseek-v4-flash) thông qua OpenRouter API.
Dùng chung cho pipeline chính (main_deepseek.py), eval (cq_validator_deepseek.py), và API (api/).
"""

import os
import re
import time
from types import SimpleNamespace

from dotenv import load_dotenv
from openai import OpenAI

from pipeline.civilian.community import determine_community
from pipeline.civilian.worlds import build_worlds
from pipeline.civilian.prompt_builder import build_prompt

# Nạp biến môi trường từ file .env
load_dotenv()

# ── CẤU HÌNH MODEL & OPENROUTER ─────────────────────────────
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MODEL_NAME = "deepseek/deepseek-v4-flash"

SUMMARY_MODEL_NAME = MODEL_NAME

MAX_RETRY_ATTEMPTS = 5  # Đồng bộ với các module summarizer khác


def get_client() -> OpenAI:
    """
    Khởi tạo OpenAI client kết nối tới OpenRouter API endpoint.
    Lấy API key từ biến môi trường OPENROUTER_API_KEY hoặc DEEPSEEK_API_KEY.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("Không tìm thấy OPENROUTER_API_KEY trong môi trường / file .env")

    return OpenAI(
        api_key=api_key,
        base_url=OPENROUTER_BASE_URL,
        timeout=180,
    )


def retry_generate(client: OpenAI, prompt: str, *args,
                   max_tokens: int = 4096, max_retries: int = 5, **kwargs) -> str:
    """
    Hàm retry linh hoạt. Đã thêm *args và **kwargs để chống lỗi truyền dư tham số positional.
    """
    # Nếu truyền thừa vị trí (ví dụ truyền model_name ở vị trí 3):
    # args[0] có thể là model_name hoặc max_tokens tùy nơi gọi
    if args:
        if isinstance(args[0], int):
            max_tokens = args[0]
        if len(args) > 1 and isinstance(args[1], int):
            max_retries = args[1]

    attempt = 0
    while True:
        try:
            resp = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                top_p=0.0001,
                seed=42,
                max_tokens=max_tokens,
            )

            finish_reason = resp.choices[0].finish_reason
            content = resp.choices[0].message.content
            print(f"    [DEBUG] finish_reason={finish_reason} | usage={resp.usage}")

            if not content or not content.strip():
                print(f"    [DEBUG] Content rỗng (finish_reason={finish_reason}), "
                      f"thử lại với max_tokens cao hơn...")
                resp = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    top_p=0.0001,
                    seed=42,
                    max_tokens=max(max_tokens * 2, 8192),
                )
                content = resp.choices[0].message.content

            return content.strip() if content else ""

        except Exception as e:
            msg = str(e)
            attempt += 1

            if attempt > max_retries:
                raise RuntimeError(
                    f"DeepSeek/OpenRouter vẫn lỗi sau {max_retries} lần retry: {msg}"
                ) from e

            if any(k in msg for k in ("429", "rate", "RESOURCE_EXHAUSTED", "overloaded", "quota")):
                match = re.search(r"retry in ([0-9.]+)s", msg, re.IGNORECASE)
                wait = float(match.group(1)) + 2 if match else 35
                print(f"\nRate limit. Đợi {wait:.1f}s... (lần {attempt}/{max_retries})")
                time.sleep(wait)
                continue

            raise


def summarize_person(row: dict, text: str, g, client: OpenAI,
                      model_name: str = SUMMARY_MODEL_NAME,
                      extra_instruction: str = "") -> dict:
    """
    Sinh tóm tắt cá nhân hóa cho một person (row) dựa trên văn bản đầu vào (text)
    và đồ thị ontology (g), dùng model DeepSeek qua OpenRouter.
    """
    community = determine_community(row)
    worlds = build_worlds(row)
    prompt = build_prompt(row, text, g)
    if extra_instruction:
        prompt += f"\n\n[YÊU CẦU BỔ SUNG DO VI PHẠM ĐỘ DÀI]\n{extra_instruction}"

    response = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=8192,
    )

    finish_reason = response.choices[0].finish_reason
    print(f"[DEBUG] finish_reason={finish_reason} | usage={response.usage}")

    raw_content = response.choices[0].message.content
    summary = raw_content.strip() if raw_content else ""

    return {
        "uuid": row.get("uuid", ""),
        "summary": summary,
        "community": community,
        "worlds": worlds,
        "prompt_len": len(prompt),
    }


def generate_content_deepseek(client: OpenAI, model: str, contents: str, config: dict | None = None):
    """
    Adapter: mô phỏng interface response.text của Gemini (client.models.generate_content)
    bằng OpenRouter/DeepSeek (client.chat.completions.create), để dùng chung được với
    pipeline/generation.py::generate_with_length_limit.
    """
    temperature = (config or {}).get("temperature", 0.0)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": contents}],
        temperature=temperature,
        max_tokens=8192,
    )
    raw = response.choices[0].message.content
    return SimpleNamespace(text=raw.strip() if raw else "")