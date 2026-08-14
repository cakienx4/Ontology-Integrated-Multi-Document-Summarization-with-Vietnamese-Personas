from rdflib import Graph, Namespace
from pathlib import Path
BASE = Namespace("http://purl.obolibrary.org/obo/persona#")

HARD_BRANCHES = ["professional_persona", "skills_and_expertise"]

SOFT_BRANCHES = [
    "sports_persona",
    "arts_persona",
    "travel_persona",
    "culinary_persona",
    "hobbies_and_interests",
]

GENERAL_BRANCHES = ["persona", "cultural_background", "career_goals_and_ambitions"]

ALL_BRANCHES = HARD_BRANCHES + SOFT_BRANCHES + GENERAL_BRANCHES

BRANCH_LABELS = {
    "professional_persona":       "Hồ sơ nghề nghiệp",
    "skills_and_expertise":       "Kỹ năng và chuyên môn",
    "sports_persona":             "Thể thao",
    "arts_persona":               "Nghệ thuật",
    "travel_persona":             "Du lịch",
    "culinary_persona":           "Ẩm thực",
    "hobbies_and_interests":      "Sở thích và mối quan tâm",
    "persona":                    "Bản sắc cá nhân",
    "cultural_background":        "Nền tảng văn hóa",
    "career_goals_and_ambitions": "Mục tiêu và tham vọng",
}

REL_LABELS = {
    "dinh_hinh":   "định hình",
    "tac_dong":    "tác động đến",
    "cung_co":     "củng cố",
    "thuc_day":    "thúc đẩy",
    "tuong_quan":  "tương quan với",
    "uu_tien_hon": "ưu tiên hơn",
}


def load_graph(ttl_path: str) -> Graph:
    g = Graph()
    ttl_path = Path(ttl_path).resolve().as_uri()
    g.parse(ttl_path, format='turtle')
    return g


def _query_branch(g: Graph, branch: str) -> dict:
    """
    Lấy toàn bộ term thuộc branch (L1-L3, transitive closure qua rdfs:subClassOf*),
    kèm theo các quan hệ ngữ nghĩa (object property) xuất phát từ mỗi term.
    """
    q_terms = f"""
    PREFIX persona: <http://purl.obolibrary.org/obo/persona#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>

    SELECT ?term ?label WHERE {{
        ?term a owl:Class ;
              rdfs:label ?label ;
              rdfs:subClassOf* persona:{branch} .
        FILTER(?term != persona:{branch})
    }}
    """
    terms = {str(r.term): str(r.label) for r in g.query(q_terms)}

    q_rels = f"""
    PREFIX persona: <http://purl.obolibrary.org/obo/persona#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>

    SELECT ?from_uri ?from_label ?rel_uri ?to_label WHERE {{
        ?from_uri rdfs:subClassOf* persona:{branch} ;
                  rdfs:label ?from_label .
        FILTER(?from_uri != persona:{branch})
        ?rel_uri a owl:ObjectProperty .
        ?from_uri ?rel_uri ?to .
        ?to rdfs:label ?to_label .
    }}
    """
    result = {}
    for r in g.query(q_rels):
        from_label = str(r.from_label)
        rel_id     = str(r.rel_uri).split("#")[-1]
        to_label   = str(r.to_label)
        rel_display = REL_LABELS.get(rel_id, rel_id)

        result.setdefault(from_label, []).append((rel_display, to_label))

    # Thêm các term không có quan hệ nào (để không bị bỏ sót trong context)
    for label in terms.values():
        result.setdefault(label, [])

    return result


def _format_branch(branch_name: str, branch_data: dict) -> str:
    display_name = BRANCH_LABELS.get(branch_name, branch_name)
    lines = [f"[{display_name}]"]

    for term_label, rels in branch_data.items():
        if rels:
            rel_strs = "; ".join(f"{rel} '{target}'" for rel, target in rels)
            lines.append(f"  * {term_label}: {rel_strs}")
        else:
            lines.append(f"  * {term_label}")

    return "\n".join(lines)


def build_ontology_context(g: Graph, branches: list = None) -> str:
    """
    Sinh ontology_context dạng text từ graph.
    Mặc định duyệt cả 10 branches (HARD + SOFT + GENERAL).
    Có thể truyền `branches` để giới hạn (ví dụ chỉ HARD_BRANCHES cho confirmation world).
    """
    if branches is None:
        branches = ALL_BRANCHES

    sections = []
    for branch in branches:
        branch_data = _query_branch(g, branch)
        if branch_data:
            sections.append(_format_branch(branch, branch_data))

    context = "\n\n".join(sections)
    return context


# ── TEST ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    g = load_graph("../../ontology/persona_analysis_3.ttl")
    context = build_ontology_context(g)
    print(context)
    print(f"\n--- Tổng độ dài context: {len(context)} ký tự ---")
