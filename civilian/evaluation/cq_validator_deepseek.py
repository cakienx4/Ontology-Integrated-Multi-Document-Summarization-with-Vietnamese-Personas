"""
cq_validator_deepseek.py

Chạy pipeline persona cho từng Competency Question (CQ) trong cq_test_cases_MINI.json,
sinh bản tóm tắt cho từng person, dùng model DeepSeek (OpenRouter)
làm judge để đánh giá PASS / FAIL / UNCLEAR theo expected_effect.

    python cq_validator_deepseek.py
    python cq_validator_deepseek.py --no-judge          # chỉ sinh tóm tắt, không gọi LLM judge

Xuất:
  - cq_validation_report_deepseek.md
  - cq_validation_results_deepseek.json
"""

import argparse
import json
import os
import sys
import time
import traceback
from datetime import datetime
import re
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pipeline.ontology_context import load_graph
from pipeline.summarizer_deepseek import summarize_person, retry_generate, get_client, MODEL_NAME

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_CSV = os.path.join(BASE_DIR, "..", "data", "sample50.csv")
TTL_PATH = os.path.join(BASE_DIR, "..", "ontology", "persona_analysis_3.ttl")
TEST_CASES_PATH = os.path.join(BASE_DIR, "cq_test_cases.json")

OUT_MD   = os.path.join(BASE_DIR, "cq_validation_report_deepseek_2.md")
OUT_JSON = os.path.join(BASE_DIR, "cq_validation_results_deepseek_2.json")

SUMMARY_MODEL_NAME = MODEL_NAME
JUDGE_MODEL_NAME   = MODEL_NAME


def load_test_cases() -> dict:
    with open(TEST_CASES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_row(df: pd.DataFrame, row_index: int) -> dict:
    return df.iloc[row_index].to_dict()


def build_judge_prompt(cq: dict, summary_a: str, summary_b: str = None) -> str:
    if cq["type"] == "single_constraint":
        instruction = f"""
Bạn là người đánh giá độc lập (judge) cho một hệ thống tóm tắt văn bản cá nhân hóa.

Competency Question (CQ): {cq['question']}
Ràng buộc cần kiểm tra: {cq.get('note', '')}
Kỳ vọng (expected_effect): {cq['expected_effect']}
Câu hỏi đánh giá cụ thể: {cq['judge_question']}

Đây là bản tóm tắt cần đánh giá:
---
{summary_a}
---

Hãy đánh giá xem bản tóm tắt trên có thỏa mãn ràng buộc / kỳ vọng nêu trên không.
"""
    else:
        instruction = f"""
Bạn là người đánh giá độc lập (judge) cho một hệ thống tóm tắt văn bản cá nhân hóa.

Competency Question (CQ): {cq['question']}
Kỳ vọng (expected_effect): {cq['expected_effect']}
Câu hỏi đánh giá cụ thể: {cq['judge_question']}

Đây là bản tóm tắt A (person: {cq['person_a']['label']}):
---
{summary_a}
---

Đây là bản tóm tắt B (person: {cq['person_b']['label']}):
---
{summary_b}
---

Hãy so sánh hai bản tóm tắt và đánh giá xem sự khác biệt giữa chúng có đúng theo
chiều mà expected_effect mô tả không.
"""

    instruction += """
QUAN TRỌNG: Chỉ trả về JSON thuần túy, không thêm markdown, không thêm giải thích ngoài JSON, theo đúng schemas sau. Trường "confidence" PHẢI là số thực viết bằng CHỮ SỐ với dấu CHẤM thập phân (ví dụ: 0.8) — TUYỆT ĐỐI không viết bằng chữ (sai: "zero point nine"), không dùng dấu phẩy (sai: 0,8):
{
  "verdict": "PASS" | "FAIL" | "UNCLEAR",
  "confidence": <số thực 0.0 đến 1.0>,
  "reasoning": "<giải thích ngắn gọn 2-4 câu bằng tiếng Việt>"
}
"""
    return instruction


_NUMBER_WORDS = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    "point": ".",
}

def _sanitize_confidence(cleaned: str) -> str:
    """
    Sửa các trường hợp model viết confidence không đúng chuẩn JSON,
    ví dụ '0.nine' -> '0.9'. Nếu không quy đổi được, fallback về 0.5
    thay vì làm json.loads() thất bại toàn bộ.
    """
    match = re.search(r'"confidence"\s*:\s*([^,}]+)', cleaned)
    if not match:
        return cleaned

    raw_val = match.group(1).strip()
    try:
        float(raw_val)
        return cleaned
    except ValueError:
        pass

    fixed = raw_val.lower()
    for word, digit in _NUMBER_WORDS.items():
        fixed = re.sub(rf'\b{word}\b', digit, fixed)
    fixed = fixed.replace(",", ".").replace(" ", "")
    fixed = re.sub(r'[^0-9.]', "", fixed)

    try:
        float(fixed)
    except ValueError:
        print(f"    [DEBUG-JUDGE] Không sanitize được confidence: {raw_val!r}, fallback 0.5")
        fixed = "0.5"

    return cleaned[:match.start(1)] + fixed + cleaned[match.end(1):]


def call_judge(cq: dict, summary_a: str, summary_b: str, client: OpenAI) -> dict:
    prompt = build_judge_prompt(cq, summary_a, summary_b)
    try:
        response = client.chat.completions.create(
            model=JUDGE_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=2048,
        )
        raw = response.choices[0].message.content
        if not raw:
            return {
                "verdict": "UNCLEAR",
                "confidence": 0.0,
                "reasoning": "Model trả về response rỗng (None)",
                "raw_response": "",
            }
        raw = raw.strip()
        cleaned = raw.replace("```json", "").replace("```", "").strip()
        cleaned = _sanitize_confidence(cleaned)
        parsed  = json.loads(cleaned)
        return {
            "verdict":      parsed.get("verdict", "UNCLEAR"),
            "confidence":   parsed.get("confidence", 0.0),
            "reasoning":    parsed.get("reasoning", ""),
            "raw_response": raw,
        }
    except Exception as e:
        return {
            "verdict":      "UNCLEAR",
            "confidence":   0.0,
            "reasoning":    f"Lỗi khi gọi/parse judge: {e}",
            "raw_response": "",
        }


def run_validation(cq_filter=None, do_judge=True):
    data = load_test_cases()
    texts = data["texts"]
    test_cases = data["test_cases"]

    if cq_filter:
        test_cases = [c for c in test_cases if c["cq_id"] in cq_filter]

    client = get_client()

    df = pd.read_csv(DATA_CSV)
    g = load_graph(TTL_PATH)

    results = []

    for cq in test_cases:
        print(f"\n=== {cq['cq_id']}: {cq['question'][:60]}... ===")
        text = texts[cq["text_id"]]
        case_result = {
            "cq_id": cq["cq_id"],
            "question": cq["question"],
            "type": cq["type"],
            "field_under_test": cq.get("field_under_test", ""),
            "expected_effect": cq["expected_effect"],
        }

        try:
            row_a = get_row(df, cq["person_a"]["row_index"])
            print(f"  [A] {cq['person_a']['label']} -> đang tóm tắt...")

            #  SỬA: Gọi trực tiếp summarize_person
            result_a = summarize_person(
                row=row_a,
                text=text,
                g=g,
                client=client,
            )
            case_result["person_a"] = {**cq["person_a"], "summary": result_a["summary"]}

            if cq["type"] == "pair_comparison":
                row_b = get_row(df, cq["person_b"]["row_index"])
                print(f"  [B] {cq['person_b']['label']} -> đang tóm tắt...")

                #  SỬA: Gọi trực tiếp summarize_person
                result_b = summarize_person(
                    row=row_b,
                    text=text,
                    g=g,
                    client=client,
                )
                case_result["person_b"] = {**cq["person_b"], "summary": result_b["summary"]}
                summary_b = result_b["summary"]
            else:
                summary_b = None

            if do_judge:
                print("  -> đang gọi LLM judge...")

                #  SỬA: Gọi trực tiếp call_judge
                judge_result = call_judge(
                    cq=cq,
                    summary_a=result_a["summary"],
                    summary_b=summary_b,
                    client=client
                )
                case_result["judge"] = judge_result
                print(f"  => {judge_result['verdict']} (confidence={judge_result['confidence']})")
            else:
                case_result["judge"] = None

            case_result["status"] = "OK"

        except Exception as e:
            print(f"  !!! LỖI: {e}")
            case_result["status"] = "ERROR"
            case_result["error"] = str(e)
            case_result["error_trace"] = traceback.format_exc()

        results.append(case_result)
        time.sleep(1)

    return results


# ── EXPORT ───────────────────────────────────────────────────────────────────

def export_json(results: list):
    payload = {
        "generated_at": datetime.now().isoformat(),
        "summary_model": SUMMARY_MODEL_NAME,
        "judge_model":   JUDGE_MODEL_NAME,
        "results":       results,
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\nĐã ghi kết quả JSON: {OUT_JSON}")


def export_markdown(results: list):
    lines = []
    lines.append("# Báo cáo validate Competency Questions (CQ)")
    lines.append(f"\nThời gian sinh: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Model tóm tắt: `{SUMMARY_MODEL_NAME}` | Model judge: `{JUDGE_MODEL_NAME}`\n")

    n_pass    = sum(1 for r in results if r.get("judge") and r["judge"]["verdict"] == "PASS")
    n_fail    = sum(1 for r in results if r.get("judge") and r["judge"]["verdict"] == "FAIL")
    n_unclear = sum(1 for r in results if r.get("judge") and r["judge"]["verdict"] == "UNCLEAR")
    n_error   = sum(1 for r in results if r.get("status") == "ERROR")

    lines.append("## Tổng quan")
    lines.append(f"- Tổng số CQ: {len(results)}")
    lines.append(f"- PASS: {n_pass} | FAIL: {n_fail} | UNCLEAR: {n_unclear} | ERROR: {n_error}\n")

    lines.append("| CQ | Verdict | Confidence | Trường kiểm tra |")
    lines.append("|---|---|---|---|")
    for r in results:
        verdict = r["judge"]["verdict"] if r.get("judge") else r.get("status", "?")
        conf    = r["judge"]["confidence"] if r.get("judge") else "-"
        lines.append(f"| {r['cq_id']} | {verdict} | {conf} | {r.get('field_under_test','')} |")
    lines.append("")

    for r in results:
        lines.append(f"\n---\n## {r['cq_id']}: {r['question']}")
        lines.append(f"**Trường kiểm tra:** {r.get('field_under_test', '')}\n")
        lines.append(f"**Loại test:** {r.get('type', '')}\n")
        lines.append(f"**Kỳ vọng (expected_effect):** {r.get('expected_effect', '')}\n")

        if r.get("status") == "ERROR":
            lines.append(f"**LỖI:** {r.get('error', '')}\n")
            continue

        pa = r.get("person_a", {})
        lines.append(f"### Person A — {pa.get('label', '')}")
        lines.append(f"```\n{pa.get('summary', '')}\n```\n")

        if "person_b" in r:
            pb = r["person_b"]
            lines.append(f"### Person B — {pb.get('label', '')}")
            lines.append(f"```\n{pb.get('summary', '')}\n```\n")

        if r.get("judge"):
            j = r["judge"]
            lines.append("### Đánh giá LLM judge")
            lines.append(f"- **Verdict:** {j['verdict']}\n")
            lines.append(f"- **Confidence:** {j['confidence']}\n")
            lines.append(f"- **Lý do:** {j['reasoning']}\n")

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Đã ghi báo cáo Markdown: {OUT_MD}")


# ── ENTRYPOINT ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Validate Competency Questions cho hệ thống persona (DeepSeek).")
    parser.add_argument("--cq", nargs="*", default=None,
                        help="Chỉ chạy các CQ chỉ định, ví dụ: --cq CQ1 CQ8")
    parser.add_argument("--no-judge", action="store_true",
                        help="Không gọi LLM judge, chỉ sinh tóm tắt")
    args = parser.parse_args()

    results = run_validation(cq_filter=args.cq, do_judge=not args.no_judge)
    export_json(results)
    export_markdown(results)


if __name__ == "__main__":
    main()