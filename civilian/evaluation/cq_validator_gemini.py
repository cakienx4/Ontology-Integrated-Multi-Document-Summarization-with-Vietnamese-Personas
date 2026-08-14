"""
    python cq_validator_gemini.py
    python cq_validator_gemini.py --no-judge          # chỉ sinh tóm tắt, không gọi LLM judge
"""

import argparse
import json
import os
import sys
import time
import traceback
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
from google import genai
load_dotenv()
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pipeline.ontology_context import load_graph
from pipeline.civilian.summarizer_gemini import summarize_person, retry_generate

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_CSV = os.path.join(BASE_DIR, "..", "data", "sample50.csv")
TTL_PATH = os.path.join(BASE_DIR, "..", "ontology", "persona_analysis_3.ttl")
TEST_CASES_PATH = os.path.join(BASE_DIR, "cq_test_cases.json")

OUT_MD = os.path.join(BASE_DIR, "cq_validation_report_gemini.md")
OUT_JSON = os.path.join(BASE_DIR, "cq_validation_results_gemini.json")

SUMMARY_MODEL_NAME = "gemini-3.1-flash-lite"
JUDGE_MODEL_NAME = "gemini-3.1-flash-lite"

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
QUAN TRỌNG: Chỉ trả về JSON thuần túy, không thêm markdown, không thêm giải thích
ngoài JSON, theo đúng schemas sau:
{
  "verdict": "PASS" | "FAIL" | "UNCLEAR",
  "confidence": <số thực 0.0 đến 1.0>,
  "reasoning": "<giải thích ngắn gọn 2-4 câu bằng tiếng Việt>"
}
"""
    return instruction


def call_judge(cq: dict, summary_a: str, summary_b: str, client: genai.Client) -> dict:
    prompt = build_judge_prompt(cq, summary_a, summary_b)

    response = retry_generate(
        client.models.generate_content,
        model=JUDGE_MODEL_NAME,
        contents=prompt,
        config={"temperature": 0.0}
    )

    raw = response.text.strip()

    cleaned = (
        raw.replace("```json", "")
           .replace("```", "")
           .strip()
    )

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return {
            "verdict": "UNCLEAR",
            "confidence": 0.0,
            "reasoning": "Judge không trả về đúng định dạng JSON.",
            "raw_response": raw,
        }

    return {
        "verdict": parsed.get("verdict", "UNCLEAR"),
        "confidence": parsed.get("confidence", 0.0),
        "reasoning": parsed.get("reasoning", ""),
        "raw_response": raw,
    }


def run_validation(cq_filter=None, do_judge=True, api_key=None):
    data = load_test_cases()
    texts = data["texts"]
    test_cases = data["test_cases"]

    if cq_filter:
        test_cases = [c for c in test_cases if c["cq_id"] in cq_filter]

    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("Chưa set GEMINI_API_KEY. Chạy: export GEMINI_API_KEY=your_key")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

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
            result_a = retry_generate(
                summarize_person,
                row_a,
                text,
                g,
                client,
            )
            case_result["person_a"] = {**cq["person_a"], "summary": result_a["summary"]}

            if cq["type"] == "pair_comparison":
                row_b = get_row(df, cq["person_b"]["row_index"])
                print(f"  [B] {cq['person_b']['label']} -> đang tóm tắt...")
                result_b = retry_generate(
                    summarize_person,
                    row_b,
                    text,
                    g,
                    client,
                )
                case_result["person_b"] = {**cq["person_b"], "summary": result_b["summary"]}
                summary_b = result_b["summary"]
            else:
                summary_b = None

            if do_judge:
                print("  -> đang gọi LLM judge...")
                judge_result = retry_generate(
                    call_judge,
                    cq,
                    result_a["summary"],
                    summary_b,
                    client,
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
        time.sleep(1)  # tránh rate limit

    return results


def export_json(results: list):
    payload = {
        "generated_at": datetime.now().isoformat(),
        "summary_model": SUMMARY_MODEL_NAME,
        "judge_model": JUDGE_MODEL_NAME,
        "results": results,
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\nĐã ghi kết quả JSON: {OUT_JSON}")


def export_markdown(results: list):
    lines = []
    lines.append(f"# Báo cáo validate Competency Questions (CQ)")
    lines.append(f"\nThời gian sinh: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Model tóm tắt: `{SUMMARY_MODEL_NAME}` | Model judge: `{JUDGE_MODEL_NAME}`\n")

    n_pass = sum(1 for r in results if r.get("judge") and r["judge"]["verdict"] == "PASS")
    n_fail = sum(1 for r in results if r.get("judge") and r["judge"]["verdict"] == "FAIL")
    n_unclear = sum(1 for r in results if r.get("judge") and r["judge"]["verdict"] == "UNCLEAR")
    n_error = sum(1 for r in results if r.get("status") == "ERROR")

    lines.append("## Tổng quan")
    lines.append(f"- Tổng số CQ: {len(results)}")
    lines.append(f"- PASS: {n_pass} | FAIL: {n_fail} | UNCLEAR: {n_unclear} | ERROR: {n_error}\n")

    lines.append("| CQ | Verdict | Confidence | Trường kiểm tra |")
    lines.append("|---|---|---|---|")
    for r in results:
        verdict = r["judge"]["verdict"] if r.get("judge") else (r.get("status", "?"))
        conf = r["judge"]["confidence"] if r.get("judge") else "-"
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
            lines.append(f"### Đánh giá LLM judge")
            lines.append(f"- **Verdict:** {j['verdict']}\n")
            lines.append(f"- **Confidence:** {j['confidence']}\n")
            lines.append(f"- **Lý do:** {j['reasoning']}\n")

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Đã ghi báo cáo Markdown: {OUT_MD}")


def main():
    parser = argparse.ArgumentParser(description="Validate Competency Questions cho hệ thống persona.")
    parser.add_argument("--cq", nargs="*", default=None, help="Chỉ chạy các CQ chỉ định, ví dụ: --cq CQ1 CQ8")
    parser.add_argument("--no-judge", action="store_true", help="Không gọi LLM judge, chỉ sinh tóm tắt")
    parser.add_argument("--api-key", default=None, help="Gemini API key (mặc định lấy từ env GEMINI_API_KEY)")
    args = parser.parse_args()

    results = run_validation(cq_filter=args.cq, do_judge=not args.no_judge, api_key=args.api_key)
    export_json(results)
    export_markdown(results)


if __name__ == "__main__":
    main()
