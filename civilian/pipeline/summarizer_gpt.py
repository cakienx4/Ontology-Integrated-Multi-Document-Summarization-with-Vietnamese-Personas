import re
import time
from types import SimpleNamespace

import httpx
from openai import OpenAI

from community import determine_community
from worlds import build_worlds
from prompt_builder import build_prompt

# CẤU HÌNH MODEL
OSS_HOST   = "https://text-sum-gpt-oss-120b-runai-text-sum.runai-inference.cyberspace.vn"
MODEL_NAME = "gpt-oss-120b"
API_KEY    = "EMPTY"

SUMMARY_MODEL_NAME = MODEL_NAME

MAX_RETRY_ATTEMPTS = 3


def get_client() -> OpenAI:
    return OpenAI(
        api_key=API_KEY,
        base_url=f"{OSS_HOST}/v1",
        http_client=httpx.Client(
            verify=False,
            timeout=httpx.Timeout(connect=10.0, read=900.0, write=60.0, pool=10.0),
        ),
        max_retries=0,
    )


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
                    f"gpt-oss-120b vẫn lỗi sau {MAX_RETRY_ATTEMPTS} lần retry: {msg}"
                ) from e

            if any(k in msg for k in ("429", "rate", "RESOURCE_EXHAUSTED", "overloaded")):
                match = re.search(r"retry in ([0-9.]+)s", msg, re.IGNORECASE)
                wait = float(match.group(1)) + 2 if match else 35
                print(f"\nRate limit. Đợi {wait:.1f}s... (lần {attempt}/{MAX_RETRY_ATTEMPTS})")
                time.sleep(wait)
                continue

            if any(k in msg for k in ("429", "rate", "RESOURCE_EXHAUSTED", "overloaded")):
                match = re.search(r"retry in ([0-9.]+)s", msg, re.IGNORECASE)
                wait = float(match.group(1)) + 2 if match else 35
                print(f"\nRate limit. Đợi {wait:.1f}s... (lần {attempt}/{MAX_RETRY_ATTEMPTS})")
                time.sleep(wait)
                continue

            if any(k in msg.lower() for k in ("timeout", "timed out")):
                wait = 20 * attempt  # backoff tang dan: 20s, 40s, 60s, 80s, 100s
                print(f"\nRequest timed out (model cham hoac prompt qua dai). "
                      f"Đợi {wait}s rồi thử lại... (lần {attempt}/{MAX_RETRY_ATTEMPTS})")
                time.sleep(wait)
                continue

            raise


def summarize_person(row: dict, text: str, g, client: OpenAI,
                      model_name: str = SUMMARY_MODEL_NAME,
                      extra_instruction: str = "") -> dict:
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
        extra_body={"reasoning_effort": "low"},
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


def generate_content_gpt(client: OpenAI, model: str, contents: str, config: dict | None = None):
    temperature = (config or {}).get("temperature", 0.0)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": contents}],
        temperature=temperature,
        max_tokens=8192,
        extra_body={"reasoning_effort": "low"},
    )
    raw = response.choices[0].message.content
    return SimpleNamespace(text=raw.strip() if raw else "")
