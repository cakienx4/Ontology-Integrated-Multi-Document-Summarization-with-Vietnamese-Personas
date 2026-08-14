from pathlib import Path
from rdflib import Graph, Namespace, Literal

BASE = Namespace("http://purl.obolibrary.org/obo/persona#")

MD_ROOT = Path(__file__).resolve().parents[2]
from pipeline.utils import load_graph
# ── BRANCH GỐC (khớp persona_states.ttl) ───────────────────────────────────
STATE_BRANCHES = ["nganh_cong_vu", "chu_de_chinh_sach"]

BRANCH_LABELS = {
    "nganh_cong_vu":     "Ngành công vụ",
    "chu_de_chinh_sach": "Chủ đề chính sách",
}

# ── QUAN HỆ (Object Properties, khớp persona_states.ttl) ───────────────────
REL_LABELS = {
    "lien_quan_mat_thiet": "liên quan mật thiết",
    "uu_tien_hon":         "ưu tiên hơn",
}

def _query_term_by_label(g: Graph, label: str):
    """Tìm URI của term có rdfs:label khớp đúng với label truyền vào."""
    q = """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?term WHERE {
        ?term rdfs:label ?label .
    }
    """
    for r in g.query(q, initBindings={"label": Literal(label)}):
        return r.term
    return None


def _query_term_relations(g: Graph, term_uri) -> list:
    """Lấy các quan hệ (object property) xuất phát từ 1 term cụ thể."""
    q = """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    SELECT ?rel_uri ?to_label WHERE {
        ?rel_uri a owl:ObjectProperty .
        ?term ?rel_uri ?to .
        ?to rdfs:label ?to_label .
    }
    """
    ket_qua = []
    for r in g.query(q, initBindings={"term": term_uri}):
        rel_id = str(r.rel_uri).split("#")[-1]
        rel_display = REL_LABELS.get(rel_id, rel_id)
        ket_qua.append((rel_display, str(r.to_label)))
    return ket_qua


def build_ontology_context_cho_nganh(g: Graph, nganh_to: str) -> str:
    """Lấy context ontology chỉ cho 1 ngành cụ thể của persona (khớp rdfs:label)."""
    if not nganh_to:
        return ""

    term_uri = _query_term_by_label(g, nganh_to)
    if term_uri is None:
        print(f"[CANH BAO] Khong tim thay term ontology khop voi nganh_to: '{nganh_to}'")
        return ""

    rels = _query_term_relations(g, term_uri)
    return _format_branch(nganh_to, {nganh_to: rels})

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


_ONTOLOGY_PATH = MD_ROOT / "persona_states.ttl"
_STATE_GRAPH = load_graph(str(_ONTOLOGY_PATH))


def lay_ontology_context_cho_nganh(nganh_to: str) -> str:
    return build_ontology_context_cho_nganh(_STATE_GRAPH, nganh_to)


# ── TEST ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    context = lay_ontology_context_cho_nganh("Y tế")
    print(context)
    print(f"\n--- Tổng độ dài context: {len(context)} ký tự ---")