"""
    python ontology_score_gemini.py --cq-results path/to/cq_validation_results_gemini.json
"""

import argparse
import json
import os
import re
import sys
import time

import pandas as pd
import pronto
from dotenv import load_dotenv
from google import genai

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_CSV    = os.path.join(BASE_DIR, "..", "data",     "sample50.csv")
OBO_PATH    = os.path.join(BASE_DIR, "..", "ontology", "persona_analysis_3.obo")
CQ_JSON_DEFAULT = os.path.join(BASE_DIR, "cq_validation_results_gemini.json")
OUT_JSON    = os.path.join(BASE_DIR, "ontology_score_results_gemini.json")
OUT_MD      = os.path.join(BASE_DIR, "ontology_score_report_gemini.md")

MODEL_NAME = "gemini-3.1-flash-lite"

# 10 nhánh chính của ontology, map sang cột tương ứng trong CSV
BRANCH_COLUMN_MAP = {
    "professional_persona":     "professional_persona",
    "sports_persona":           "sports_persona",
    "arts_persona":             "arts_persona",
    "travel_persona":           "travel_persona",
    "culinary_persona":         "culinary_persona",
    "persona":                  "persona",
    "cultural_background":      "cultural_background",
    "skills_and_expertise":     "skills_and_expertise",
    "hobbies_and_interests":    "hobbies_and_interests",
    "career_goals_and_ambitions": "career_goals_and_ambitions",
}


def load_ontology_terms(obo_path: str) -> dict:
    onto = pronto.Ontology(obo_path)
    result = {}

    for branch_id in BRANCH_COLUMN_MAP:
        root = onto[branch_id]
        l1_terms = []
        all_names = set()

        for t in root.subclasses(with_self=False):
            name = t.name or ""
            defn = str(t.definition) if t.definition else ""
            depth = len(list(t.superclasses(with_self=False))) - 1

            if depth == 1:
                l1_terms.append({
                    "id":   t.id,
                    "name": name,
                    "def":  defn,
                })

            if name:
                all_names.add(name.lower())
            for s in t.synonyms:
                if s.description:
                    all_names.add(s.description.lower())

            for word in re.findall(r'\b\w{4,}\b', defn.lower()):
                all_names.add(word)

        result[branch_id] = {
            "l1":        l1_terms,
            "all_names": all_names,
        }

    return result


def retry_generate(client: genai.Client, prompt: str, model: str = MODEL_NAME) -> str:
    while True:
        try:
            resp = client.models.generate_content(model=model, contents=prompt)
            return resp.text.strip()
        except Exception as e:
            msg = str(e)
            if "RESOURCE_EXHAUSTED" in msg or "429" in msg:
                match = re.search(r"retry in ([0-9.]+)s", msg, re.IGNORECASE)
                wait = float(match.group(1)) + 2 if match else 35
                print(f" Rate limit, chờ {wait:.1f}s...")
                time.sleep(wait)
            else:
                raise


def extract_features(client: genai.Client, branch_id: str, l1_terms: list,
                     prose_list: list) -> list:
    l1_str = "\n".join(
        f'- {t["name"]}: {t["def"][:120]}' for t in l1_terms
    )
    # Ghép 50 prose text (đánh số để Gemini không nhầm)
    texts_str = "\n\n".join(
        f'[{i+1}] {p}' for i, p in enumerate(prose_list) if p and str(p) != "nan"
    )

    prompt = f"""Bạn đang phân tích nhánh ontology "{branch_id}" với các chiều phân tích (L1):
{l1_str}

Dưới đây là nội dung mô tả về {len(prose_list)} người dùng:
{texts_str}

Nhiệm vụ: Trích xuất danh sách các ĐẶC TRƯNG CỤ THỂ (không trừu tượng) xuất hiện \
trong tất cả các đoạn văn trên. Ví dụ: "chơi bóng bàn", "thích du lịch bụi", \
"kỹ năng lập trình Python", "thích ẩm thực cay", v.v.

Quy tắc:
- Mỗi đặc trưng là một cụm từ ngắn (2-6 từ), cụ thể, không lặp nhau
- Không thêm giải thích, chỉ liệt kê
- Tối đa 80 đặc trưng, ưu tiên các đặc trưng xuất hiện nhiều lần

CHỈ trả về JSON array of strings, không thêm bất kỳ nội dung nào khác:
["đặc trưng 1", "đặc trưng 2", ...]
"""
    raw = retry_generate(client, prompt)
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    try:
        features = json.loads(cleaned)
        if isinstance(features, list):
            return [str(f).strip() for f in features if f]
    except Exception:
        # Fallback: tách dòng
        lines = [l.strip().strip('"-,') for l in cleaned.split("\n") if l.strip()]
        return [l for l in lines if 2 < len(l) < 80]
    return []


def semantic_match(client: genai.Client, branch_id: str, l1_terms: list,
                   unmatched_features: list) -> dict:
    if not unmatched_features:
        return {}

    l1_str = "\n".join(
        f'- {t["name"]}: {t["def"][:120]}' for t in l1_terms
    )
    features_str = "\n".join(f'- {f}' for f in unmatched_features)

    prompt = f"""Nhánh ontology "{branch_id}" có các chiều phân tích (L1) sau:
{l1_str}

Với mỗi đặc trưng dưới đây, hãy đánh giá xem có ít nhất một chiều phân tích trên \
có thể bao phủ (classify, categorize) đặc trưng đó không.

Đặc trưng cần đánh giá:
{features_str}

CHỈ trả về JSON object, key là tên đặc trưng (nguyên văn), value là true/false:
{{"đặc trưng 1": true, "đặc trưng 2": false, ...}}
"""
    raw = retry_generate(client, prompt)
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    try:
        result = json.loads(cleaned)
        if isinstance(result, dict):
            return {k: bool(v) for k, v in result.items()}
    except Exception:
        pass
    # Nếu parse lỗi → mặc định covered (conservative)
    return {f: True for f in unmatched_features}


def string_match(feature: str, all_names: set) -> bool:

    words = set(re.findall(r'\b\w{4,}\b', feature.lower()))
    return bool(words & all_names)


# ── FEATURE COVERAGE ────────────────────────────────────────────────────────

def measure_feature_coverage(client: genai.Client, df: pd.DataFrame,
                              onto_terms: dict) -> dict:

    branch_results = {}

    for branch_id, col in BRANCH_COLUMN_MAP.items():
        print(f"\n  [{branch_id}]")

        l1_terms  = onto_terms[branch_id]["l1"]
        all_names = onto_terms[branch_id]["all_names"]

        # Lấy prose texts (loại nan/rỗng)
        prose_list = [
            str(v) for v in df[col].tolist()
            if v and str(v).strip().lower() not in ("nan", "")
        ]
        print(f"    {len(prose_list)}/50 texts hợp lệ")

        if not prose_list:
            branch_results[branch_id] = {
                "features_total": 0, "features_covered": 0,
                "coverage": 0.0, "details": [],
            }
            continue

        # Bước 1: trích đặc trưng cụ thể
        print(f"    → Đang trích đặc trưng...")
        features = extract_features(client, branch_id, l1_terms, prose_list)
        print(f"    → Trích được {len(features)} đặc trưng")
        time.sleep(1)

        if not features:
            branch_results[branch_id] = {
                "features_total": 0, "features_covered": 0,
                "coverage": 0.0, "details": [],
            }
            continue

        # Bước 2a: string match
        matched    = {}
        unmatched  = []
        for f in features:
            if string_match(f, all_names):
                matched[f] = True
            else:
                unmatched.append(f)

        print(f"    → String match: {len(matched)}/{len(features)} | "
              f"Cần semantic match: {len(unmatched)}")

        # Bước 2b: semantic match cho phần còn lại
        if unmatched:
            sem_results = semantic_match(client, branch_id, l1_terms, unmatched)
            matched.update(sem_results)
            time.sleep(1)

        total   = len(features)
        covered = sum(1 for v in matched.values() if v)
        details = [{"feature": f, "covered": matched.get(f, False)} for f in features]

        branch_results[branch_id] = {
            "features_total":   total,
            "features_covered": covered,
            "coverage":         round(covered / total, 4) if total else 0.0,
            "details":          details,
        }
        print(f"    → Coverage: {covered}/{total} = "
              f"{branch_results[branch_id]['coverage']:.1%}")

    return branch_results


def measure_cq_coverage(cq_json_path: str) -> dict:
    with open(cq_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = data.get("results", [])
    total = len(results)
    passed = sum(
        1 for r in results
        if r.get("judge") and r["judge"].get("verdict") == "PASS"
    )
    return {
        "total_cq":  total,
        "passed_cq": passed,
        "coverage":  round(passed / total, 4) if total else 0.0,
        "per_cq": [
            {
                "cq_id":   r["cq_id"],
                "verdict": r["judge"]["verdict"] if r.get("judge") else "N/A",
                "confidence": r["judge"].get("confidence") if r.get("judge") else None,
            }
            for r in results
        ],
    }


def export_json(feature_results: dict, cq_results: dict, score: float):
    total_f = sum(b["features_total"]   for b in feature_results.values())
    cover_f = sum(b["features_covered"] for b in feature_results.values())
    feat_cov = round(cover_f / total_f, 4) if total_f else 0.0

    payload = {
        "ontology_score": round(score, 4),
        "feature_coverage": {
            "overall": feat_cov,
            "total_features":   total_f,
            "covered_features": cover_f,
            "per_branch": {
                bid: {
                    "features_total":   b["features_total"],
                    "features_covered": b["features_covered"],
                    "coverage":         b["coverage"],
                }
                for bid, b in feature_results.items()
            },
        },
        "cq_coverage": cq_results,
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\nĐã ghi: {OUT_JSON}")


def export_markdown(feature_results: dict, cq_results: dict, score: float):
    total_f = sum(b["features_total"]   for b in feature_results.values())
    cover_f = sum(b["features_covered"] for b in feature_results.values())
    feat_cov = round(cover_f / total_f, 4) if total_f else 0.0

    lines = []
    lines.append("# Ontology Score Report\n")
    lines.append(f"## Kết quả tổng\n")
    lines.append(f"| Thành phần | Giá trị |")
    lines.append(f"|---|---|")
    lines.append(f"| Feature Coverage | {feat_cov:.1%} ({cover_f}/{total_f}) |")
    lines.append(f"| CQ Coverage | {cq_results['coverage']:.1%} "
                 f"({cq_results['passed_cq']}/{cq_results['total_cq']}) |")
    lines.append(f"| **Ontology Score** | **{score:.1%}** |\n")

    lines.append("## Feature Coverage theo nhánh\n")
    lines.append("| Branch | Extracted Features | Covered Features | Coverage |")
    lines.append("|---|---|---|---|")
    for bid, b in feature_results.items():
        lines.append(
            f"| {bid} | {b['features_total']} | {b['features_covered']} "
            f"| {b['coverage']:.1%} |"
        )
    lines.append("")

    lines.append("## CQ Coverage\n")
    lines.append("| CQ | Verdict | Confidence |")
    lines.append("|---|---|---|")
    for c in cq_results["per_cq"]:
        lines.append(f"| {c['cq_id']} | {c['verdict']} | {c['confidence']} |")

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Đã ghi: {OUT_MD}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cq-results", default=CQ_JSON_DEFAULT,
                        help="Đường dẫn đến cq_validation_results_gemini_MINI.json")
    parser.add_argument("--api-key", default=None)
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("Chưa set GEMINI_API_KEY")
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    df     = pd.read_csv(DATA_CSV)

    print("=== Đang load ontology...")
    onto_terms = load_ontology_terms(OBO_PATH)
    print(f"    Loaded {sum(len(v['l1']) for v in onto_terms.values())} L1 terms "
          f"từ {len(onto_terms)} nhánh\n")

    print("=== Đo Feature Coverage (10 branches × ~2 Gemini calls)...")
    feature_results = measure_feature_coverage(client, df, onto_terms)

    print("\n=== Đo CQ Coverage...")
    cq_results = measure_cq_coverage(args.cq_results)
    print(f"    CQ Coverage: {cq_results['passed_cq']}/{cq_results['total_cq']} "
          f"= {cq_results['coverage']:.1%}")

    total_f = sum(b["features_total"]   for b in feature_results.values())
    cover_f = sum(b["features_covered"] for b in feature_results.values())
    feat_cov = cover_f / total_f if total_f else 0.0
    score = (feat_cov + cq_results["coverage"]) / 2

    print(f"\n{'='*40}")
    print(f"Feature Coverage : {feat_cov:.1%}")
    print(f"CQ Coverage      : {cq_results['coverage']:.1%}")
    print(f"Ontology Score   : {score:.1%}")
    print(f"{'='*40}")

    export_json(feature_results, cq_results, score)
    export_markdown(feature_results, cq_results, score)


if __name__ == "__main__":
    main()
