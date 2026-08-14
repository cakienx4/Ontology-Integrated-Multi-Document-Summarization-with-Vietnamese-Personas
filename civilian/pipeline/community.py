import json
import os


def get_language(education_level: str, age: int) -> dict:
    edu_map = {
        "Không học vấn": 1,
        "Tiểu học": 1,
        "THCS": 2,
        "THPT": 2,
        "Trung cấp / Cao đẳng": 3,
        "Đại học": 3,
        "Sau đại học": 4,
    }
    level = edu_map.get(education_level, 2)

    # Bổ trợ: người trên 70 tuổi điều chỉnh xuống 1 bậc (CQ3)
    if age >= 70 and level > 1:
        level -= 1

    desc_map = {
        1: "Đơn giản — câu ngắn, từ ngữ đời thường, không dùng thuật ngữ chuyên môn",
        2: "Trung bình — câu rõ ràng, hạn chế thuật ngữ, ví dụ cụ thể",
        3: "Trung bình-cao — có thể dùng thuật ngữ phổ thông, lập luận 2 tầng",
        4: "Phức tạp — thuật ngữ chuyên môn, lập luận nhiều tầng, số liệu chi tiết",
    }
    return {"level": level, "description": desc_map[level]}


def get_topic(occupation: str, age: int, row: dict = None) -> dict:
    """
    {
      "hard": [...topics từ occupation, như cũ...],
      "soft": {
          "Du lịch":   {"subtopic": "Thiên nhiên / Sinh thái", "intensity": 0.9, "summary": "..."},
          "Nghệ thuật":{"subtopic": None, "intensity": 0.3, "summary": "..."},
          ...
      }
    }
    """
    occupation_map = {"...": "giữ nguyên như cũ"}
    hard_topics = occupation_map.get(occupation, ["Đời sống", "Thực tế"])
    if age >= 60 and "Sức khỏe" not in hard_topics:
        hard_topics = ["Sức khỏe"] + hard_topics

    soft = {}
    if row is not None:
        field_labels = {
            "sports_persona": "Thể thao", "arts_persona": "Nghệ thuật",
            "travel_persona": "Du lịch", "culinary_persona": "Ẩm thực",
            "hobbies_and_interests": "Sở thích khác",
        }
        for field, label in field_labels.items():
            text = str(row.get(field, "")).strip()
            if not text or text.lower() in ("nan", "none", "không có"):
                continue

            sentences = [s.strip() for s in text.split(".") if s.strip()]
            summary = ". ".join(sentences[:2])
            if summary and not summary.endswith("."):
                summary += "."

            subtopic = None
            if label in SOFT_TOPICS:
                sub_scores = _score_keyword_groups(text, SOFT_TOPICS[label])
                matched = {g for g, s in sub_scores.items() if s >= DOMAIN_SCORE_THRESHOLD}
                if matched:
                    subtopic = max(matched, key=lambda g: sub_scores[g])

            soft[label] = {
                "subtopic": subtopic,
                "intensity": _score_intensity(text),
                "summary": summary,
            }

    return {"hard": hard_topics, "soft": soft}


_DOMAIN_KEYWORDS_PATH = os.path.join(
    os.path.dirname(__file__), "../..", "data", "domain_keywords.json"
)

with open(_DOMAIN_KEYWORDS_PATH, encoding="utf-8") as f:
    _DOMAIN_DATA = json.load(f)

DOMAIN_KEYWORDS = _DOMAIN_DATA["domains"]
KEYWORD_RELATIONS = _DOMAIN_DATA.get("keyword_relations", [])
DOMAIN_PRIORITY = _DOMAIN_DATA.get("domain_priority", [])
SOFT_TOPICS = _DOMAIN_DATA.get("soft_topics", {})  # MỚI
INTENSITY_MARKERS = _DOMAIN_DATA.get("intensity_markers", {})  # MỚI

DOMAIN_SCORE_THRESHOLD = 0.6
PRIORITY_TIE_MARGIN = 0.15
INTENSITY_HIGH_THRESHOLD = 0.5


def _score_keyword_groups(text: str, keyword_groups: dict, relations: list = None) -> dict:
    """
    Tổng quát hóa của _compute_domain_scores cũ — không còn đọc thẳng
    DOMAIN_KEYWORDS/KEYWORD_RELATIONS ở module scope, mà nhận qua tham số,
    nên dùng được cho cả Domain (chuyên môn) lẫn soft_topics (Du lịch, Nghệ thuật...).
    """
    text = text.lower()
    scores = {group: 0.0 for group in keyword_groups}

    for group, kw_weights in keyword_groups.items():
        for kw, weight in kw_weights.items():
            if kw in text:
                scores[group] += weight

    if relations:
        for rel in relations:
            kw, target, weight = rel["from"], rel["to"], rel["weight"]
            if kw in text and target in scores:
                scores[target] += weight

    return scores


def _apply_priority_rules(selected: set, scores: dict, priority_rules: list, tie_margin: float) -> set:
    """Tổng quát hóa của _apply_domain_priority cũ — nhận priority_rules/tie_margin qua tham số."""
    result = set(selected)
    for rule in priority_rules:
        prefer, over = rule["prefer"], rule["over"]
        if prefer in result and over in result:
            if abs(scores.get(prefer, 0.0) - scores.get(over, 0.0)) <= tie_margin:
                result.discard(over)
    return result


def _score_intensity(text: str) -> float:
    """MỚI — dùng chung cho mọi field SOFT, đọc từ intensity_markers trong domain_keywords.json."""
    text = text.lower()
    score = 0.0
    for marker, weight in INTENSITY_MARKERS.items():
        if marker in text:
            score = max(score, weight)
    return score


def get_domain(skills_and_expertise: str, occupation: str) -> list:
    scores = _score_keyword_groups(skills_and_expertise, DOMAIN_KEYWORDS, KEYWORD_RELATIONS)
    domains = {d for d, s in scores.items() if s >= DOMAIN_SCORE_THRESHOLD}
    domains = _apply_priority_rules(domains, scores, DOMAIN_PRIORITY, PRIORITY_TIE_MARGIN)

    if not domains:
        occ_domain_map = {
            "Buôn bán / kinh doanh": ["Tài chính / Kế toán", "Quản lý / Tổ chức"],
            "Kỹ thuật viên / kỹ sư": ["Công nghệ / Kỹ thuật số"],
            "Y tế / dược": ["Y tế / Chăm sóc"],
            "Nghiên cứu / học thuật": ["Quản lý / Tổ chức", "Giao tiếp / Truyền thông"],
            "Freelancer / làm tự do": ["Sáng tạo / Nghệ thuật", "Công nghệ / Kỹ thuật số"],
            "Tài xế / giao hàng": ["Vận tải / Giao nhận"],
            "Nông nghiệp / ngư nghiệp": ["Nông nghiệp / Tự nhiên"],
        }
        domains = set(occ_domain_map.get(occupation, ["Đời sống thực tế"]))

    return sorted(domains)


def get_cultural(cultural_background: str, region: str, zone: str) -> dict:
    text = cultural_background.lower()

    traditional_signals = [
        "truyền thống", "phong tục", "tập quán", "bài chòi",
        "quan họ", "hát xẩm", "làng", "tổ tiên", "tín ngưỡng", "đình làng"
    ]  # đã bỏ "lễ hội" — quá chung chung, không phân biệt được truyền thống/hiện đại

    open_signals = [
        "quốc tế", "hiện đại", "đa văn hóa", "nước ngoài", "toàn cầu",
        "hội nhập", "công nghệ", "startup", "mạng xã hội",
        "chung cư", "căn hộ", "cao tầng", "đô thị"
    ]

    blend_signals = ["pha trộn", "kết hợp giữa", "vừa truyền thống vừa", "giao thoa"]

    trad_score = sum(1 for s in traditional_signals if s in text)
    open_score = sum(1 for s in open_signals if s in text)
    is_blend = any(s in text for s in blend_signals)

    if is_blend and abs(trad_score - open_score) <= 1:
        orientation = "Trung dung"
    elif trad_score > open_score:
        orientation = "Truyền thống"
    elif open_score > trad_score:
        orientation = "Cởi mở / Hội nhập"
    else:
        orientation = "Trung dung"

    if zone == "Nông Thôn" and orientation == "Trung dung":
        orientation = "Truyền thống"

    return {
        "orientation": orientation,
        "region": region,
        "zone": zone,
        "context": f"{orientation} — {zone} — {region}"
    }


def get_prototype(row: dict, language: dict, topic: list, cultural: dict) -> str:
    age = row["age"]
    sex = row["sex"]
    edu = row["education_level"]
    occ = row["occupation"]
    zone = row["zone"]

    if age < 30:
        life_stage = "người trẻ"
    elif age < 50:
        life_stage = "người trung niên"
    elif age < 65:
        life_stage = "người lớn tuổi"
    else:
        life_stage = "người cao tuổi"

    prototype = (
        f"{life_stage} {sex.lower()}, {occ.lower()}, trình độ {edu.lower()}, "
        f"sống tại {zone.lower()} {cultural['region']}. "
        f"Văn phong phù hợp: {language['description']}. "
        f"Chủ đề quan tâm chính: {', '.join(topic[:3])}. "
        f"Định hướng văn hóa: {cultural['orientation']}."
    )
    return prototype


# ── HÀM TỔNG HỢP ─────────────────────────────────────────────────────────────

def determine_community(row: dict) -> dict:
    language = get_language(row["education_level"], row["age"])
    topic = get_topic(row["occupation"], row["age"], row)
    domain = get_domain(row["skills_and_expertise"], row["occupation"])
    cultural = get_cultural(row["cultural_background"], row["region"], row["zone"])
    prototype = get_prototype(row, language, topic["hard"], cultural)

    return {
        "Language": language, "Topic": topic, "Domain": domain,
        "Cultural": cultural, "Prototype": prototype,
    }


if __name__ == "__main__":
    import pandas as pd
    import json

    df = pd.read_csv("../../data/sample50.csv")

    for i in [2, 5, 15]:  # bà Nga, người buôn bán, freelancer
        row = df.iloc[i].to_dict()
        community = determine_community(row)
        print(f"\n{'=' * 60}")
        print(f"Person {i}: {row['persona']}...")
        print(json.dumps(community, ensure_ascii=False, indent=2))
