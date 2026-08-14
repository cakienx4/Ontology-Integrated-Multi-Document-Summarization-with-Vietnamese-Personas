"""
pipeline/content_classifier.py

Phân loại văn bản đầu vào theo:
- type  (kiểu bài: hình thức trình bày)
- genre (loại bài: lĩnh vực nội dung)

Dùng cùng cơ chế weighted-keyword + threshold + priority tie-break như
get_domain() trong community.py, để đồng bộ cách tiếp cận rule-based
trong toàn project.
"""

import json
import os

_TYPES_PATH  = os.path.join(os.path.dirname(__file__), "../..", "config", "article_types.json")
_GENRES_PATH = os.path.join(os.path.dirname(__file__), "../..", "config", "article_genres.json")

with open(_TYPES_PATH, encoding="utf-8") as f:
    _TYPE_DATA = json.load(f)

with open(_GENRES_PATH, encoding="utf-8") as f:
    _GENRE_DATA = json.load(f)

TYPE_KEYWORDS   = _TYPE_DATA["types"]
TYPE_PRIORITY   = _TYPE_DATA.get("type_priority", [])
DEFAULT_TYPE    = _TYPE_DATA.get("default_type", "Tin tức")

GENRE_KEYWORDS  = _GENRE_DATA["genres"]
GENRE_PRIORITY  = _GENRE_DATA.get("genre_priority", [])
DEFAULT_GENRE   = _GENRE_DATA.get("default_genre", "Thời sự / Xã hội")

SCORE_THRESHOLD    = 0.6
PRIORITY_TIE_MARGIN = 0.15


def _compute_scores(text: str, keyword_map: dict) -> dict:
    text_lower = text.lower()
    scores = {label: 0.0 for label in keyword_map}
    for label, keyword_weights in keyword_map.items():
        for kw, weight in keyword_weights.items():
            if kw in text_lower:
                scores[label] += weight
    return scores


def _apply_priority(best_candidates: set, scores: dict, priority_rules: list) -> set:
    result = set(best_candidates)
    for rule in priority_rules:
        prefer, over = rule["prefer"], rule["over"]
        if prefer in result and over in result:
            diff = abs(scores.get(prefer, 0.0) - scores.get(over, 0.0))
            if diff <= PRIORITY_TIE_MARGIN:
                result.discard(over)
    return result


def classify_type(text: str) -> str:
    scores = _compute_scores(text, TYPE_KEYWORDS)
    candidates = {label for label, s in scores.items() if s >= SCORE_THRESHOLD}
    candidates = _apply_priority(candidates, scores, TYPE_PRIORITY)

    if not candidates:
        return DEFAULT_TYPE
    # nếu còn nhiều candidate sau tie-break, chọn điểm cao nhất
    return max(candidates, key=lambda label: scores[label])


def classify_genre(text: str) -> str:
    scores = _compute_scores(text, GENRE_KEYWORDS)
    candidates = {label for label, s in scores.items() if s >= SCORE_THRESHOLD}
    candidates = _apply_priority(candidates, scores, GENRE_PRIORITY)

    if not candidates:
        return DEFAULT_GENRE
    return max(candidates, key=lambda label: scores[label])


def classify_content(text: str) -> dict:
    return {
        "type":  classify_type(text),
        "genre": classify_genre(text),
    }


if __name__ == "__main__":
    sample_text = """
    Chất lượng sản phẩm tuyệt vời, giá cả hợp lý. Đã giới thiệu cho bạn bè. Sản phẩm dễ sử dụng, có ghi chú hướng dẫn rõ ràng. Tôi vô cùng hài lòng với lần mua sắm này.
"""
    print(classify_content(sample_text))