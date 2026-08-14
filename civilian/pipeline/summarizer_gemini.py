"""
pipeline/summarizer.py

Module tóm tắt văn bản cá nhân hóa theo persona.
Dùng chung cho pipeline chính (main.py) và eval (cq_validator_*.py).
"""

import re
import time

from google import genai

from pipeline.civilian.community import determine_community
from pipeline.civilian.worlds import build_worlds
from pipeline.civilian.prompt_builder import build_prompt

SUMMARY_MODEL_NAME = "gemini-3.1-flash-lite"

MAX_RETRY_ATTEMPTS = 5

def retry_generate(func, *args, **kwargs):
    attempt = 0
    while True:
        try:
            return func(*args, **kwargs)

        except Exception as e:
            msg = str(e)
            attempt += 1

            if attempt > MAX_RETRY_ATTEMPTS:
                raise RuntimeError(
                    f"Gemini vẫn lỗi sau {MAX_RETRY_ATTEMPTS} lần retry: {msg}"
                ) from e

            if "RESOURCE_EXHAUSTED" in msg or "429" in msg:
                match = re.search(r"retry in ([0-9.]+)s", msg, re.IGNORECASE)
                wait = float(match.group(1)) + 2 if match else 40
                print(f"\n429 quota. Đợi {wait:.1f}s... (lần {attempt}/{MAX_RETRY_ATTEMPTS})")
                time.sleep(wait)
                continue

            elif "503" in msg or "UNAVAILABLE" in msg:
                wait = 20
                print(f"\nServer bận. Đợi {wait}s... (lần {attempt}/{MAX_RETRY_ATTEMPTS})")
                time.sleep(wait)
                continue

            raise


def summarize_person(row: dict, text: str, g, client: genai.Client,
                      model_name: str = SUMMARY_MODEL_NAME,
                      extra_instruction: str = "") -> dict:
    """
    Sinh tóm tắt cá nhân hóa cho một person (row) dựa trên văn bản đầu vào (text)
    và đồ thị ontology (g).
    """
    community = determine_community(row)
    worlds = build_worlds(row)
    prompt = build_prompt(row, text, g)
    if extra_instruction:
        prompt += f"\n\n[YÊU CẦU BỔ SUNG DO VI PHẠM ĐỘ DÀI]\n{extra_instruction}"
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config={"temperature": 0.0},
    )

    summary = response.text.strip()
    return {
        "uuid": row.get("uuid", ""),
        "summary": summary,
        "community": community,
        "worlds": worlds,
        "prompt_len": len(prompt),
    }