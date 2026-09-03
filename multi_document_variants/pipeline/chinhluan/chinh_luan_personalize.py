import re
import json
import argparse
import asyncio
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]

from pipeline.utils import (
    retry_generate_async, OSS_MODEL_NAME, load_graph,
    tao_oss_client_async, lay_chu_de_hieu_luc,
    OSS_MAX_CONCURRENCY_SUMMARY, uoc_luong_so_token,
)
from pipeline.profiles.ontology_context_state import lay_ontology_context_cho_nganh
from pipeline.baochi.rss_personalize import (
    classify_genre_rss,
    lay_chuc_vu,
    _chon_style,
    CHUC_VU_LANH_DAO_KEYWORDS,
    GENRE_LUON_DAY_DU,
    SO_CHU_DE_UU_TIEN_TOI_DA_CHO_DAY_DU,
)

from pipeline.chinhluan.chinh_luan_extract import xu_ly_mot_bai
from pipeline.chinhluan.chinh_luan_phan_tich_lap_luan import goi_llm_phan_tich_async

_ONTOLOGY_PATH = ROOT_DIR / "persona_states.ttl"
_STATE_GRAPH = load_graph(str(_ONTOLOGY_PATH))

PROFILE_PATH = ROOT_DIR / "data" / "profile_variants" / "state_profiles_nt_nn_tc_kn_cd_ch.json"

DUONG_DAN_RAW_MAC_DINH = "data/chinh_luan/nhandan_chinhluan.json"
DUONG_DAN_INPUT_MAC_DINH = "output/chinh_luan/phan_tich_lap_luan/tung_bai"
DUONG_DAN_OUTPUT_MAC_DINH = "output/chinh_luan/summary"

NGUONG_KHOP_GENRE = 0.6

CHINH_LUAN_MAX_OUTPUT_TOKENS = 4000
CHINH_LUAN_MAX_OUTPUT_TOKENS_MO_RONG = 8000

OPENING_STYLES_MO_BAI_CHINH_LUAN = [
    "Mở bằng một câu nêu khái quát đúng vấn đề mà bài chính luận đề cập, có thể nhắc thẳng vấn đề/bối cảnh cụ thể của bài, KHÔNG đi vào chi tiết từng luận điểm.",
    "Mở bằng cách nêu mối liên hệ giữa vấn đề của bài với định hướng công việc trước mắt của người đọc, có thể nhắc rõ vấn đề cụ thể, KHÔNG đi vào nội dung từng luận điểm.",
    "Mở bằng một nhận định ngắn gọn về tầm quan trọng/bối cảnh của vấn đề bài viết đề cập, có thể nêu rõ vấn đề đó là gì, KHÔNG liệt kê các luận điểm cụ thể.",
    "Mở bằng cách nêu thẳng vấn đề chính của bài dưới dạng một câu khẳng định ngắn gọn, không dùng từ 'bối cảnh' hay 'trong bối cảnh', KHÔNG đi vào chi tiết từng luận điểm.",
]

OPENING_STYLES_CHINH_LUAN = [
    "Mở thẳng bằng vấn đề cụ thể nhất mà bài chính luận đề cập, không dẫn dắt, không nêu bối cảnh chung.",
    "Mở bằng cách liên hệ trực tiếp vấn đề của bài tới mối quan tâm hoặc nhiệm vụ hiện tại của người đọc, rồi mới đi vào nội dung.",
    "Mở bằng một nhận định hoặc câu hỏi ngắn liên quan trực tiếp đến công việc của người đọc, sau đó lập tức nối vào vấn đề chính của bài.",
    "Mở bằng cách tóm tắt nhanh vấn đề chính của bài dưới dạng một câu khẳng định, không dùng từ 'bối cảnh' hay 'trong bối cảnh'.",
]

CLOSING_STYLES_CHINH_LUAN = [
    "Kết bằng cách diễn đạt lại trực tiếp, dứt khoát đúng nội dung kết luận/lời kêu gọi của tác giả, không dùng cụm 'nhìn chung' hay 'kết lại'.",
    "Kết bằng cách nhấn mạnh lại tầm quan trọng của vấn đề trước khi nêu đúng kết luận/lời kêu gọi của tác giả, không lặp nguyên văn câu đã dùng ở thân bài.",
    "Kết bằng cách liên hệ ngắn gọn kết luận với vấn đề đã nêu ở đầu bài, sau đó khẳng định lại đúng lời kêu gọi/kết luận gốc.",
    "Kết bằng một câu khẳng định dứt khoát đúng tinh thần kết luận/lời kêu gọi của tác giả, KHÔNG thêm bất kỳ khuyến nghị, đề xuất hay gợi ý hành động/theo dõi nào ngoài nội dung đó.",
]

# ==== BƯỚC 1: XÁC ĐỊNH STYLE THEO CHỦ ĐỀ CỦA PERSONA ====

def xac_dinh_style(persona: dict, genre: str, genre_score: float) -> str:
    chu_de_list = lay_chu_de_hieu_luc(persona)
    if not chu_de_list or genre_score < NGUONG_KHOP_GENRE:
        return "binh_thuong"

    if genre == chu_de_list[0]:
        return "chuyen_sau"
    if genre in chu_de_list[1:]:
        return "khong_chuyen_mon"
    return "binh_thuong"


# ==== BƯỚC 2: TEXT HƯỚNG DẪN VĂN PHONG THEO STYLE ====
STYLE_INSTRUCTIONS = {
    "chuyen_sau": (
        "Persona này CÓ chuyên môn đúng lĩnh vực/chủ đề của bài viết. Trình bày "
        "văn phong chuyên nghiệp, sử dụng thuật ngữ chính trị - hành chính - pháp "
        "lý một cách TỰ NHIÊN, KHÔNG cần giải thích lại các khái niệm cơ bản. Có "
        "thể đi sâu vào ý nghĩa, tầm quan trọng của từng luận điểm đối với công "
        "việc/lĩnh vực của persona, nhưng KHÔNG được tự thêm nhận định, đánh giá "
        "không có trong bài gốc."
    ),
    "khong_chuyen_mon": (
        "Persona này KHÔNG có chuyên môn đúng lĩnh vực/chủ đề của bài viết (chỉ "
        "liên quan ở mức độ chung). Trình bày CHI TIẾT hơn, dùng ngôn ngữ phổ "
        "thông, dễ hiểu. BẮT BUỘC mỗi thuật ngữ chính trị/hành chính/pháp lý/đối "
        "ngoại xuất hiện trong bài đều phải có giải thích ngắn gọn NGAY TRONG "
        "CÙNG CÂU (đặt trong ngoặc đơn hoặc nối bằng cụm từ giải nghĩa tự nhiên), "
        "không để thuật ngữ đứng một mình không giải thích."
    ),
    "binh_thuong": (
        "Persona này HOÀN TOÀN KHÔNG liên quan chuyên môn tới chủ đề của bài viết. "
        "Trình bày càng đơn giản, dễ hiểu càng tốt, ưu tiên diễn đạt bằng ngôn ngữ "
        "đời thường. BẮT BUỘC mỗi thuật ngữ chính trị/hành chính/pháp lý/đối ngoại "
        "xuất hiện trong bài đều phải có giải thích ngắn gọn NGAY TRONG CÙNG CÂU, "
        "tương tự yêu cầu ở mức 'khong_chuyen_mon' nhưng cần đơn giản hóa mạnh hơn "
        "nữa - hạn chế tối đa việc dùng từ chuyên ngành nếu có thể diễn đạt lại "
        "bằng từ phổ thông mà không làm sai lệch ý nghĩa."
    ),
}

LOAI_CHINH_LUAN_HIEN_THI = {
    "xa_luan": "xã luận",
    "binh_luan_phe_phan": "bình luận - phê phán",
    "khac": "chính luận",
}


# ==== BƯỚC 2b: XÁC ĐỊNH ĐỊNH DẠNG (ĐẦY ĐỦ vs VÀO THẲNG VẤN ĐỀ) ====
NGUONG_KINH_NGHIEM_TRANG_TRONG = 25


def lay_so_nam_kinh_nghiem(kinh_nghiem_text: str) -> int:
    match = re.search(r"(\d+)\s*năm kinh nghiệm", kinh_nghiem_text or "")
    return int(match.group(1)) if match else 0


def can_van_phong_day_du_chinh_luan(persona: dict, genre: str, loai_chinh_luan: str) -> bool:
    # Xã luận là thể loại chính thức, định hướng - luôn dùng văn phong trang trọng
    if loai_chinh_luan == "xa_luan":
        return True

    chuc_vu = lay_chuc_vu(persona.get("kinh_nghiem", "")).lower()
    if any(kw in chuc_vu for kw in CHUC_VU_LANH_DAO_KEYWORDS):
        return True
    if lay_so_nam_kinh_nghiem(persona.get("kinh_nghiem", "")) >= NGUONG_KINH_NGHIEM_TRANG_TRONG:
        return True

    chu_de_uu_tien_cao = set(lay_chu_de_hieu_luc(persona)[:SO_CHU_DE_UU_TIEN_TOI_DA_CHO_DAY_DU])
    if genre in GENRE_LUON_DAY_DU and genre in chu_de_uu_tien_cao:
        return True

    return False

# ==== BƯỚC 3: DỰNG PROMPT ====

def _dinh_dang_danh_sach_luan_diem(phan_tich: dict) -> str:
    danh_sach = phan_tich.get("danh_sach_luan_diem", [])
    ds_text = ""
    for i, ld in enumerate(danh_sach, 1):
        luan_cu = ", ".join(ld.get("luan_cu_lien_quan", []))
        quan_he_text = ""
        if ld.get("quan_he"):
            nhan_quan_he = {
                "nhan_qua": "là NGUYÊN NHÂN/HỆ QUẢ của",
                "phan_bien": "PHẢN BIỆN/đối lập với",
                "bo_sung": "BỔ SUNG thêm ý cho",
            }.get(ld["quan_he"], ld["quan_he"])
            quan_he_text = (
                f" (luận điểm này {nhan_quan_he} luận điểm số "
                f"{ld.get('quan_he_voi_luan_diem_so')} — bản tóm tắt PHẢI thể hiện "
                f"rõ mối quan hệ này bằng từ nối phù hợp, không viết 2 luận điểm "
                f"như 2 ý độc lập rời rạc)"
            )
        ds_text += (
            f"\n{i}. {ld.get('luan_diem')}\n"
            f"   Luận cứ chứng minh: {luan_cu}{quan_he_text}\n"
        )
    return ds_text


def _dinh_dang_bo_cuc(persona: dict, genre: str, van_de: str, loai_chinh_luan: str) -> tuple:
    day_du = can_van_phong_day_du_chinh_luan(persona, genre, loai_chinh_luan)
    opening_style = (
        _chon_style(persona.get("id", ""), OPENING_STYLES_MO_BAI_CHINH_LUAN)
        if day_du
        else _chon_style(persona.get("id", ""), OPENING_STYLES_CHINH_LUAN)
    )
    closing_style = _chon_style(persona.get("id", "") + "_close", CLOSING_STYLES_CHINH_LUAN)

    if day_du:
        text = f"""- ĐỊNH DẠNG: bài viết PHẢI có bố cục ĐẦY ĐỦ, trang trọng, gồm 3 phần rõ ràng, cách nhau bằng dấu xuống dòng:
      1. TIÊU ĐỀ: 1 dòng in đậm/viết hoa đứng đầu tiên, ngắn gọn, khái quát đúng vấn đề bài chính luận đề cập (dựa trên "{van_de}"), không copy nguyên văn tiêu đề gốc của bài báo.
      2. MỞ BÀI: đoạn riêng ngay sau tiêu đề, 2-3 câu nêu khái quát vấn đề của bài, KHÔNG đi vào chi tiết từng luận điểm cụ thể. Câu đầu tiên áp dụng phong cách: {opening_style}
      3. THÂN BÀI: trình bày lần lượt các luận điểm theo đúng thứ tự đã liệt kê bên dưới, mỗi luận điểm gắn liền với luận cứ chứng minh tương ứng.
      4. KẾT BÀI: đoạn riêng, đứng cuối cùng, nêu lại kết luận và lời kêu gọi của tác giả. Câu cuối cùng của toàn bài áp dụng phong cách: {closing_style}"""
    else:
        text = f"""- ĐỊNH DẠNG: bài viết KHÔNG có tiêu đề riêng và KHÔNG cần tách bạch bố cục mở-thân-kết - viết thẳng vào vấn đề ngay từ câu/dòng đầu tiên, ngắn gọn, dễ đọc. Câu đầu tiên áp dụng phong cách: {opening_style}
      Dù không tách bố cục, bài vẫn phải đi đủ trình tự Vấn đề -> Luận điểm -> Luận cứ -> Kết luận về mặt nội dung. Câu cuối cùng của toàn bài áp dụng phong cách: {closing_style}"""

    return text, day_du


def build_chinh_luan_prompt(persona: dict, bai: dict, style: str, genre: str) -> tuple:
    loai = bai.get("loai_chinh_luan", "khac")
    loai_hien_thi = LOAI_CHINH_LUAN_HIEN_THI.get(loai, "chính luận")
    phan_tich = bai.get("phan_tich_lap_luan", {})

    ontology_ctx = lay_ontology_context_cho_nganh(persona.get("nganh_to", ""))

    ontology_section = ""
    if ontology_ctx:
        ontology_section = f"""
    PHẦN 1: KHUNG PHÂN TÍCH NGÀNH CÔNG VỤ (Ontology Context)
    {ontology_ctx}

    """

    yeu_cau_van_phong = STYLE_INSTRUCTIONS.get(style, STYLE_INSTRUCTIONS["binh_thuong"])
    danh_sach_luan_diem_text = _dinh_dang_danh_sach_luan_diem(phan_tich)
    yeu_cau_dinh_dang, day_du = _dinh_dang_bo_cuc(
        persona, genre, phan_tich.get("van_de", ""), loai
    )

    prompt = f"""{ontology_section}Bạn đang tóm tắt cá nhân hóa 1 bài {loai_hien_thi} từ báo Nhân Dân cho một cán bộ có hồ sơ công vụ sau:

    - Ngành/lĩnh vực: {persona.get('nganh_to')} - {persona.get('nganh_nho')}
    - Đơn vị công tác: {persona.get('to_chuc')}
    - Mô tả chung: {persona.get('mo_ta_chung')}

    YÊU CẦU VĂN PHONG (áp dụng cho toàn bộ bài tóm tắt):
    {yeu_cau_van_phong}

    Dưới đây là cấu trúc lập luận đã được phân tích sẵn từ bài viết gốc. Bạn KHÔNG được cấp toàn
    văn gốc của bài - hãy coi TOÀN BỘ nội dung dưới đây (vấn đề, danh sách luận điểm, luận cứ, kết
    luận) là NGUỒN THÔNG TIN DUY NHẤT và ĐẦY ĐỦ để viết bản tóm tắt. Đây là KHUNG BẮT BUỘC phải bám
    theo, KHÔNG tự suy đoán hay bổ sung chi tiết nào ngoài phạm vi thông tin được cấp dưới đây:

    Vấn đề: {phan_tich.get('van_de', '')}

    Danh sách luận điểm (TẤT CẢ đều PHẢI xuất hiện trong bản tóm tắt, không được bỏ bất kỳ luận điểm nào dù dài hay ngắn):
    {danh_sach_luan_diem_text}

    Kết luận và lời kêu gọi của tác giả (PHẢI giữ đúng tinh thần, không suy diễn thêm, không làm thay đổi lập trường):
    {phan_tich.get('ket_luan_va_loi_keu_goi', '')}

    QUY TẮC BẮT BUỘC:
    - Giữ ĐÚNG lập trường và quan điểm gốc của tác giả. KHÔNG thêm ý kiến cá nhân của AI, KHÔNG diễn giải theo hướng trái ngược hoặc trung lập hóa thông điệp gốc. Đây là bài chính luận có lập trường rõ ràng, không phải tin tức khách quan - PHẢI giữ nguyên tính thuyết phục và lập trường đó.
    - Cấu trúc bài tóm tắt PHẢI đi theo đúng trình tự: Vấn đề -> Luận điểm -> Luận cứ (dẫn chứng chứng minh) -> Kết luận, giống cấu trúc gốc của bài.
    - MỌI luận điểm trong danh sách ở trên đều PHẢI xuất hiện trong bản tóm tắt, chỉ được điều chỉnh ĐỘ DÀI/ĐỘ CHI TIẾT/CÁCH DIỄN ĐẠT theo yêu cầu văn phong ở trên - TUYỆT ĐỐI KHÔNG được bỏ hẳn một luận điểm chỉ vì nó không liên quan sát tới chuyên môn của persona.
    - PHẢI bảo toàn đúng MỌI quan hệ lập luận đã ghi kèm ở từng luận điểm (xem chú thích trong ngoặc ở danh sách luận điểm bên trên) - dù là nhân quả, phản biện hay bổ sung, đều phải thể hiện rõ bằng từ nối phù hợp trong bản tóm tắt, không viết các luận điểm có quan hệ với nhau như những ý độc lập rời rạc.
    - PHẢI giữ lại kết luận và lời kêu gọi (nếu có) của tác giả, đúng tinh thần đã nêu ở trên.
    - Cá nhân hóa được thực hiện qua việc điều chỉnh TRỌNG TÂM (luận điểm liên quan tới công việc của persona có thể được nhấn mạnh, viết diễn giải kỹ hơn một chút), MỨC ĐỘ CHI TIẾT và CÁCH DIỄN ĐẠT - KHÔNG được thông qua việc bỏ sót hoặc thiên lệch nội dung.
    {yeu_cau_dinh_dang}
    - Câu/đoạn kết bài CHỈ được diễn đạt lại đúng nội dung kết luận và lời kêu gọi đã trích ở trên, TUYỆT ĐỐI KHÔNG tự thêm gợi ý theo dõi tiếp theo, khuyến nghị hành động, hay bất kỳ nội dung nào không có trong bài gốc.
    - DÙ Ở ĐỊNH DẠNG NÀO: bên trong thân bài TUYỆT ĐỐI KHÔNG đánh số luận điểm kiểu "Luận điểm 1:", không dùng gạch đầu dòng, không lặp lại nguyên văn "ĐOẠN N" - các luận điểm phải được nối với nhau bằng câu văn xuôi tự nhiên, liền mạch, có tính thuyết phục, không phải bản liệt kê máy móc.
    - KHÔNG chèn bất kỳ câu/cụm chú thích nào về quá trình viết bài (không ghi "(đây là đoạn mở bài)", "(kết luận)"...). Chỉ trả về đúng nội dung bài tóm tắt, không thêm lời dẫn kiểu "Dưới đây là...".

    TRƯỚC KHI TRẢ VỀ, tự kiểm tra lại theo checklist sau, rồi mới trả lời:
    1. Đếm lại: bản tóm tắt có nhắc tới đủ TẤT CẢ luận điểm đã liệt kê ở trên không? Nếu thiếu luận điểm nào, PHẢI bổ sung trước khi trả về.
    2. Kết luận/lời kêu gọi của tác giả có được giữ đúng tinh thần không, có bị suy diễn hoặc trung lập hóa không?
    3. Với các luận điểm có ghi quan hệ (nhân quả/phản biện/bổ sung): bản tóm tắt có thể hiện rõ quan hệ đó bằng từ nối, hay đang viết như các ý rời rạc?
    4. Bản tóm tắt còn giữ được tính THUYẾT PHỤC của bài gốc không, hay đã biến thành liệt kê sự kiện khô khan (đặc biệt cần chú ý ở văn phong đơn giản hóa)?
    5. Nếu style là "khong_chuyen_mon" hoặc "binh_thuong": rà lại từng câu, liệt kê trong đầu các thuật ngữ chính trị/hành chính/pháp lý/đối ngoại xuất hiện, kiểm tra từng thuật ngữ đã có giải thích trong câu chưa.
    Chỉ trả về bản đã kiểm tra lại, không trả về bản nháp.
    """.strip()

    return prompt, day_du


# ==== BƯỚC 3b: HẬU KIỂM ĐỘ BAO PHỦ LUẬN ĐIỂM (Python-only, không gọi LLM) ====

_TU_DUNG_CHUNG_LUAN_DIEM = {
    "và", "của", "cho", "các", "là", "trong", "với", "để", "những",
    "đã", "sẽ", "này", "đó", "về", "một", "có", "không", "được",
}

SO_LAN_THU_LAI_KIEM_TRA_LUAN_DIEM = 1


def _luan_diem_nghi_thieu(summary: str, danh_sach_luan_diem: list, nguong_ty_le: float = 0.25) -> list:
    summary_lower = summary.lower()
    chi_so_nghi_thieu = []
    for i, luan_diem in enumerate(danh_sach_luan_diem, start=1):
        noi_dung = (luan_diem.get("luan_diem") or "").lower()
        tu_list = [t.strip(".,;:!?()\"'“”") for t in noi_dung.split()]
        tu_dai = [t for t in tu_list if len(t) >= 5 and t not in _TU_DUNG_CHUNG_LUAN_DIEM]
        if not tu_dai:
            continue
        so_khop = sum(1 for t in tu_dai if t in summary_lower)
        if (so_khop / len(tu_dai)) < nguong_ty_le:
            chi_so_nghi_thieu.append(i)
    return chi_so_nghi_thieu

_RE_TIEN_TO_DOAN = re.compile(r"\[ĐOẠN \d+\]\s*")


# ==== BƯỚC 3c: HẬU KIỂM THUẬT NGỮ CHƯA GIẢI THÍCH (chỉ áp dụng khi style != "chuyen_sau") ====

_RE_ACRONYM = re.compile(r"\b[A-Z]{2,6}\b")
_RE_ROMAN_NUMERAL = re.compile(r"^[IVXLCDM]+$")

_NGOAI_LE_ACRONYM = {"XII", "XIII", "XIV", "XV", "XVI"}


def _trich_tieu_de(summary: str) -> tuple:
    dong_list = summary.split("\n", 1)
    if dong_list and dong_list[0].strip().startswith("**") and dong_list[0].strip().endswith("**"):
        phan_con_lai = dong_list[1] if len(dong_list) > 1 else ""
        return dong_list[0], phan_con_lai
    return "", summary


def _thuat_ngu_chua_giai_thich(summary: str, style: str) -> list:
    if style == "chuyen_sau":
        return []

    _, than_bai = _trich_tieu_de(summary)

    ung_vien = set(_RE_ACRONYM.findall(than_bai)) - _NGOAI_LE_ACRONYM
    ung_vien = {a for a in ung_vien if not _RE_ROMAN_NUMERAL.match(a)}

    chua_giai_thich = []
    for acr in sorted(ung_vien):
        mau_1 = re.search(r"\(\s*" + re.escape(acr) + r"\s*\)", summary)
        mau_2 = re.search(r"\b" + re.escape(acr) + r"\b\s*\([^)]{3,100}\)", summary)
        if not mau_1 and not mau_2:
            chua_giai_thich.append(acr)

    return chua_giai_thich


def _lay_van_ban_cham_genre_chinh_luan(bai: dict) -> str:
    noi_dung = bai.get("noi_dung_da_danh_so", "")
    noi_dung_sach = _RE_TIEN_TO_DOAN.sub("", noi_dung)
    return f"{bai.get('title', '')} {noi_dung_sach}"


async def tom_tat_chinh_luan_cho_persona(persona: dict, bai: dict, client, semaphore,
                                         model_name: str = OSS_MODEL_NAME) -> dict:
    phan_tich = bai.get("phan_tich_lap_luan", {})
    danh_sach_luan_diem = phan_tich.get("danh_sach_luan_diem", [])
    if not danh_sach_luan_diem:
        print(f"Bài {bai.get('id')} không có phân tích lập luận hợp lệ, bỏ qua persona {persona.get('id')}.")
        return {
            "id": persona.get("id"),
            "bai_id": bai.get("id"),
            "loi": "thieu_phan_tich_lap_luan",
        }

    text_de_cham_genre = _lay_van_ban_cham_genre_chinh_luan(bai)
    genre, genre_score = classify_genre_rss(text_de_cham_genre)

    style = xac_dinh_style(persona, genre, genre_score)
    prompt, day_du = build_chinh_luan_prompt(persona, bai, style, genre)

    async def _goi(max_tokens):
        async def _call():
            return await client.models.generate_content(
                model=model_name,
                contents=prompt,
                config={"temperature": 0.0, "max_output_tokens": max_tokens},
            )

        async with semaphore:
            try:
                return await retry_generate_async(_call)
            except Exception as loi:
                print(
                    f"[DEBUG-LỖI] bài {bai.get('id')} — persona {persona.get('id')}: "
                    f"gọi LLM thất bại sau hết retry ({loi}). max_output_tokens={max_tokens}."
                )
                raise

    summary = ""
    chi_so_nghi_thieu = []
    acronym_nghi_thieu = []
    for lan_thu in range(SO_LAN_THU_LAI_KIEM_TRA_LUAN_DIEM + 1):
        so_ky_tu = len(prompt)
        so_token_uoc_luong = uoc_luong_so_token(prompt)
        print(
            f"[DEBUG] bài {bai.get('id')} — persona {persona.get('id')} (lần {lan_thu + 1}): "
            f"prompt {so_ky_tu} ký tự (~{so_token_uoc_luong} token ước lượng)"
        )

        response = await _goi(CHINH_LUAN_MAX_OUTPUT_TOKENS)
        if getattr(response, "finish_reason", None) == "length":
            print(
                f"[DEBUG] bài {bai.get('id')} — persona {persona.get('id')}: output bị cắt cụt ở "
                f"{CHINH_LUAN_MAX_OUTPUT_TOKENS} token, thử lại với "
                f"{CHINH_LUAN_MAX_OUTPUT_TOKENS_MO_RONG} token."
            )
            response = await _goi(CHINH_LUAN_MAX_OUTPUT_TOKENS_MO_RONG)

        summary = response.text.strip()
        chi_so_nghi_thieu = _luan_diem_nghi_thieu(summary, danh_sach_luan_diem)
        acronym_nghi_thieu = _thuat_ngu_chua_giai_thich(summary, style)

        if not chi_so_nghi_thieu and not acronym_nghi_thieu:
            break

        if lan_thu < SO_LAN_THU_LAI_KIEM_TRA_LUAN_DIEM:
            ghi_chu_loi = []
            if chi_so_nghi_thieu:
                ghi_chu_loi.append(
                    f"đã bỏ sót hoặc lược quá mạnh luận điểm số {chi_so_nghi_thieu} "
                    f"trong danh sách luận điểm ở trên - PHẢI bổ sung đủ"
                )
            if acronym_nghi_thieu:
                ghi_chu_loi.append(
                    f"dùng các từ viết tắt {acronym_nghi_thieu} mà KHÔNG giải thích - "
                    f"PHẢI thêm giải thích ngắn gọn (tên đầy đủ trong ngoặc) ngay khi "
                    f"từ đó xuất hiện lần đầu"
                )
            print(f"Bài {bai.get('id')} — persona {persona.get('id')}: {'; '.join(ghi_chu_loi)}, thử lại...")
            prompt += (
                f"\n\nLƯU Ý QUAN TRỌNG: bản nháp trước có dấu hiệu " + "; ".join(ghi_chu_loi) + "."
            )
        else:
            ghi_chu_loi = []
            if chi_so_nghi_thieu:
                ghi_chu_loi.append(f"luận điểm số {chi_so_nghi_thieu}")
            if acronym_nghi_thieu:
                ghi_chu_loi.append(f"từ viết tắt {acronym_nghi_thieu} chưa giải thích")
            print(f"Bài {bai.get('id')} — persona {persona.get('id')}: vẫn nghi vấn {'; '.join(ghi_chu_loi)} sau khi thử lại, cần rà thủ công.")

    return {
        "id": persona.get("id"),
        "bai_id": bai.get("id"),
        "loai_chinh_luan": bai.get("loai_chinh_luan"),
        "genre": genre,
        "genre_score": round(genre_score, 2),
        "style": style,
        "day_du": day_du,
        "summary": summary,
        "so_luan_diem": len(danh_sach_luan_diem),
        "can_soat_tay": bool(chi_so_nghi_thieu or acronym_nghi_thieu),
        "luan_diem_nghi_thieu": chi_so_nghi_thieu,
        "acronym_nghi_thieu": acronym_nghi_thieu,
    }


# ==== BƯỚC 3c: TỰ CHẠY EXTRACT + PHÂN TÍCH LẬP LUẬN (CÓ CACHE), GIỐNG PATTERN HÀNH CHÍNH ====
# Hành chính cache theo ten_file_goc (docx). Chính luận không đọc docx mà đọc
# 1 file JSON crawl RSS chứa nhiều bài, nên cache ở đây được khóa theo bai_id
# thay vì tên file - mỗi bài 1 file cache riêng trong 2 thư mục dưới đây.

EXTRACT_CACHE_DIR = "output/chinh_luan/extracted"
PHAN_TICH_CACHE_DIR = "output/chinh_luan/phan_tich_lap_luan/tung_bai"


async def lay_bai_da_phan_tich(bai_id: str, duong_dan_raw: Path, client, semaphore,
                               model_name: str = OSS_MODEL_NAME) -> dict:
    extract_cache_dir = ROOT_DIR / EXTRACT_CACHE_DIR
    phan_tich_cache_dir = ROOT_DIR / PHAN_TICH_CACHE_DIR
    extract_cache_dir.mkdir(parents=True, exist_ok=True)
    phan_tich_cache_dir.mkdir(parents=True, exist_ok=True)

    extract_cache_path = extract_cache_dir / f"{bai_id}.json"
    phan_tich_cache_path = phan_tich_cache_dir / f"{bai_id}.json"

    # Đã có cả 2 bước trong cache -> dùng luôn, không gọi lại LLM
    if phan_tich_cache_path.exists():
        with open(phan_tich_cache_path, encoding="utf-8") as f:
            bai = json.load(f)
        print(f"Đã đọc bài {bai_id} (đã phân tích lập luận) từ cache: {phan_tich_cache_path}")
        return bai

    # Bước 1: extract - cache riêng để đổi persona khác cho CÙNG bài
    # không phải tách đoạn lại từ file crawl thô
    if extract_cache_path.exists():
        with open(extract_cache_path, encoding="utf-8") as f:
            ket_qua_extract = json.load(f)
        print(f"Đã đọc bài {bai_id} (đã tách đoạn) từ cache: {extract_cache_path}")
    else:
        if not duong_dan_raw.exists():
            raise SystemExit(
                f"Không tìm thấy bài {bai_id} trong cache và cũng không tìm thấy "
                f"file crawl gốc: {duong_dan_raw}"
            )
        with open(duong_dan_raw, encoding="utf-8") as f:
            danh_sach_bai_goc = json.load(f)
        bai_goc = next((b for b in danh_sach_bai_goc if b.get("id") == bai_id), None)
        if bai_goc is None:
            raise SystemExit(f"Không tìm thấy bài có id = {bai_id} trong {duong_dan_raw}")

        print(f"Đang tách đoạn cho bài {bai_id}...")
        ket_qua_extract = xu_ly_mot_bai(bai_goc)
        with open(extract_cache_path, "w", encoding="utf-8") as f:
            json.dump(ket_qua_extract, f, ensure_ascii=False, indent=2)

    # Bước 2: phân tích lập luận - có gọi LLM nên cache lại riêng, tách biệt
    # với bước extract để không phải gọi lại LLM khi đổi persona khác
    print(f"Đang phân tích cấu trúc lập luận cho bài {bai_id}...")
    phan_tich = await goi_llm_phan_tich_async(client, semaphore, ket_qua_extract, model=model_name)
    bai = dict(ket_qua_extract)
    bai["phan_tich_lap_luan"] = phan_tich
    with open(phan_tich_cache_path, "w", encoding="utf-8") as f:
        json.dump(bai, f, ensure_ascii=False, indent=2)

    return bai


# ==== BƯỚC 5: CLI ====

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tóm tắt chính luận cá nhân hóa cho 1 persona")
    parser.add_argument(
        "--input", default=DUONG_DAN_INPUT_MAC_DINH,
        help="Đường dẫn file JSON chính luận đã phân tích lập luận SẴN CÓ (nếu bạn đã tự "
             "chạy chinh_luan_extract.py + chinh_luan_phan_tich_lap_luan.py trước và có "
             "1 file gộp nhiều bài). Nếu bài cần chạy KHÔNG có trong file này, script sẽ "
             "tự tách đoạn + phân tích lập luận cho bài đó từ --raw-input."
    )
    parser.add_argument(
        "--raw-input", default=DUONG_DAN_RAW_MAC_DINH,
        help="Đường dẫn file JSON crawl RSS thô (chưa qua xử lý gì), dùng khi bài "
             "cần chạy chưa có trong --input hoặc chưa có trong cache."
    )
    parser.add_argument("--output-dir", default=DUONG_DAN_OUTPUT_MAC_DINH)
    parser.add_argument("--bai-id", required=True, help="id bài chính luận, ví dụ CL0002")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--id", help="id của persona, ví dụ NN001")
    group.add_argument("--so-luong", type=int, help="chạy từ persona đầu tiên đến persona thứ n")
    group.add_argument("--tu-id", help="chạy từ persona này (vd NN0001), dùng kèm --den-id")
    parser.add_argument("--den-id", help="id persona kết thúc, dùng kèm --tu-id (vd NN0050)")
    parser.add_argument("--model", default=OSS_MODEL_NAME)
    parser.add_argument(
        "--variant",
        type=str,
        default=None,
        help="tên biến thể persona, nếu có sẽ ghi vào thư mục con riêng để tránh đè lên dữ liệu persona đầy đủ trường"
    )
    args = parser.parse_args()

    if args.den_id and not args.tu_id:
        parser.error("--den-id phải đi kèm --tu-id")


    async def xu_ly_mot_persona(client, semaphore, out_dir, persona, bai, model, i, tong):
        out_path_json = out_dir / f"{persona['id']}.json"
        out_path_md = out_dir / f"{persona['id']}.md"

        if out_path_json.exists():
            print(f"[{i}/{tong}] {persona['id']} đã tồn tại -> bỏ qua")
            return

        print(f"\n[{i}/{tong}] Bắt đầu xử lý {persona['id']}...")
        ket_qua = await tom_tat_chinh_luan_cho_persona(persona, bai, client, semaphore, model_name=model)

        with open(out_path_json, "w", encoding="utf-8") as f:
            json.dump(ket_qua, f, ensure_ascii=False, indent=2)
        with open(out_path_md, "w", encoding="utf-8") as f:
            f.write(ket_qua["summary"])

        dinh_dang = "đầy đủ (tiêu đề + mở-thân-kết)" if ket_qua["day_du"] else "vào thẳng vấn đề"
        print(
            f"Genre: {ket_qua['genre']} ({ket_qua['genre_score']}) — Style: {ket_qua['style']} — Định dạng: {dinh_dang}")
        print(f"Số luận điểm: {ket_qua['so_luan_diem']}")
        print(f"Đã ghi: {out_path_json}")


    async def chay():
        client = tao_oss_client_async()
        semaphore = asyncio.Semaphore(OSS_MAX_CONCURRENCY_SUMMARY)

        bai = None
        thu_muc_input = ROOT_DIR / args.input if not Path(args.input).is_absolute() else Path(args.input)
        duong_dan_input = thu_muc_input / f"{args.bai_id}.json"
        if duong_dan_input.exists():
            with open(duong_dan_input, encoding="utf-8") as f:
                bai = json.load(f)
        else:
            print(f"[CẢNH BÁO] Không tìm thấy file bài viết: {duong_dan_input}")

        if bai is None:
            duong_dan_raw = ROOT_DIR / args.raw_input if not Path(args.raw_input).is_absolute() else Path(
                args.raw_input)
            bai = await lay_bai_da_phan_tich(args.bai_id, duong_dan_raw, client, semaphore, model_name=args.model)

        ten_file_persona = f"state_profiles_{args.variant}.json" if args.variant else "state_profiles_nt_nn_tc_kn_cd_ch.json"
        duong_dan_persona = ROOT_DIR / "data" / "profile_variants" / ten_file_persona
        with open(duong_dan_persona, encoding="utf-8") as f:
            personas = json.load(f)

        if args.id:
            personas_can_chay = [p for p in personas if p.get("id") == args.id]
            if not personas_can_chay:
                raise SystemExit(f"Không tìm thấy persona có id = {args.id} trong {PROFILE_PATH}")
        elif args.tu_id:
            so_tu = int(re.sub(r"\D", "", args.tu_id))
            so_den = int(re.sub(r"\D", "", args.den_id)) if args.den_id else so_tu
            personas_can_chay = [
                p for p in personas
                if so_tu <= int(re.sub(r"\D", "", p.get("id", "0"))) <= so_den
            ]
            if not personas_can_chay:
                raise SystemExit(f"Không tìm thấy persona nào trong khoảng {args.tu_id} - {args.den_id or args.tu_id}")
        else:
            personas_can_chay = personas[:args.so_luong]

        thanh_phan_dir = [ROOT_DIR, args.output_dir]
        if args.variant:
            thanh_phan_dir.append(args.variant)
        thanh_phan_dir.append(args.bai_id)
        out_dir = Path(*thanh_phan_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        tong = len(personas_can_chay)
        tasks = [
            xu_ly_mot_persona(client, semaphore, out_dir, persona, bai, args.model, i, tong)
            for i, persona in enumerate(personas_can_chay, start=1)
        ]
        await asyncio.gather(*tasks)

    asyncio.run(chay())