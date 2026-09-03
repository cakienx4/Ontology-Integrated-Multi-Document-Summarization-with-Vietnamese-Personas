""" Cách chạy:
python3 -m pipeline.baochi.rss_personalize --variant nt_nn_tc_kn_cd_ch
"""

import re
import json
import hashlib
import asyncio
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]

MD_ROOT = ROOT_DIR / "multi_document_variants"
SHARED_ROOT = ROOT_DIR / "shared"

DATA_DIR = MD_ROOT / "data" / "bao_chi"
OUTPUT_DIR = MD_ROOT / "output" / "bao_chi" / "rss_summary"

from pipeline.utils import (
    retry_generate_async, OSS_MODEL_NAME, load_graph,
    tao_oss_client_async, lay_chu_de_hieu_luc, OSS_MAX_CONCURRENCY,
    OSS_MAX_CONCURRENCY_SUMMARY,
)
from pipeline.profiles.ontology_context_state import lay_ontology_context_cho_nganh
from pipeline.baochi.rss_tom_tat_bai import tom_tat_nhieu_bai

_ONTOLOGY_PATH = MD_ROOT / "persona_states.ttl"
_STATE_GRAPH = load_graph(str(_ONTOLOGY_PATH))

_GENRES_PATH = SHARED_ROOT / "config" / "article_genres.json"
with open(_GENRES_PATH, encoding="utf-8") as f:
    _GENRE_DATA = json.load(f)

GENRE_KEYWORDS = _GENRE_DATA["genres"]
GENRE_PRIORITY = _GENRE_DATA.get("genre_priority", [])
DEFAULT_GENRE = _GENRE_DATA.get("default_genre", "Thời sự / Xã hội")

_OVERLAP_PATH = SHARED_ROOT / "config" / "genre_overlap.json"
with open(_OVERLAP_PATH, encoding="utf-8") as f:
    _OVERLAP_DATA = json.load(f)

CACHE_BAI_LIEN_QUAN_PATH = (
    OUTPUT_DIR / "lien_quan" / "rss_filter" / "bai_lien_quan_theo_nganh_to.json"
)

FILTER_DIR = MD_ROOT / "output" / "bao_chi" / "rss_filter"

GENRE_OVERLAP = _OVERLAP_DATA.get("overlap", {})
NGUONG_LIEN_QUAN_GIAN_TIEP = _OVERLAP_DATA.get("nguong_lien_quan_gian_tiep", 0.3)

RSS_SCORE_THRESHOLD = 0.6
RSS_PRIORITY_TIE_MARGIN = 0.15

CHU_DE_WEIGHTS = [1.0, 0.6, 0.4]
CHU_DE_WEIGHT_FALLBACK = 0.3

DUONG_DAN_LOAI_BAI = ["goc-nhin", "tam-diem"]
MAX_BAI_LIEN_QUAN_MOI_PERSONA = 2
SO_TIN_TOI_DA_FALLBACK_MOI_NHOM = 10

FILTER_MAX_TOKENS = 4096

SO_TIN_MOI_BATCH = 8
BATCH_MAX_TOKENS = 3072
BATCH_MAX_TOKENS_MO_RONG = 6144

MO_KET_MAX_TOKENS = 768
MO_KET_MAX_TOKENS_MO_RONG = 1536

LIEN_QUAN_MAX_TOKENS = 1024
LIEN_QUAN_MAX_TOKENS_MO_RONG = 2048

TI_LE_BAO_PHU_TOI_THIEU = 0.85


def xac_dinh_loai_bai(article: dict) -> str:
    slug = (article.get("category_slug") or "").strip().lower()
    if slug in DUONG_DAN_LOAI_BAI:
        return "bài"
    return "tin"


def nhom_tin_theo_chu_de(persona: dict, ranked_articles: list) -> list:
    chu_de_list = lay_chu_de_hieu_luc(persona)
    nhom = []
    for i, cd in enumerate(chu_de_list):
        bai = [a for a in ranked_articles if a.get("genre") == cd]
        if bai:
            nhom.append({"chu_de": cd, "trong_so": _weight_of_chu_de(i), "bai": bai})
    return nhom


def tim_tin_lien_quan_gian_tiep(persona: dict, articles: list, da_chon: list) -> list:
    chu_de_list = lay_chu_de_hieu_luc(persona)
    if not chu_de_list:
        return []

    da_chon_id = {id(a) for a in da_chon}
    ung_vien = []
    for a in articles:
        if id(a) in da_chon_id:
            continue
        if a.get("loai_bai") == "bài":
            continue
        genre = a.get("genre")
        if genre in chu_de_list:
            continue
        diem_overlap = 0.0
        for cd in chu_de_list:
            diem_overlap = max(diem_overlap, GENRE_OVERLAP.get(cd, {}).get(genre, 0.0))
        if diem_overlap >= NGUONG_LIEN_QUAN_GIAN_TIEP:
            ung_vien.append((diem_overlap, a))

    ung_vien.sort(
        key=lambda x: (x[0], x[1].get("genre_score", 0.0)),
        reverse=True
    )

    max_tin_gian_tiep = min(
        10,
        max(3, len(da_chon) // 3)
    )

    return [a for _, a in ung_vien[:max_tin_gian_tiep]]


CHUC_VU_LANH_DAO_KEYWORDS = [
    "giám đốc", "trưởng phòng", "trưởng nhóm", "cục trưởng",
    "vụ trưởng", "chủ tịch", "phó chủ tịch", "bí thư", "trưởng", "lãnh đạo",
]

GENRE_LUON_DAY_DU = {"Chính trị / Pháp luật", "Quốc phòng / An ninh"}
SO_CHU_DE_UU_TIEN_TOI_DA_CHO_DAY_DU = 2

OPENING_STYLES_MO_BAI = [
    "Mở bằng một câu nêu bao quát các nhóm vấn đề/xu hướng nổi bật sẽ xuất hiện trong bài, KHÔNG nêu tên sự kiện cụ thể, KHÔNG nêu số liệu, KHÔNG nhắc đến bất kỳ tin riêng lẻ nào.",
    "Mở bằng cách nêu mối liên hệ giữa các nhóm chủ đề sắp trình bày với định hướng công việc trước mắt của người đọc, giữ ở mức khái quát, KHÔNG đi vào nội dung của tin cụ thể nào.",
    "Mở bằng một nhận định ngắn gọn về bối cảnh chung bao trùm các nhóm tin sắp tóm tắt, KHÔNG nêu tên bất kỳ sự kiện hay tin cụ thể nào.",
    "Mở bằng cách nêu khái quát (không liệt kê tên tin) các mảng nội dung chính sẽ được đề cập, theo đúng thứ tự ưu tiên nhóm chủ đề, KHÔNG đi vào chi tiết của tin nào.",
]
OPENING_STYLES = [
    "Mở thẳng bằng số liệu hoặc sự kiện cụ thể nhất trong tin xếp hạng cao nhất, không dẫn dắt, không nêu bối cảnh chung.",
    "Mở bằng cách liên hệ trực tiếp tới mối quan tâm trước mắt hoặc nhiệm vụ hiện tại của người đọc, rồi mới dẫn vào tin liên quan.",
    "Mở bằng một nhận định hoặc câu hỏi ngắn liên quan trực tiếp đến công việc của người đọc, sau đó lập tức nối vào tin số 1.",
    "Mở bằng cách tóm tắt nhanh diễn biến chính của tin số 1 dưới dạng một câu khẳng định, không dùng từ 'bối cảnh' hay 'trong bối cảnh'.",
]
CLOSING_STYLES = [
    "Kết bằng một câu chốt nêu điểm cần lưu ý gần nhất, đặt NGAY SAU phần tóm tắt các ý chính, không dùng cụm 'nhìn chung' hay 'kết lại'.",
    "Kết bằng cách quay lại liên hệ với tin đầu tiên sau khi đã tóm tắt các ý chính, không liệt kê lại nguyên văn các ý đã nêu.",
    "Kết bằng cách nêu điểm cần theo dõi tiếp theo, đặt NGAY SAU phần tóm tắt các ý chính — câu này KHÔNG được thay thế phần tóm tắt.",
    "Kết bằng một câu nhấn mạnh mức độ ưu tiên của ý quan trọng nhất vừa tóm tắt, không lặp nguyên văn câu đã viết ở thân bài.",
]

BANNED_PHRASES = [
    "Trong bối cảnh", "Nhìn chung", "Kết lại", "Có thể thấy rằng",
    "Đáng chú ý là", "Trong khi đó", "Bên cạnh đó", "Đối với",
]


def _chon_style(persona_id: str, styles: list) -> str:
    h = int(hashlib.md5(persona_id.encode()).hexdigest(), 16)
    return styles[h % len(styles)]


def _compute_scores(text: str, keyword_map: dict) -> dict:
    text_lower = text.lower()
    scores = {label: 0.0 for label in keyword_map}
    for label, kw_weights in keyword_map.items():
        for kw, w in kw_weights.items():
            if kw in text_lower:
                scores[label] += w
    return scores


def _apply_priority(candidates: set, scores: dict, rules: list) -> set:
    result = set(candidates)
    for rule in rules:
        prefer, over = rule["prefer"], rule["over"]
        if prefer in result and over in result:
            if abs(scores.get(prefer, 0.0) - scores.get(over, 0.0)) <= RSS_PRIORITY_TIE_MARGIN:
                result.discard(over)
    return result


def classify_genre_rss(text: str) -> tuple:
    scores = _compute_scores(text, GENRE_KEYWORDS)
    candidates = {label for label, s in scores.items() if s >= RSS_SCORE_THRESHOLD}
    candidates = _apply_priority(candidates, scores, GENRE_PRIORITY)

    if not candidates:
        return DEFAULT_GENRE, 0.0

    best = max(candidates, key=lambda label: scores[label])
    return best, scores[best]


def gan_genre_cho_bai(articles: list) -> list:
    for a in articles:
        text = f"{a.get('title', '')} {a.get('summary', '')}"
        genre, score = classify_genre_rss(text)
        a["genre"] = genre
        a["genre_score"] = score
        a["loai_bai"] = xac_dinh_loai_bai(a)
    return articles


def _weight_of_chu_de(index: int) -> float:
    if index < len(CHU_DE_WEIGHTS):
        return CHU_DE_WEIGHTS[index]
    return CHU_DE_WEIGHT_FALLBACK


def xep_hang_bai_cho_persona(persona: dict, articles: list) -> list:
    chu_de_list = lay_chu_de_hieu_luc(persona)
    if not chu_de_list:
        return []

    theo_chu_de = {cd: [] for cd in chu_de_list}
    for a in articles:
        if a.get("loai_bai") == "bài":
            continue
        if a.get("genre") in theo_chu_de and a.get("genre_score", 0.0) > 0.0:
            theo_chu_de[a["genre"]].append(a)
    for cd in theo_chu_de:
        theo_chu_de[cd].sort(key=lambda a: a.get("genre_score", 0.0), reverse=True)

    da_chon = []
    for cd in chu_de_list:
        da_chon.extend(theo_chu_de[cd])

    return da_chon


def lay_chuc_vu(kinh_nghiem_text: str) -> str:
    match = re.search(r"đảm nhiệm vị trí (.+?)\.", kinh_nghiem_text or "")
    return match.group(1).strip() if match else ""


DO_TUOI_NGUONG_TRANG_TRONG = 55


def can_van_phong_day_du(persona: dict, ranked_articles: list) -> bool:
    chuc_vu = lay_chuc_vu(persona.get("kinh_nghiem", "")).lower()
    if any(kw in chuc_vu for kw in CHUC_VU_LANH_DAO_KEYWORDS):
        return True
    if persona.get("do_tuoi", 0) >= DO_TUOI_NGUONG_TRANG_TRONG:
        return True

    chu_de_uu_tien_cao = set(lay_chu_de_hieu_luc(persona)[:SO_CHU_DE_UU_TIEN_TOI_DA_CHO_DAY_DU])
    co_tin_nhay_cam_dung_chuyen_mon_chinh = any(
        a.get("genre") in GENRE_LUON_DAY_DU and a.get("genre") in chu_de_uu_tien_cao
        for a in ranked_articles
    )
    if co_tin_nhay_cam_dung_chuyen_mon_chinh:
        return True

    return False

CHU_THICH_THUA_TU_KHOA = [
    "(ghi chú", "(đã bỏ qua", "(lược bỏ", "(gộp vì", "được gộp vì",
    "(tin này đã", "(lưu ý:",
]


def co_chu_thich_thua(text: str) -> bool:
    text_lower = text.lower()
    return any(tu_khoa in text_lower for tu_khoa in CHU_THICH_THUA_TU_KHOA)

def _dinh_dang_danh_sach_tin(articles: list, dung_full_content: bool = True) -> str:
    ds = ""
    for i, a in enumerate(articles, 1):
        noi_dung = (a.get("content") or a.get("summary", "")) if dung_full_content else a.get("summary", "")
        ds += (
            f"\n{i}. [{a.get('genre')}] {a.get('title')}\n"
            f"   Nội dung: {noi_dung}\n"
        )
    return ds


MUC_DO_CHI_TIET = [
    "Mỗi tin trong nhóm này viết thành MỘT ĐOẠN VĂN RIÊNG (không gộp 2 tin trở lên vào cùng 1 "
    "đoạn). ĐỘ DÀI đoạn văn KHÔNG cố định — phụ thuộc vào lượng thông tin thực sự có trong "
    "phần 'Nội dung' của tin: tin có nhiều số liệu, diễn biến, phát biểu, bối cảnh thì viết dài "
    "và đầy đủ tương ứng; tin ít nội dung thì viết ngắn, KHÔNG kéo dài giả tạo. Tóm tắt trọn vẹn "
    "TẤT CẢ ý chính và ý phụ quan trọng, có phân tích sâu, dùng thuật ngữ chuyên ngành phù hợp "
    "(tham khảo Ontology Context nếu có) — đây là phần TRỌNG TÂM của bài, mức độ chuyên sâu cao nhất.",
    "Mỗi tin trong nhóm này viết thành MỘT ĐOẠN VĂN RIÊNG (không gộp 2 tin trở lên vào cùng 1 "
    "đoạn). ĐỘ DÀI đoạn văn co giãn theo lượng nội dung thật có trong tin, không ép về một số "
    "câu cố định. Tóm tắt trọn vẹn ý chính của tin (không bỏ sót ý quan trọng), có thể dùng "
    "thuật ngữ ngành nhưng không cần phân tích sâu như nhóm trọng tâm.",
    "Mỗi tin trong nhóm này viết thành MỘT ĐOẠN VĂN RIÊNG (không gộp 2 tin trở lên vào cùng 1 "
    "đoạn). ĐỘ DÀI đoạn văn co giãn theo lượng nội dung thật có trong tin, không ép về một số "
    "câu cố định. Tóm tắt trọn vẹn ý chính, ngôn ngữ phổ thông, không cần thuật ngữ chuyên "
    "ngành, nhưng vẫn phải nêu đủ nội dung cốt lõi (không chỉ nêu tên tin).",
]


def _muc_do_cho_tang(idx: int) -> str:
    return MUC_DO_CHI_TIET[min(idx, len(MUC_DO_CHI_TIET) - 1)]


def build_filter_prompt(persona: dict, articles: list) -> str:
    ds = ""
    for i, a in enumerate(articles, 1):
        ds += f"\n{i}. {a.get('title')}\n   Tóm tắt gốc: {a.get('summary')}\n"

    câu_hỏi_kiểm_tra = (
        f"Tin này có phục vụ trực tiếp cho công việc, chuyên môn hoặc nhiệm vụ thực tế của "
        f"một người làm trong ngành \"{persona.get('nganh_to')} - {persona.get('nganh_nho')}\" "
        f"hay không? (dựa vào mô tả chung và định hướng công việc trước mắt của người này ở trên)"
    )

    prompt = f"""Bạn đang lọc tin RSS cho một cán bộ có hồ sơ công vụ sau:

        - Ngành/lĩnh vực: {persona.get('nganh_to')} - {persona.get('nganh_nho')}
        - Đơn vị công tác: {persona.get('to_chuc')}
        - Mô tả chung: {persona.get('mo_ta_chung')}
        - Định hướng công việc trước mắt: {persona.get('cau_hoi_truoc_mat')}

        Câu hỏi kiểm tra cho MỖI tin: "{câu_hỏi_kiểm_tra}"

        - "giu": CHỈ khi tin có ý nghĩa trực tiếp với công việc/chuyên môn của người này — ví dụ
          chính sách, quy định, số liệu, sự kiện, xu hướng thuộc đúng ngành họ đang làm, mà họ cần
          biết để phục vụ công việc.
        - "ha": tin có nhắc đến từ khóa liên quan đến ngành của họ, nhưng chỉ mang tính CHUYỆN CỦA
          MỘT DOANH NGHIỆP, TỔ CHỨC HOẶC CÁ NHÂN CỤ THỂ, không có ý nghĩa chung với công việc của
          người này. Ví dụ: một công ty tư nhân báo lãi/lỗ, cổ phiếu một doanh nghiệp tăng/giảm,
          một câu lạc bộ thể thao gặp khủng hoảng tài chính, tài sản cá nhân của người nổi tiếng
          thay đổi, một dự án cụ thể của một chủ đầu tư mở bán — dù có nhắc từ khóa cùng ngành,
          những tin này không phục vụ công việc chung của người này.
        - "loai": hoàn toàn không liên quan đến lĩnh vực của người này.

        QUY TẮC MẶC ĐỊNH: nếu phân vân giữa "giu" và "ha", LUÔN chọn "ha". "giu" phải là lựa chọn
        có chủ đích, không phải lựa chọn an toàn.

        Danh sách tin:
        {ds}

        Chỉ trả về DUY NHẤT một mảng JSON, không thêm chữ nào khác, không dùng dấu ```. Mỗi phần
        tử có đúng 2 trường:
        [
          {{"stt": 1, "hanh_dong": "giu"}},
          {{"stt": 2, "hanh_dong": "ha"}}
        ]

        Phải trả đủ {len(articles)} phần tử, đúng theo số thứ tự đã đánh ở trên, không được bỏ sót.
        """.strip()

    return prompt


async def loc_bai_lien_quan_persona(persona: dict, ranked_articles: list, client, semaphore,
                                    model_name: str = OSS_MODEL_NAME) -> tuple:
    if not ranked_articles:
        return [], []

    prompt = build_filter_prompt(persona, ranked_articles)

    async def _call():
        return await client.models.generate_content(
            model=model_name,
            contents=prompt,
            config={
                "temperature": 0.0,
                "max_output_tokens": FILTER_MAX_TOKENS,
            },
        )

    async with semaphore:
        response = await retry_generate_async(_call)
    text = response.text.strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    matches = re.findall(
        r'\{\s*"stt"\s*:\s*(\d+)\s*,\s*"hanh_dong"\s*:\s*"(\w+)"\s*\}',
        text,
    )
    hanh_dong_theo_stt = {int(stt): hanh_dong for stt, hanh_dong in matches}

    if not hanh_dong_theo_stt:
        print(f"[loc_bai_lien_quan_persona] KHÔNG LẤY ĐƯỢC OBJECT NÀO TỪ RESPONSE, giữ nguyên tất cả.")
        print(f"[loc_bai_lien_quan_persona] RAW RESPONSE (500 ký tự đầu):\n{text[:500]}")
        return ranked_articles, []

    if len(hanh_dong_theo_stt) < len(ranked_articles):
        print(
            f"[loc_bai_lien_quan_persona] CẢNH BÁO: chỉ lấy được "
            f"{len(hanh_dong_theo_stt)}/{len(ranked_articles)} tin (có thể do bị cắt cụt), "
            f"các tin còn lại mặc định giữ."
        )

    bai_giu = []
    bai_ha = []
    for i, a in enumerate(ranked_articles, 1):
        hanh_dong = hanh_dong_theo_stt.get(i, "giu")
        if hanh_dong == "giu":
            bai_giu.append(a)
        elif hanh_dong == "ha":
            bai_ha.append(a)

    return bai_giu, bai_ha

def _snapshot_key(bai_candidates: list) -> str:
    links = sorted(a.get("link", "") for a in bai_candidates)
    return hashlib.md5("|".join(links).encode("utf-8")).hexdigest()[:12]


def _doc_cache_bai_lien_quan() -> dict:
    if not CACHE_BAI_LIEN_QUAN_PATH.exists():
        return {}
    with open(CACHE_BAI_LIEN_QUAN_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _ghi_cache_bai_lien_quan(cache: dict) -> None:
    CACHE_BAI_LIEN_QUAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_BAI_LIEN_QUAN_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def build_filter_prompt_bai(persona: dict, bai_list: list) -> str:
    ds = ""
    for i, a in enumerate(bai_list, 1):
        noi_dung = a.get("content") or a.get("summary", "")
        ds += f"\n{i}. {a.get('title')}\n   Nội dung: {noi_dung}\n"

    nganh_to = persona.get("nganh_to", "")
    câu_hỏi_kiểm_tra = (
        f"Bài viết (dạng phân tích/góc nhìn, không phải tin thời sự thuần túy) này có bàn về "
        f"chủ đề đủ gần với lĩnh vực rộng \"{nganh_to}\" để một cán bộ công tác trong lĩnh vực "
        f"này thấy đáng đọc tham khảo, mở rộng nhận thức, hay không?"
    )

    prompt = f"""Bạn đang lọc các bài phân tích/góc nhìn (KHÔNG phải tin thời sự) cho một cán bộ
        công tác trong lĩnh vực rộng: {nganh_to}

        Câu hỏi kiểm tra cho MỖI bài: "{câu_hỏi_kiểm_tra}"

        - "giu": bài đủ liên quan ở mức lĩnh vực lớn, đáng đưa vào bản tóm tắt.
        - "loai": bài không liên quan gì đến lĩnh vực này.

        Danh sách bài:
        {ds}

        Chỉ trả về DUY NHẤT một mảng JSON, không thêm chữ nào khác, không dùng dấu ```. Mỗi phần
        tử có đúng 2 trường:
        [
          {{"stt": 1, "hanh_dong": "giu"}},
          {{"stt": 2, "hanh_dong": "loai"}}
        ]

        Phải trả đủ {len(bai_list)} phần tử, đúng theo số thứ tự đã đánh ở trên, không được bỏ sót.
        """.strip()

    return prompt


async def loc_bai_loai_bai_cho_persona(persona: dict, bai_candidates: list, client, semaphore,
                                       model_name: str = OSS_MODEL_NAME) -> list:
    if not bai_candidates:
        return []

    nganh_to = persona.get("nganh_to", "")
    snap_key = _snapshot_key(bai_candidates)
    cache_key = f"{snap_key}::{nganh_to}"

    cache = _doc_cache_bai_lien_quan()
    if cache_key in cache:
        links_giu = set(cache[cache_key])
        bai_giu_cache = [a for a in bai_candidates if a.get("link") in links_giu]
        return bai_giu_cache[:MAX_BAI_LIEN_QUAN_MOI_PERSONA]

    prompt = build_filter_prompt_bai(persona, bai_candidates)

    async def _call():
        return await client.models.generate_content(
            model=model_name,
            contents=prompt,
            config={
                "temperature": 0.0,
                "max_output_tokens": FILTER_MAX_TOKENS,
            },
        )

    async with semaphore:
        response = await retry_generate_async(_call)
    text = response.text.strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    matches = re.findall(
        r'\{\s*"stt"\s*:\s*(\d+)\s*,\s*"hanh_dong"\s*:\s*"(\w+)"\s*\}',
        text,
    )
    hanh_dong_theo_stt = {int(stt): hanh_dong for stt, hanh_dong in matches}

    bai_giu = [
        a for i, a in enumerate(bai_candidates, 1)
        if hanh_dong_theo_stt.get(i, "loai") == "giu"
    ]

    cache[cache_key] = [a.get("link") for a in bai_giu]
    _ghi_cache_bai_lien_quan(cache)

    return bai_giu[:MAX_BAI_LIEN_QUAN_MOI_PERSONA]


async def loc_bai_lien_quan_persona_co_cache(persona: dict, ranked_articles: list, client, semaphore,
                                             model_name: str = OSS_MODEL_NAME, variant: str = None) -> tuple:
    thu_muc_cache = FILTER_DIR / variant if variant else FILTER_DIR
    thu_muc_cache.mkdir(parents=True, exist_ok=True)
    cache_path = thu_muc_cache / f"{persona.get('id')}.json"

    if cache_path.exists():
        with open(cache_path, encoding="utf-8") as f:
            cache = json.load(f)
        bai_theo_link = {a.get("link"): a for a in ranked_articles}
        bai_giu = [bai_theo_link[link] for link in cache["giu"] if link in bai_theo_link]
        bai_ha = [bai_theo_link[link] for link in cache["ha"] if link in bai_theo_link]
        return bai_giu, bai_ha

    bai_giu, bai_ha = await loc_bai_lien_quan_persona(persona, ranked_articles, client, semaphore, model_name)

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "giu": [a.get("link") for a in bai_giu],
                "ha": [a.get("link") for a in bai_ha],
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    return bai_giu, bai_ha

def _khoi_phuc_tin_cho_nhom_bi_ha_het(chu_de_list: list, ranked_truoc_loc: list, ranked_sau_loc: list) -> tuple:
    link_da_giu = {a.get("link") for a in ranked_sau_loc}
    ranked = list(ranked_sau_loc)
    ten_cac_nhom_bi_khoi_phuc = []

    for cd in chu_de_list:
        nhom_truoc = [a for a in ranked_truoc_loc if a.get("genre") == cd]
        if not nhom_truoc:
            continue
        nhom_sau = [a for a in nhom_truoc if a.get("link") in link_da_giu]
        if nhom_sau:
            continue

        nhom_truoc_sap_xep = sorted(nhom_truoc, key=lambda a: a.get("genre_score", 0.0), reverse=True)
        bo_sung = nhom_truoc_sap_xep[:SO_TIN_TOI_DA_FALLBACK_MOI_NHOM]
        ranked.extend(bo_sung)
        link_da_giu.update(a.get("link") for a in bo_sung)
        ten_cac_nhom_bi_khoi_phuc.append(cd)

    return ranked, ten_cac_nhom_bi_khoi_phuc

def build_batch_prompt(persona: dict, nhom_ten: str, idx_nhom: int, tong_so_nhom: int,
                       batch_tin: list, la_batch_dau_nhom: bool, ontology_ctx: str,
                       day_du: bool, opening_style: str = None) -> str:

    so_tin = len(batch_tin)
    cam_cum_tu = ", ".join(f"'{p}'" for p in BANNED_PHRASES)

    ontology_section = ""
    if ontology_ctx:
        ontology_section = f"""KHUNG PHÂN TÍCH NGÀNH CÔNG VỤ (Ontology Context):
{ontology_ctx}

"""

    khuynh_huong = ""
    if idx_nhom == 0:
        khuynh_huong = (
            f"\n- KHUYNH HƯỚNG PHÂN TÍCH BẮT BUỘC cho nhóm này: chủ động chọn góc nhìn, số "
            f"liệu, hệ quả liên quan TRỰC TIẾP tới định hướng công việc sau đây, để nó DẪN "
            f"DẮT cách bạn diễn giải các tin: \"{persona.get('cau_hoi_truoc_mat', '')}\""
        )

    cau_dan_yeu_cau = ""
    if la_batch_dau_nhom and idx_nhom > 0:
        if day_du:
            cau_dan_yeu_cau = (
                f"\n- Đoạn tin ĐẦU TIÊN trong batch này PHẢI mở đầu bằng một câu dẫn ngắn "
                f"(không quá 1 câu) báo hiệu đang chuyển sang chủ đề mới \"{nhom_ten}\", nêu "
                f"tên nhóm một cách tự nhiên trong câu văn — câu dẫn nằm CHUNG trong đoạn tóm "
                f"tắt tin đầu tiên, KHÔNG tính là một đoạn riêng. Ví dụ ĐÚNG (1 đoạn): "
                f"\"Chuyển sang nhóm Thời sự - Xã hội, Bộ Nội vụ đề xuất bỏ thời hạn tối đa 12 "
                f"tháng đối với văn bản ủy quyền nhận lương hưu...\""
            )
        else:
            cau_dan_yeu_cau = (
                f"\n- Đoạn tin ĐẦU TIÊN trong batch này PHẢI mở đầu bằng một câu dẫn ngắn nêu "
                f"tên nhóm chủ đề mới \"{nhom_ten}\" một cách tự nhiên, theo mẫu \"Ở lĩnh vực "
                f"{nhom_ten}, ...\", rồi nối NGAY vào nội dung tin đó trong CÙNG một đoạn."
            )

    mo_dau_yeu_cau = ""
    if opening_style:
        mo_dau_yeu_cau = (
            f"\n- Câu ĐẦU TIÊN của đoạn tin đầu tiên trong batch này áp dụng phong cách: "
            f"{opening_style}"
        )

    prompt = f"""{ontology_section}Bạn đang viết PHẦN THÂN BÀI của một văn bản tóm tắt tin tức cá
        nhân hóa hàng ngày cho một người có hồ sơ sau:

        - Ngành/lĩnh vực: {persona.get('nganh_to')} - {persona.get('nganh_nho')}
        - Đơn vị công tác: {persona.get('to_chuc')}
        - Mô tả chung: {persona.get('mo_ta_chung')}

        Đây là NHÓM CHỦ ĐỀ "{nhom_ten}" (ưu tiên thứ {idx_nhom + 1}/{tong_so_nhom}), phần bạn cần
        viết là {so_tin} tin sau đây (nhóm này có thể còn phần khác đã/sẽ được viết ở request
        riêng — bạn CHỈ cần viết đúng {so_tin} tin dưới đây, không cần biết phần còn lại):
        {_dinh_dang_danh_sach_tin(batch_tin)}

        Yêu cầu mức độ chi tiết: {_muc_do_cho_tang(idx_nhom)}{khuynh_huong}{cau_dan_yeu_cau}{mo_dau_yeu_cau}

        CẤU TRÚC BẮT BUỘC: MỖI TIN viết thành MỘT ĐOẠN VĂN RIÊNG BIỆT, xuống dòng giữa các đoạn.
        SỐ ĐOẠN BẮT BUỘC: chính xác {so_tin} đoạn — trừ khi 2 tin trong batch này thật sự cùng nói
        về MỘT SỰ KIỆN CỤ THỂ giống nhau (trùng tên riêng/đơn vị/địa điểm, trùng mốc thời gian,
        trùng hành động/quyết định), khi đó được GỘP thành 1 đoạn duy nhất, tổng hợp đầy đủ chi
        tiết từ cả hai, không lặp thông tin trùng nhau. Nếu 2 tin CÙNG chủ đề nhưng là HAI SỰ KIỆN
        KHÁC NHAU thì TUYỆT ĐỐI KHÔNG gộp — mỗi tin vẫn phải có đoạn riêng. Việc xác nhận "cùng sự
        kiện" CHỈ diễn ra trong suy luận nội bộ — TUYỆT ĐỐI KHÔNG viết câu/chú thích kiểu "tin X và
        tin Y được gộp vì...", "(Ghi chú: ...)" trong bài. Bài chỉ chứa nội dung tóm tắt tự nhiên.

        KHÔNG đặt tiêu đề kiểu "Tin 1:", KHÔNG gạch đầu dòng. KHÔNG viết các đoạn theo cùng một
        khuôn mẫu số câu hay cấu trúc câu lặp lại — mỗi đoạn có độ dài và cách triển khai khác
        nhau, phản ánh đúng lượng thông tin thật có trong tin đó (có tin 1 câu, có tin 4-5 câu).

        TUYỆT ĐỐI KHÔNG dùng các cụm sau: {cam_cum_tu}. Không tự suy luận, đánh giá hoặc rút ra bài
        học nếu bài báo không nêu (không thêm "cho thấy", "phản ánh", "là lời cảnh báo", "minh
        chứng", "bài học", "gợi mở" trừ khi ý đó xuất hiện rõ trong bài gốc).

        Chỉ trả về nội dung các đoạn thân bài, không thêm lời dẫn, không thêm tiêu đề, không thêm
        mở bài hay kết luận — phần đó được viết riêng ở bước khác.
        """.strip()

    return prompt


async def viet_mot_batch(persona: dict, nhom_ten: str, idx_nhom: int, tong_so_nhom: int,
                         batch_tin: list, la_batch_dau_nhom: bool, ontology_ctx: str,
                         day_du: bool, opening_style: str, client, semaphore_summary,
                         model_name: str = OSS_MODEL_NAME) -> tuple:
    """Viết thân bài cho 1 batch, trả về (text, bi_cat_cut)."""
    prompt = build_batch_prompt(
        persona, nhom_ten, idx_nhom, tong_so_nhom, batch_tin, la_batch_dau_nhom,
        ontology_ctx, day_du, opening_style,
    )

    async def _goi(mt):
        async def _call():
            return await client.models.generate_content(
                model=model_name,
                contents=prompt,
                config={"temperature": 0.0, "max_output_tokens": mt},
            )

        async with semaphore_summary:
            return await retry_generate_async(_call)

    response = await _goi(BATCH_MAX_TOKENS)
    bi_cat_cut = getattr(response, "finish_reason", None) == "length"
    if bi_cat_cut:
        response = await _goi(BATCH_MAX_TOKENS_MO_RONG)
        bi_cat_cut = getattr(response, "finish_reason", None) == "length"

    return response.text.strip(), bi_cat_cut


def build_mo_ket_prompt(persona: dict, day_du: bool, ten_cac_nhom: list, tin_hang_dau: list,
                        closing_style: str, opening_style: str = None) -> str:
    """Prompt viết TIÊU ĐỀ + ĐOẠN MỞ BÀI (chỉ khi day_du=True) + ĐOẠN KẾT LUẬN — dựa trên nội
    dung đã cô đọng (tầng 1) của 2-3 tin ưu tiên cao nhất, KHÔNG dùng lại toàn bộ thân bài đã
    viết (tránh input phình to lại, đây chính là nguyên nhân gây lỗi 500/timeout ở bản gốc)."""
    ds_tin_hang_dau = _dinh_dang_danh_sach_tin(tin_hang_dau)
    thu_tu_nhom = " -> ".join(ten_cac_nhom)

    if day_du:
        yeu_cau = f"""Bạn cần viết 3 phần cho một văn bản tóm tắt tin tức cá nhân hóa:

        1. TIÊU ĐỀ: một dòng ngắn gọn, nêu khái quát chủ đề bản tin.
        2. MỞ BÀI (2-3 câu): nêu khái quát các nhóm chủ đề sẽ đề cập theo đúng thứ tự ưu tiên
           sau: {thu_tu_nhom}. KHÔNG đi vào số liệu cụ thể của từng tin. Phong cách câu đầu
           tiên: {opening_style}
        3. KẾT LUẬN (2-4 câu): tổng kết lại 2-3 điểm quan trọng nhất, dựa trên các tin ưu tiên
           cao nhất dưới đây, diễn đạt ngắn gọn, không lặp nguyên văn. Phong cách câu cuối
           cùng: {closing_style}

        Tham khảo nội dung các tin ưu tiên cao nhất (chỉ để nắm ý chính, KHÔNG cần nhắc chi
        tiết số liệu):
        {ds_tin_hang_dau}

        Trả về ĐÚNG định dạng (mỗi phần viết liền thành đoạn văn, không tự xuống dòng giữa
        chừng trong cùng 1 phần):
        TIÊU ĐỀ: <tiêu đề>
        MỞ BÀI: <đoạn mở bài>
        KẾT LUẬN: <đoạn kết luận>
        Không thêm chữ nào khác ngoài 3 dòng trên."""
    else:
        yeu_cau = f"""Bạn cần viết ĐOẠN KẾT LUẬN (2-4 câu) cho một văn bản tóm tắt tin tức cá
        nhân hóa, tổng kết lại 2-3 điểm quan trọng nhất, dựa trên các tin ưu tiên cao nhất dưới
        đây, diễn đạt ngắn gọn, không lặp nguyên văn. Phong cách câu cuối cùng: {closing_style}

        Tham khảo nội dung các tin ưu tiên cao nhất:
        {ds_tin_hang_dau}

        Trả về ĐÚNG định dạng:
        KẾT LUẬN: <đoạn kết luận>
        Không thêm chữ nào khác."""

    prompt = f"""Hồ sơ người đọc:
        - Ngành/lĩnh vực: {persona.get('nganh_to')} - {persona.get('nganh_nho')}
        - Đơn vị công tác: {persona.get('to_chuc')}

        {yeu_cau}

        TUYỆT ĐỐI KHÔNG lặp lại nguyên văn câu đã có trong nội dung tin tham khảo ở trên — phải
        diễn đạt lại. Không tự suy luận, đánh giá nếu tin không nêu rõ.
        """.strip()

    return prompt


async def viet_mo_ket(persona: dict, day_du: bool, ten_cac_nhom: list, tin_hang_dau: list,
                      opening_style: str, closing_style: str, client, semaphore_summary,
                      model_name: str = OSS_MODEL_NAME) -> tuple:
    """Trả về (tieu_de, mo_bai, ket_luan, bi_cat_cut). tieu_de/mo_bai rỗng khi day_du=False."""
    prompt = build_mo_ket_prompt(persona, day_du, ten_cac_nhom, tin_hang_dau, closing_style,
                                 opening_style)

    async def _goi(mt):
        async def _call():
            return await client.models.generate_content(
                model=model_name,
                contents=prompt,
                config={"temperature": 0.0, "max_output_tokens": mt},
            )

        async with semaphore_summary:
            return await retry_generate_async(_call)

    response = await _goi(MO_KET_MAX_TOKENS)
    bi_cat_cut = getattr(response, "finish_reason", None) == "length"
    if bi_cat_cut:
        response = await _goi(MO_KET_MAX_TOKENS_MO_RONG)
        bi_cat_cut = getattr(response, "finish_reason", None) == "length"

    text = response.text.strip()

    def _trich(nhan: str) -> str:
        m = re.search(rf"{nhan}\s*:\s*(.+?)(?=\n[A-ZÀ-Ỹ ]{{2,}}:|\Z)", text, re.DOTALL)
        return m.group(1).strip() if m else ""

    tieu_de = _trich("TIÊU ĐỀ")
    mo_bai = _trich("MỞ BÀI")
    ket_luan = _trich("KẾT LUẬN")

    return tieu_de, mo_bai, ket_luan, bi_cat_cut


def build_lien_quan_prompt(persona: dict, tin_gian_tiep: list, bai_lien_quan: list) -> str:
    khoi_gian_tiep_text = ""
    if tin_gian_tiep:
        khoi_gian_tiep_text = f"""
        NHÓM TIN LIÊN QUAN GIÁN TIẾP (ngoài chủ đề chính, nhưng có liên hệ nhẹ, gồm
        {len(tin_gian_tiep)} tin):
        {_dinh_dang_danh_sach_tin(tin_gian_tiep, dung_full_content=False)}
        Yêu cầu:
        - CHỈ giữ lại tin có giá trị tham khảo thực sự rõ ràng; MẠNH DẠN bỏ hẳn tin liên quan
          lỏng lẻo, kể cả khi phải bỏ nguyên một nhóm chủ đề trong danh sách trên.
        - Tổng độ dài KHÔNG vượt quá 1-2 đoạn văn ngắn — ưu tiên súc tích.
        - MỖI đoạn PHẢI bắt đầu bằng cụm báo hiệu tin ngoài chuyên môn chính, ví dụ "Các tin
          khác đáng chú ý:", "Về [chủ đề X]:".
        - Mỗi tin chỉ giữ đúng ý quan trọng nhất (khoảng 1 câu/tin), không mô tả chi tiết.
        - Nếu nhiều tin cùng sự kiện/chủ đề thì gộp thành một câu.
        """

    khoi_bai_text = ""
    if bai_lien_quan:
        khoi_bai_text = f"""
        NHÓM BÀI GÓC NHÌN/PHÂN TÍCH LIÊN QUAN (không phải tin thời sự, gồm {len(bai_lien_quan)}
        bài):
        {_dinh_dang_danh_sach_tin(bai_lien_quan, dung_full_content=False)}
        Yêu cầu:
        - Tóm tắt súc tích quan điểm/góc nhìn chính của MỖI bài trong 1 đoạn ngắn riêng.
        - CHỈ đoạn ĐẦU TIÊN của nhóm này bắt đầu bằng cụm "Góc nhìn liên quan:" — các đoạn tiếp
          theo trong CÙNG nhóm KHÔNG lặp lại cụm này.
        """

    prompt = f"""Bạn đang viết PHẦN CUỐI (phụ, không phải trọng tâm) của một văn bản tóm tắt tin
        tức cá nhân hóa cho một người thuộc ngành {persona.get('nganh_to')} - {persona.get('nganh_nho')}.
        {khoi_gian_tiep_text}
        {khoi_bai_text}
        Đặt nhóm tin liên quan gián tiếp trước, nhóm bài góc nhìn sau (nếu có cả 2). Chỉ trả về
        nội dung các đoạn văn, không thêm lời dẫn, không thêm tiêu đề.
        """.strip()

    return prompt


async def viet_phan_lien_quan(persona: dict, tin_gian_tiep: list, bai_lien_quan: list,
                              client, semaphore_summary, model_name: str = OSS_MODEL_NAME) -> tuple:
    if not tin_gian_tiep and not bai_lien_quan:
        return "", False

    prompt = build_lien_quan_prompt(persona, tin_gian_tiep, bai_lien_quan)

    async def _goi(mt):
        async def _call():
            return await client.models.generate_content(
                model=model_name,
                contents=prompt,
                config={"temperature": 0.0, "max_output_tokens": mt},
            )

        async with semaphore_summary:
            return await retry_generate_async(_call)

    response = await _goi(LIEN_QUAN_MAX_TOKENS)
    bi_cat_cut = getattr(response, "finish_reason", None) == "length"
    if bi_cat_cut:
        response = await _goi(LIEN_QUAN_MAX_TOKENS_MO_RONG)
        bi_cat_cut = getattr(response, "finish_reason", None) == "length"

    return response.text.strip(), bi_cat_cut


def _chia_batch(danh_sach: list, kich_thuoc: int) -> list:
    """Chia 1 danh sách thành các batch con liên tiếp, mỗi batch tối đa kich_thuoc phần tử."""
    return [danh_sach[i:i + kich_thuoc] for i in range(0, len(danh_sach), kich_thuoc)]


async def tom_tat_rss_cho_persona(persona: dict, articles: list, client, semaphore, semaphore_summary,
                                  model_name: str = OSS_MODEL_NAME, variant: str = None,
                                  bai_candidates_da_tom_tat: list = None) -> dict:
    ranked_truoc_loc = xep_hang_bai_cho_persona(persona, articles)

    if not ranked_truoc_loc:
        return {
            "id": persona.get("id"),
            "summary": "",
            "ranked_articles": [],
            "note": "Không có tin nào khớp chu_de của persona này.",
        }

    ranked, bai_bi_ha = await loc_bai_lien_quan_persona_co_cache(
        persona, ranked_truoc_loc, client, semaphore, variant=variant
    )

    ranked, ten_cac_nhom_bi_khoi_phuc = _khoi_phuc_tin_cho_nhom_bi_ha_het(
        lay_chu_de_hieu_luc(persona), ranked_truoc_loc, ranked
    )
    if ten_cac_nhom_bi_khoi_phuc:
        print(
            f"[tom_tat_rss_cho_persona] [{persona.get('id')}] CẢNH BÁO: "
            f"{len(ten_cac_nhom_bi_khoi_phuc)} nhóm chủ đề bị bước lọc giu/ha đánh 'ha' HẾT toàn bộ "
            f"tin ({', '.join(ten_cac_nhom_bi_khoi_phuc)}) -> mỗi nhóm đó chỉ lấy lại tối đa "
            f"{SO_TIN_TOI_DA_FALLBACK_MOI_NHOM} tin điểm cao nhất, KHÔNG lấy lại toàn bộ danh sách "
            f"ban đầu."
        )
        link_da_giu = {a.get("link") for a in ranked}
        bai_bi_ha = [a for a in bai_bi_ha if a.get("link") not in link_da_giu]

    khong_co_tin_huu_ich = not ranked
    if khong_co_tin_huu_ich:
        print(
            f"[tom_tat_rss_cho_persona] [{persona.get('id')}] CẢNH BÁO: bước lọc giu/ha đánh "
            f"'ha' cho TOÀN BỘ {len(ranked_truoc_loc)} tin khớp chủ đề chính -> fallback dùng "
            f"lại danh sách trước khi lọc để tránh mất sạch nội dung nhóm chủ đề chính."
        )
        ranked = ranked_truoc_loc
        bai_bi_ha = []

    tom_tat_map = await tom_tat_nhieu_bai(ranked, client, semaphore)
    ranked = [
        {**a, "content": tom_tat_map.get(a.get("link"), a.get("summary", ""))}
        for a in ranked
    ]

    nhom_tin = nhom_tin_theo_chu_de(persona, ranked)
    so_bai_moi_nhom = [{"chu_de": n["chu_de"], "so_bai": len(n["bai"])} for n in nhom_tin]
    tin_gian_tiep = bai_bi_ha + tim_tin_lien_quan_gian_tiep(persona, articles, ranked)

    if bai_candidates_da_tom_tat is None:
        bai_candidates = [a for a in articles if a.get("loai_bai") == "bài"]
        tom_tat_map_bai = await tom_tat_nhieu_bai(bai_candidates, client, semaphore)
        bai_candidates_da_tom_tat = [
            {**a, "content": tom_tat_map_bai.get(a.get("link"), a.get("summary", ""))}
            for a in bai_candidates
        ]
    bai_lien_quan = await loc_bai_loai_bai_cho_persona(persona, bai_candidates_da_tom_tat, client, semaphore)

    so_bai = len(ranked) + len(tin_gian_tiep)
    so_tin_chinh = len(ranked)
    print(f"[tom_tat_rss_cho_persona] [{persona.get('id')}] so_bai={so_bai}, "
          f"so_tin_chinh={so_tin_chinh}, so_nhom={len(nhom_tin)}")

    day_du = can_van_phong_day_du(persona, ranked)
    ontology_ctx = lay_ontology_context_cho_nganh(persona.get("nganh_to", ""))
    opening_style = (
        _chon_style(persona.get("id", ""), OPENING_STYLES_MO_BAI)
        if day_du
        else _chon_style(persona.get("id", ""), OPENING_STYLES)
    )
    closing_style = _chon_style(persona.get("id", "") + "_close", CLOSING_STYLES)

    viec_can_lam = []
    for idx_nhom, n in enumerate(nhom_tin):
        cac_batch_cua_nhom = _chia_batch(n["bai"], SO_TIN_MOI_BATCH)
        for idx_batch, batch_tin in enumerate(cac_batch_cua_nhom):
            viec_can_lam.append({
                "idx_nhom": idx_nhom,
                "idx_batch": idx_batch,
                "nhom_ten": n["chu_de"],
                "batch_tin": batch_tin,
                "la_batch_dau_nhom": idx_batch == 0,
                "la_batch_dau_toan_bai": idx_nhom == 0 and idx_batch == 0,
            })

    async def _xu_ly_1_viec(viec):
        text, bi_cat = await viet_mot_batch(
            persona, viec["nhom_ten"], viec["idx_nhom"], len(nhom_tin), viec["batch_tin"],
            viec["la_batch_dau_nhom"], ontology_ctx, day_du,
            opening_style if viec["la_batch_dau_toan_bai"] else None,
            client, semaphore_summary, model_name,
        )
        return {**viec, "text": text, "bi_cat_cut": bi_cat}

    ket_qua_batch = await asyncio.gather(*[_xu_ly_1_viec(v) for v in viec_can_lam])
    ket_qua_batch.sort(key=lambda r: (r["idx_nhom"], r["idx_batch"]))

    than_bai_doan = [r["text"] for r in ket_qua_batch if r["text"]]
    bi_cat_cut_batch = any(r["bi_cat_cut"] for r in ket_qua_batch)

    if not day_du and nhom_tin:
        than_bai_doan = [f"Về {nhom_tin[0]['chu_de']}:"] + than_bai_doan

    ten_cac_nhom = [n["chu_de"] for n in nhom_tin]
    tin_hang_dau = ranked[:3]
    tieu_de, mo_bai, ket_luan, bi_cat_cut_mo_ket = await viet_mo_ket(
        persona, day_du, ten_cac_nhom, tin_hang_dau, opening_style, closing_style,
        client, semaphore_summary, model_name,
    )

    doan_lien_quan, bi_cat_cut_lien_quan = await viet_phan_lien_quan(
        persona, tin_gian_tiep, bai_lien_quan, client, semaphore_summary, model_name,
    )

    cac_phan = []
    if day_du and tieu_de:
        cac_phan.append(tieu_de)
    if day_du and mo_bai:
        cac_phan.append(mo_bai)
    cac_phan.extend(than_bai_doan)
    if doan_lien_quan:
        cac_phan.append(doan_lien_quan)
    if ket_luan:
        cac_phan.append(ket_luan)

    summary = "\n\n".join(doan for doan in cac_phan if doan.strip())

    bi_cat_cut = bi_cat_cut_batch or bi_cat_cut_mo_ket or bi_cat_cut_lien_quan
    so_doan_thuc_te = len([doan for doan in summary.split("\n\n") if doan.strip()])
    ti_le_bao_phu = so_doan_thuc_te / so_tin_chinh if so_tin_chinh else 0.0

    notes = []
    if not nhom_tin:
        notes.append(
            f"Nhóm chủ đề chính rỗng sau khi lọc giu/ha (có thể do bước lọc đánh 'ha' cho toàn bộ "
            f"tin, xem log CẢNH BÁO fallback ở trên nếu có), hoặc thực sự không có tin khớp chu_de."
        )
    elif nhom_tin[0]["chu_de"] != lay_chu_de_hieu_luc(persona)[0]:
        notes.append(
            f"Không có tin nào khớp đúng chủ đề chuyên môn chính "
            f"(\"{lay_chu_de_hieu_luc(persona)[0]}\") trong đợt tin này."
        )
    if bi_cat_cut:
        notes.append(
            "CẢNH BÁO: có ít nhất 1 phần (batch thân bài / mở-kết / tin liên quan) có thể bị "
            "CẮT CỤT dù đã thử lại với max_tokens cao hơn — cần xem lại persona này riêng."
        )
    if ti_le_bao_phu < TI_LE_BAO_PHU_TOI_THIEU:
        notes.append(
            f"CẢNH BÁO: bài viết chỉ có {so_doan_thuc_te} đoạn, trong khi nhóm tin chính có "
            f"{so_tin_chinh} tin — có khả năng model đã tự gộp hoặc bỏ bớt tin."
        )
    if co_chu_thich_thua(summary):
        notes.append(
            "CẢNH BÁO: bài viết có thể chứa chú thích/ghi chú thừa về quá trình viết bài "
            "(vd: '(Ghi chú: ...)', '(đã gộp tin...)') — cần xem lại thủ công."
        )
    if khong_co_tin_huu_ich:
        notes.append(
            "Không có tin nào được đánh giá thực sự hữu ích cho persona này "
            "(LLM lọc loại toàn bộ ở bước 'giu/ha/loai') — bản tóm tắt dưới đây "
            "dùng lại toàn bộ tin cùng chủ đề chuyên môn (chưa qua bước lọc hữu ích)."
        )

    ket_qua = {
        "id": persona.get("id"),
        "summary": summary,
        "day_du": day_du,
        "so_luong_tin_da_dua_vao": so_bai,
        "so_nhom_chu_de": len(nhom_tin),
        "so_bai_moi_nhom": so_bai_moi_nhom,
        "so_batch_tang_2": len(viec_can_lam),
        "so_doan_thuc_te": so_doan_thuc_te,
        "ti_le_bao_phu": round(ti_le_bao_phu, 2),
        "than_bai_theo_batch": [
            {
                "nhom_chu_de": r["nhom_ten"],
                "tin_links": [a.get("link") for a in r["batch_tin"]],
                "text": r["text"],
            }
            for r in ket_qua_batch if r["text"]
        ],
        "ranked_articles": [
            {"title": a["title"], "genre": a["genre"], "genre_score": a["genre_score"], "link": a.get("link")}
            for a in ranked
        ],
        "tin_gian_tiep": [
            {"title": a["title"], "genre": a["genre"], "genre_score": a["genre_score"], "link": a.get("link")}
            for a in tin_gian_tiep
        ],
        "bai_lien_quan": [
            {"title": a["title"], "link": a.get("link")} for a in bai_lien_quan
        ],
    }
    if notes:
        ket_qua["note"] = " | ".join(notes)

    return ket_qua


if __name__ == "__main__":
    import argparse
    import time

    parser = argparse.ArgumentParser(description="Tóm tắt RSS cá nhân hóa")

    parser.add_argument(
        "--id",
        type=str,
        help="id của persona, ví dụ NN0001"
    )

    parser.add_argument(
        "-n", "--so-luong",
        type=int,
        help="Chỉ duyệt N persona đầu tiên"
    )

    parser.add_argument(
        "--variant",
        type=str,
        default=None,
        help="tên biến thể persona (vd nt_nn_tc_kn_cd), nếu có sẽ ghi vào thư mục con riêng để tránh đè lên dữ liệu persona đầy đủ trường"
    )
    args = parser.parse_args()

    with open(DATA_DIR / "vnexpress_rss_snapshot_3007.json", encoding="utf-8") as f:
        articles = json.load(f)

    ten_file_persona = f"state_profiles_{args.variant}.json" if args.variant else "state_profiles_nt_nn_tc_kn_cd_ch.json"
    with open(MD_ROOT / "data" / "profile_variants" / ten_file_persona, encoding="utf-8") as f:
        personas = json.load(f)

    articles = gan_genre_cho_bai(articles)

    if args.variant:
        JSON_DIR = OUTPUT_DIR / "json" / args.variant
        MD_DIR = OUTPUT_DIR / "md" / args.variant
    else:
        JSON_DIR = OUTPUT_DIR / "json"
        MD_DIR = OUTPUT_DIR / "md"
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    MD_DIR.mkdir(parents=True, exist_ok=True)


    async def xu_ly_mot_persona(client, semaphore, semaphore_summary, persona, bai_candidates_da_tom_tat):
        persona_id = persona["id"]
        out_path_json = JSON_DIR / f"{persona_id}.json"
        if out_path_json.exists():
            print(f"[{persona_id}] đã có kết quả rồi, bỏ qua.")
            return

        print(f"[{persona_id}] bắt đầu xử lý...")
        t0 = time.time()

        try:
            ket_qua = await tom_tat_rss_cho_persona(
                persona, articles, client, semaphore, semaphore_summary,
                variant=args.variant, bai_candidates_da_tom_tat=bai_candidates_da_tom_tat,
            )
        except Exception as e:
            print(f"[{persona_id}] LỖI, bỏ qua persona này: {e}")
            return

        with open(out_path_json, "w", encoding="utf-8") as f:
            json.dump(ket_qua, f, ensure_ascii=False, indent=2)

        out_path_md = MD_DIR / f"{persona_id}.md"
        with open(out_path_md, "w", encoding="utf-8") as f:
            f.write(ket_qua["summary"])

        print(f"[{persona_id}] xong, mất {time.time() - t0:.1f}s")


    async def chay():
        client = tao_oss_client_async()
        semaphore = asyncio.Semaphore(OSS_MAX_CONCURRENCY)
        semaphore_summary = asyncio.Semaphore(OSS_MAX_CONCURRENCY_SUMMARY)

        print("Tóm tắt trước 1 lần cho toàn bộ 'bài' góc nhìn (dùng chung cho mọi persona)...")
        bai_candidates = [a for a in articles if a.get("loai_bai") == "bài"]
        tom_tat_map_bai = await tom_tat_nhieu_bai(bai_candidates, client, semaphore)
        bai_candidates_da_tom_tat = [
            {**a, "content": tom_tat_map_bai.get(a.get("link"), a.get("summary", ""))}
            for a in bai_candidates
        ]
        print(f"Đã tóm tắt xong {len(bai_candidates_da_tom_tat)} bài, bắt đầu xử lý từng persona.")

        if args.id:
            persona = next((p for p in personas if p.get("id") == args.id), None)
            if persona is None:
                raise SystemExit(f"Không tìm thấy persona có id = {args.id}")

            await xu_ly_mot_persona(client, semaphore, semaphore_summary, persona, bai_candidates_da_tom_tat)

            print(f"Đã ghi json: {JSON_DIR / f'{persona['id']}.json'}")
            print(f"Đã ghi md:   {MD_DIR / f'{persona['id']}.md'}")
        else:
            danh_sach_persona = personas
            if args.so_luong:
                danh_sach_persona = danh_sach_persona[:args.so_luong]
            print("Tổng số persona cần duyệt:", len(danh_sach_persona))
            t_bat_dau = time.time()

            tasks = [
                xu_ly_mot_persona(client, semaphore, semaphore_summary, p, bai_candidates_da_tom_tat)
                for p in danh_sach_persona
            ]
            await asyncio.gather(*tasks)

            print(
                "\nXONG HẾT. Tổng thời gian:",
                round((time.time() - t_bat_dau) / 60, 1),
                "phút"
            )

    asyncio.run(chay())