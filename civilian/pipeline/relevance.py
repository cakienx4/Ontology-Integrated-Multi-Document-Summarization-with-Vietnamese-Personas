TOPIC_GENRE_ALIASES = {
    # Tài chính / Kế toán
    "Thị trường":        ["Tài chính / Kế toán"],
    "Giá cả":             ["Tài chính / Kế toán"],
    "Kinh doanh":         ["Tài chính / Kế toán"],
    "Kinh doanh cá nhân": ["Tài chính / Kế toán"],
    "Tài chính":          ["Tài chính / Kế toán"],
    "Tài chính cá nhân":  ["Tài chính / Kế toán"],
    "Thu nhập":           ["Tài chính / Kế toán"],

    # Công nghệ / Kỹ thuật số
    "Kỹ thuật":           ["Công nghệ / Kỹ thuật số"],
    "Công nghệ":          ["Công nghệ / Kỹ thuật số"],
    "Khoa học":           ["Công nghệ / Kỹ thuật số"],

    # Y tế / Chăm sóc
    "Sức khỏe":           ["Y tế / Chăm sóc"],
    "Y học":              ["Y tế / Chăm sóc"],
    "Dinh dưỡng":         ["Y tế / Chăm sóc", "Nấu ăn / Ẩm thực"],

    # Giáo dục
    "Tri thức":           ["Giáo dục"],
    "Giáo dục":           ["Giáo dục"],

    # Giải trí / Văn hóa
    "Sáng tạo":           ["Giải trí / Văn hóa"],
    "Truyền thông":       ["Giải trí / Văn hóa"],

    # Du lịch
    "Du lịch":            ["Du lịch"],

    # Môi trường
    "Môi trường":         ["Môi trường"],
    "Thời tiết":          ["Môi trường"],

    # Thời sự / Xã hội
    "Địa phương":         ["Thời sự / Xã hội"],
    "Cộng đồng":          ["Thời sự / Xã hội"],
}

ELDERLY_AGE_THRESHOLD = 60
HEALTH_GENRE = "Y tế / Chăm sóc"
ELDERLY_HEALTH_BONUS = 5.0


def score_text_relevance(row: dict, community: dict, content_meta: dict) -> float:
    domain_set = set(community["Domain"])
    topic_set  = set(community["Topic"])

    genre = content_meta.get("genre", "")
    text_type = content_meta.get("type", "")

    score = 0.0
    if genre in domain_set:
        score += 2.0

    aliased_topics = set()
    for t in topic_set:
        aliased_topics.update(TOPIC_GENRE_ALIASES.get(t, []))
    if genre in aliased_topics or text_type in topic_set:
        score += 1.0

    age = row.get("age", 0)
    if age >= ELDERLY_AGE_THRESHOLD and genre == HEALTH_GENRE:
        score += ELDERLY_HEALTH_BONUS

    return score