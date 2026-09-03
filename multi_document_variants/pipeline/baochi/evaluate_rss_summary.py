""" Cách chạy:
python3 -m pipeline.baochi.evaluate_rss_summary --variant nt_nn_tc_kn_cd_ch
"""

import json
import time
import re
import hashlib
import asyncio
from pathlib import Path
from pipeline.utils import (
    retry_generate_async, OSS_MODEL_NAME, tao_oss_client_async,
    OSS_MAX_CONCURRENCY_SUMMARY,
)
from pipeline.baochi.rss_personalize import BANNED_PHRASES
ROOT_DIR = Path(__file__).resolve().parents[3]
MD_ROOT = ROOT_DIR / "multi_document_variants"
SHARED_ROOT = ROOT_DIR / "shared"

DATA_DIR = MD_ROOT / "data" / "bao_chi"
OUTPUT_DIR = MD_ROOT / "output" / "bao_chi" / "rss_summary"
JSON_DIR = OUTPUT_DIR / "json"
EVAL_DIR = OUTPUT_DIR / "eval"
TOM_TAT_BAI_DIR = MD_ROOT / "output" / "bao_chi" / "rss_tom_tat_bai"

PERSONAS_PATH = MD_ROOT / "data" / "profile_variants" / "state_profiles_nt_nn_tc_kn_cd_ch.json"
ARTICLES_PATH = DATA_DIR / "vnexpress_rss_snapshot_3007.json"

# 2 tiêu chí BẮT BUỘC đối chiếu với văn bản nguồn — chấm riêng theo TỪNG BATCH (đúng ranh giới
# batch mà rss_personalize.py đã dùng để viết, dữ liệu lấy từ field "than_bai_theo_batch"), để
# tránh nhồi nguồn của TOÀN BỘ persona (có thể 50-60 tin) vào 1 request duy nhất — chính là
# nguyên nhân gây lỗi 500/timeout trước đây.
TIEU_CHI_CAN_NGUON = ["chon_loc_phu_hop", "nhat_quan"]

# 4 tiêu chí còn lại KHÔNG cần đối chiếu văn bản nguồn từng tin — chỉ cần bản tóm tắt cuối cùng
# (vốn đã ngắn, không phình theo số lượng tin) — chấm 1 lần duy nhất, nhẹ, an toàn.
TIEU_CHI_HINH_THUC = ["trinh_bay_phu_hop", "bo_cuc_uu_tien", "giong_dieu_phu_hop", "thai_do_dung_dan"]

TIEU_CHI = TIEU_CHI_CAN_NGUON + TIEU_CHI_HINH_THUC  # giữ đúng thứ tự cũ để dễ so sánh kết quả

NGUON_JUDGE_MAX_TOKENS = 2048
HINH_THUC_JUDGE_MAX_TOKENS = 3072
NGUONG_TI_LE_PASS_BATCH = 0.8

def load_personas(variant=None):
    ten_file = f"state_profiles_{variant}.json" if variant else "state_profiles_nt_nn_tc_kn_cd_ch.json"
    duong_dan = MD_ROOT / "data" / "profile_variants" / ten_file
    with open(duong_dan, encoding="utf-8") as f:
        return json.load(f)


def load_articles_index():
    with open(ARTICLES_PATH, encoding="utf-8") as f:
        articles = json.load(f)
    index_theo_link = {a.get("link"): a for a in articles if a.get("link")}
    index_theo_title = {a.get("title"): a for a in articles if a.get("title")}
    return index_theo_link, index_theo_title


def _doc_tom_tat_bai(link: str) -> str:
    """Đọc lại bản tóm tắt tầng 1 (đã cache sẵn khi rss_personalize.py chạy, cache theo link,
    hoàn toàn miễn phí - không tốn thêm lượt gọi LLM nào). Đây CHÍNH XÁC là nội dung nguồn mà
    LLM viết bài đã nhìn thấy (không phải văn bản gốc đầy đủ) - nên evaluate cũng dùng lại đúng
    bản này để chấm cho công bằng, thay vì đối chiếu với nội dung LLM chưa từng thấy."""
    if not link:
        return "(không có link)"
    key = hashlib.md5(link.encode("utf-8")).hexdigest()[:16]
    duong_dan = TOM_TAT_BAI_DIR / f"{key}.json"
    if not duong_dan.exists():
        return "(không tìm thấy bản tóm tắt tầng 1 trong cache - có thể cache đã bị xoá)"
    with open(duong_dan, encoding="utf-8") as f:
        return json.load(f).get("tom_tat", "")


def lay_noi_dung_nguon_C(tin_links: list) -> list:
    """Nguồn cho nhóm tin CHÍNH (C) - dùng bản tầng 1 cô đọng (đúng cái LLM viết bài đã thấy)."""
    ket_qua = []
    for link in tin_links:
        ket_qua.append({"link": link, "noi_dung": _doc_tom_tat_bai(link)})
    return ket_qua


def lay_noi_dung_nguon_GB(items: list, index_theo_link: dict, index_theo_title: dict) -> tuple:
    """Nguồn cho nhóm tin gián tiếp (G) / bài góc nhìn (B) - dùng field "summary" (RSS gốc), vì
    đây đúng là nội dung LLM viết bài đã thấy cho 2 nhóm này (dung_full_content=False khi build
    prompt ở rss_personalize.py), KHÔNG dùng content đầy đủ."""
    ket_qua = []
    so_khong_tim_thay = 0
    for item in items:
        goc = index_theo_link.get(item.get("link")) or index_theo_title.get(item.get("title"))
        if goc:
            ket_qua.append({
                "title": goc.get("title", ""),
                "noi_dung": goc.get("summary", ""),
                "genre": item.get("genre", "Góc nhìn"),
            })
        else:
            so_khong_tim_thay += 1
            ket_qua.append({
                "title": item.get("title", ""),
                "noi_dung": "(không tìm thấy nội dung gốc - chỉ còn tiêu đề)",
                "genre": item.get("genre", "Góc nhìn"),
            })
    return ket_qua, so_khong_tim_thay


def _format_nguon(nguon_list: list, nhan: str, prefix: str) -> str:
    if not nguon_list:
        return f"{nhan}: (không có)"
    dong = [f"{nhan}:"]
    for i, n in enumerate(nguon_list, 1):
        tieu_de = n.get("title", "")
        the_loai = f"[{n['genre']}] " if n.get("genre") else ""
        dong.append(f"{prefix}{i}. {the_loai}{tieu_de}\n{n['noi_dung']}")
    return "\n".join(dong)


def _chuan_hoa(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip().lower()


def _trich_cac_doan_trich_dan(text: str) -> list:
    """Tìm tất cả cụm được đặt trong dấu ngoặc kép (kiểu " " hoặc " ") trong ly_do."""
    ket_qua = []
    ket_qua.extend(re.findall(r'"([^"]{5,})"', text))
    ket_qua.extend(re.findall(r'\u201c([^\u201d]{5,})\u201d', text))
    return ket_qua


def hau_kiem_fail_reasons_batch(nhan_batch: str, cham: dict, batch_text: str,
                                 nguon_c: list, nguon_g: list, nguon_b: list) -> dict:
    canh_bao = []
    tc_bi_bia = set()  # tiêu chí mà TOÀN BỘ bằng chứng trích dẫn của fail đều bịa/suy diễn
    batch_text_chuan = _chuan_hoa(batch_text)
    nguon_text_chuan = _chuan_hoa(
        " ".join(n.get("noi_dung", "") for n in nguon_c)
        + " " + " ".join((n.get("noi_dung", "") + " " + n.get("title", "")) for n in nguon_g + nguon_b)
    )
    van_ban_chuan_gop = batch_text_chuan + " " + nguon_text_chuan
    so_c, so_g, so_b = len(nguon_c), len(nguon_g), len(nguon_b)

    for tc, ket in cham.items():
        if not isinstance(ket, dict) or ket.get("verdict") != "fail":
            continue
        ly_do = ket.get("ly_do", "")
        cac_trich_dan = _trich_cac_doan_trich_dan(ly_do)
        so_trich_bia = 0

        for tien_to, so_str in re.findall(r"\b([CGB])(\d+)\b", ly_do):
            so = int(so_str)
            if tien_to == "C" and so > so_c:
                canh_bao.append(f"[{nhan_batch}/{tc}] trích mã C{so} không tồn tại (batch này chỉ có {so_c} tin).")
            if tien_to == "G" and so > so_g:
                canh_bao.append(f"[{nhan_batch}/{tc}] trích mã G{so} không tồn tại (nhóm gián tiếp chỉ có {so_g} tin).")
            if tien_to == "B" and so > so_b:
                canh_bao.append(f"[{nhan_batch}/{tc}] trích mã B{so} không tồn tại (nhóm góc nhìn chỉ có {so_b} bài).")

        for trich in cac_trich_dan:
            if _chuan_hoa(trich) not in van_ban_chuan_gop:
                so_trich_bia += 1
                canh_bao.append(
                    f"[{nhan_batch}/{tc}] trích dẫn \"{trich[:60]}...\" KHÔNG có trong CẢ đoạn "
                    f"thân bài lẫn văn bản nguồn của batch này - có khả năng judge bịa nội dung."
                )

        co_claim_bo_sot = any(tu in ly_do.lower() for tu in ["bỏ sót", "bỏ qua", "thiếu nội dung", "không đề cập"])
        if co_claim_bo_sot:
            if not cac_trich_dan:
                canh_bao.append(
                    f"[{nhan_batch}/{tc}] verdict fail với lý do bỏ sót/thiếu nhưng KHÔNG trích dẫn bằng "
                    f"chứng cụ thể nào - có khả năng judge hallucinate, cần soát tay."
                )
            for trich in cac_trich_dan:
                trich_chuan = _chuan_hoa(trich)
                if trich_chuan and trich_chuan not in nguon_text_chuan:
                    so_trich_bia += 1
                    canh_bao.append(
                        f"[{nhan_batch}/{tc}] cho rằng bản tóm tắt bỏ sót \"{trich[:60]}...\" nhưng nội dung "
                        f"này KHÔNG tìm thấy trong văn bản nguồn của batch - có khả năng judge suy diễn."
                    )

        if cac_trich_dan and so_trich_bia >= len(cac_trich_dan):
            tc_bi_bia.add(tc)

    return {"can_soat_tay": bool(canh_bao), "chi_tiet_canh_bao": canh_bao, "tc_bi_bia": tc_bi_bia}

def hau_kiem_cum_tu_cam(summary: str) -> list:
    text_lower = summary.lower()
    return [p for p in BANNED_PHRASES if p.lower() in text_lower]

def build_judge_prompt_nguon(persona: dict, nguon_c: list, nguon_g: list, nguon_b: list,
                              batch_text: str, nhom_ten: str) -> str:
    ho_so = f"""
Vai trò: {persona.get('kinh_nghiem', '')}
Đơn vị công tác: {persona.get('to_chuc', '')}
Ngành: {persona.get('nganh_to', '')} - {persona.get('nganh_nho', '')}
Chủ đề quan tâm (ưu tiên từ cao xuống thấp): {', '.join(persona.get('chu_de', []))}
Khuynh hướng/mối quan tâm trước mắt: {persona.get('cau_hoi_truoc_mat', '')}
Mô tả chung: {persona.get('mo_ta_chung', '')}
""".strip()

    nguon_text = (
        _format_nguon(nguon_c, f"VĂN BẢN NGUỒN - nhóm tin chính thuộc chủ đề \"{nhom_ten}\" (phần đang chấm)", "C")
        + "\n\n"
        + _format_nguon(nguon_g, "VĂN BẢN NGUỒN - nhóm tin liên quan gián tiếp (toàn bộ persona)", "G")
        + "\n\n"
        + _format_nguon(nguon_b, "VĂN BẢN NGUỒN - nhóm bài góc nhìn/phân tích liên quan (toàn bộ persona)", "B")
    )

    prompt = f"""
Bạn là giám khảo đánh giá MỘT PHẦN của bản tóm tắt tin tức cá nhân hóa theo persona công chức/nhà
nước. Đây KHÔNG phải toàn bộ bản tóm tắt — chỉ là phần thân bài ứng với nhóm chủ đề "{nhom_ten}",
được viết riêng cho đúng {len(nguon_c)} tin nguồn dưới đây. Nhóm tin gián tiếp (G) và bài góc nhìn
(B) là của TOÀN BỘ persona (dùng chung cho mọi phần), chỉ đưa vào đây để bạn có đủ ngữ cảnh kiểm
tra, KHÔNG bắt buộc phải xuất hiện trong đoạn văn đang chấm.

HỒ SƠ PERSONA:
{ho_so}

{nguon_text}

LƯU Ý VỀ ĐÁNH SỐ: mã C1, C2... trong lượt chấm này CHỈ đánh số cục bộ cho {len(nguon_c)} tin
thuộc phần đang chấm — KHÔNG liên quan tới số thứ tự tin ở các phần khác của cùng persona (được
chấm ở lượt riêng). Mã G/B đánh số cho toàn bộ persona như bình thường.

ĐOẠN THÂN BÀI CẦN CHẤM (đúng phần ứng với {len(nguon_c)} tin nguồn C ở trên):
{batch_text}

BƯỚC BẮT BUỘC TRƯỚC KHI CHẤM (chỉ để bạn tự suy luận, KHÔNG in ra kết quả): với MỖI tin C1,
C2... ở trên, xác định nó được phản ánh ở đâu trong đoạn thân bài. Nếu 2 tin C.. cùng nằm chung
1 đoạn văn (không tách dòng trống), đó là gộp — chỉ hợp lệ nếu 2 tin đó THẬT SỰ cùng nói về MỘT
SỰ KIỆN CỤ THỂ (trùng tên riêng/đơn vị/địa điểm, trùng mốc thời gian, trùng hành động/quyết
định); nếu là hai sự kiện khác nhau bị gộp chung, hoặc một tin bị bỏ hẳn không xuất hiện, đó là
lỗi thật — kết luận fail cho chon_loc_phu_hop, trích rõ mã C liên quan.

Chấm phần thân bài này theo đúng 2 tiêu chí sau, mỗi tiêu chí trả về "pass" hoặc "fail" kèm lý do
ngắn gọn (tối đa 2 câu, tiếng Việt có dấu):

1. chon_loc_phu_hop: Đoạn thân bài này có ưu tiên chọn chi tiết/dữ kiện liên quan trực tiếp đến
   chu_de và khuynh hướng quan tâm của persona không, có bỏ sót chi tiết quan trọng đúng chuyên
   môn không, có giữ nhiều chi tiết không liên quan không. Với các đoạn gộp 2 tin C.. cùng sự
   kiện: áp dụng đúng quy tắc xác nhận trùng sự kiện ở trên, không tự động coi gộp là lỗi.
2. nhat_quan: Mọi thông tin trong đoạn thân bài này có đúng với văn bản nguồn C.. không (không
   bịa thêm số liệu/sự kiện), các câu có mâu thuẫn nhau không, có gán cho persona đặc điểm/quan
   điểm không có trong hồ sơ không.

Với MỖI tiêu chí (cả pass lẫn fail), ly_do PHẢI nêu ít nhất 1 ví dụ cụ thể, dùng mã C../G../B..
khi trích dẫn tin nguồn. QUY TẮC TRÍCH DẪN BẮT BUỘC: mọi ly_do khẳng định "fail" PHẢI trích một
cụm từ/câu NGẮN thực sự có trong đoạn thân bài ở trên làm bằng chứng, đặt trong dấu ngoặc kép.
Nếu không thể trích dẫn cụ thể như vậy, KHÔNG được kết luận "fail" - chuyển sang "pass".

QUY TẮC CHỐNG SUY DIỄN NGUỒN KHÔNG TỒN TẠI: nếu ly_do phê bình "bỏ sót" một nội dung nào đó, BẮT
BUỘC phải chỉ ra đúng mã C../G../B.. trong danh sách nguồn ở trên có chứa đúng nội dung đó. Nếu
rà soát toàn bộ mà không tìm thấy, đây là suy diễn sai - TUYỆT ĐỐI không dùng làm lý do fail.

QUY TẮC MẶC ĐỊNH KHI CHẤM: đánh giá công bằng, không cần khắt khe với các khác biệt rất nhỏ hoặc
không ảnh hưởng đáng kể tới độ chính xác/mức độ phù hợp của nội dung. Chỉ kết luận "fail" khi có
bằng chứng RÕ RÀNG, CỤ THỂ về vi phạm (đúng như quy tắc trích dẫn bắt buộc ở trên); nếu chỉ là
cảm nhận chủ quan hoặc sự khác biệt không đáng kể, chọn "pass".

CHỈ trả về một đối tượng JSON đúng định dạng sau, không thêm lời dẫn, không dùng markdown, CHỈ 2
khóa, mỗi khóa là MỘT OBJECT có ĐÚNG 2 trường "verdict" và "ly_do":
{{
  "chon_loc_phu_hop": {{"verdict": "pass hoặc fail", "ly_do": "..."}},
  "nhat_quan": {{"verdict": "pass hoặc fail", "ly_do": "..."}}
}}
""".strip()

    return prompt


def build_judge_prompt_hinh_thuc(persona: dict, summary: str, ten_cac_nhom: list, day_du: bool) -> str:
    ho_so = f"""
Vai trò: {persona.get('kinh_nghiem', '')}
Đơn vị công tác: {persona.get('to_chuc', '')}
Ngành: {persona.get('nganh_to', '')} - {persona.get('nganh_nho', '')}
Chủ đề quan tâm (ưu tiên từ cao xuống thấp): {', '.join(persona.get('chu_de', []))}
Khuynh hướng/mối quan tâm trước mắt: {persona.get('cau_hoi_truoc_mat', '')}
Mô tả chung: {persona.get('mo_ta_chung', '')}
""".strip()

    thu_tu_nhom = " -> ".join(ten_cac_nhom) if ten_cac_nhom else "(không có nhóm nào)"

    cau_truc_ghi_chu = f"""
CẤU TRÚC CỐ ĐỊNH của bản tóm tắt (để bạn xác định đúng vai trò từng đoạn trước khi chấm, KHÔNG
in ra): {"1) tiêu đề  2) mở bài  " if day_du else "(không có tiêu đề/mở bài riêng - đoạn đầu tiên có dòng dẫn ngắn kiểu 'Về [chủ đề]:')  "}
3) thân bài theo các nhóm chủ đề theo đúng thứ tự ưu tiên: {thu_tu_nhom}  4) đoạn tin gián tiếp
(nếu có, thường mở đầu "Các tin khác đáng chú ý:")  5) đoạn bài góc nhìn liên quan (nếu có, đoạn
đầu mở đầu "Góc nhìn liên quan:")  6) đoạn kết luận - LUÔN LÀ ĐOẠN CUỐI CÙNG THẬT SỰ của toàn bộ
bản tóm tắt (đứng sau cả tin gián tiếp và bài góc nhìn nếu chúng tồn tại). TUYỆT ĐỐI không nhầm
đoạn kết luận với đoạn cuối của nhóm góc nhìn - đối chiếu nội dung: kết luận tổng kết TOÀN BÀI,
đoạn góc nhìn chỉ tóm tắt MỘT bài phân tích bên ngoài cụ thể.
""".strip()

    prompt = f"""
Bạn là giám khảo đánh giá HÌNH THỨC TRÌNH BÀY của một bản tóm tắt tin tức cá nhân hóa theo persona
công chức/nhà nước (KHÔNG cần đối chiếu với văn bản nguồn gốc từng tin ở bước này - việc đó đã
được chấm riêng ở bước khác).

HỒ SƠ PERSONA:
{ho_so}

{cau_truc_ghi_chu}

BẢN TÓM TẮT CẦN CHẤM (toàn văn):
{summary}

Chấm bản tóm tắt trên theo đúng 4 tiêu chí sau, mỗi tiêu chí trả về "pass" hoặc "fail" kèm lý do
ngắn gọn (tối đa 2 câu, tiếng Việt có dấu), PHẢI trích 1 cụm/câu NGẮN thực sự có trong bản tóm
tắt làm bằng chứng khi kết luận "fail":

1. trinh_bay_phu_hop: Nếu persona có chuyên môn đúng chủ đề nhóm ưu tiên cao nhất thì có dùng
   thuật ngữ/bố cục kiểu chuyên gia không, nếu không đúng chuyên môn thì có trình bày ở mức phổ
   thông, không lạm dụng thuật ngữ chuyên ngành không cần thiết không; câu văn có rõ ràng mạch
   lạc, không lặp ý không.
2. bo_cuc_uu_tien: Nội dung liên quan nhất với persona có được đặt lên đầu/nổi bật không (đúng
   thứ tự nhóm chủ đề: {thu_tu_nhom}), nội dung phụ (tin gián tiếp, bài góc nhìn) có được đẩy
   xuống cuối không. Nếu có từ 2 nhóm chủ đề trở lên, xác nhận MỖI lần chuyển nhóm đều có câu dẫn
   báo hiệu (không chỉ lần đầu) - thiếu bất kỳ lần nào thì mặc định "fail".
3. giong_dieu_phu_hop: Giọng điệu có phù hợp với vị trí công tác và mục đích tham mưu/theo dõi
   chuyên ngành của persona không, có quá suồng sã hoặc quá hoa mỹ không cần thiết không; bản tóm
   tắt có GIỮ ĐÚNG tính chất định hướng/khuynh hướng mối quan tâm của persona mà KHÔNG biến thành
   câu hỏi trực tiếp hay lời khuyên/kêu gọi hành động lộ liễu không.
4. thai_do_dung_dan: Bản tóm tắt có giữ thái độ khách quan trung lập không, có câu phán xét/
   thiên vị/suy diễn động cơ không, có tôn trọng đúng mực vai trò persona không.

QUY TẮC MẶC ĐỊNH KHI CHẤM: đánh giá công bằng, không cần khắt khe với các khác biệt rất nhỏ hoặc
không ảnh hưởng đáng kể tới trải nghiệm đọc. Chỉ kết luận "fail" khi trích dẫn được cụ thể câu/cụm
từ trong bản tóm tắt cho thấy rõ vi phạm; nếu chỉ là cảm nhận chủ quan, chọn "pass".

CHỈ trả về một đối tượng JSON đúng định dạng sau, không thêm lời dẫn, không dùng markdown, CHỈ 4
khóa, mỗi khóa là MỘT OBJECT có ĐÚNG 2 trường "verdict" và "ly_do":
{{
  "trinh_bay_phu_hop": {{"verdict": "pass hoặc fail", "ly_do": "..."}},
  "bo_cuc_uu_tien": {{"verdict": "pass hoặc fail", "ly_do": "..."}},
  "giong_dieu_phu_hop": {{"verdict": "pass hoặc fail", "ly_do": "..."}},
  "thai_do_dung_dan": {{"verdict": "pass hoặc fail", "ly_do": "..."}}
}}
""".strip()

    return prompt


async def _goi_judge(prompt: str, max_tokens: int, client, semaphore, model_name: str) -> dict:
    """Gọi LLM judge, parse JSON, trả về dict {"loi": None, "cham": {...}} hoặc {"loi": "...", "raw": "..."}."""
    async def _call():
        return await client.models.generate_content(
            model=model_name,
            contents=prompt,
            config={
                "temperature": 0.0,
                "max_output_tokens": max_tokens,
                "response_mime_type": "application/json",
            },
        )

    async with semaphore:
        response = await retry_generate_async(_call)

    raw = response.text.strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        return {"loi": None, "cham": json.loads(raw)}
    except json.JSONDecodeError:
        return {"loi": "LỖI: không parse được JSON từ judge.", "raw": raw}


async def cham_1_batch_nguon(persona: dict, batch: dict, nguon_g: list, nguon_b: list,
                              client, semaphore, model_name: str = OSS_MODEL_NAME) -> dict:
    """Chấm chon_loc_phu_hop + nhat_quan cho ĐÚNG 1 batch trong than_bai_theo_batch."""
    nhom_ten = batch.get("nhom_chu_de", "")
    tin_links = batch.get("tin_links", [])
    batch_text = batch.get("text", "")
    nguon_c = lay_noi_dung_nguon_C(tin_links)

    prompt = build_judge_prompt_nguon(persona, nguon_c, nguon_g, nguon_b, batch_text, nhom_ten)
    ket_goi = await _goi_judge(prompt, NGUON_JUDGE_MAX_TOKENS, client, semaphore, model_name)

    nhan_batch = f"{nhom_ten} ({len(tin_links)} tin)"
    if ket_goi["loi"]:
        return {
            "nhan_batch": nhan_batch,
            "loi": ket_goi["loi"],
            "raw_response": ket_goi["raw"],
        }

    cham = ket_goi["cham"]
    loi_dinh_dang = []
    for tc in TIEU_CHI_CAN_NGUON:
        gt = cham.get(tc)
        if not isinstance(gt, dict) or "verdict" not in gt:
            loi_dinh_dang.append(tc)
            cham[tc] = {
                "verdict": "fail",
                "ly_do": "LỖI ĐỊNH DẠNG: judge trả về sai cấu trúc cho tiêu chí này, mặc định fail.",
            }

    hau_kiem = hau_kiem_fail_reasons_batch(nhan_batch, cham, batch_text, nguon_c, nguon_g, nguon_b)

    for tc in hau_kiem["tc_bi_bia"]:
        ly_do_goc = cham[tc].get("ly_do", "")
        cham[tc]["verdict"] = "pass"
        cham[tc]["ly_do"] = (
            f"[TỰ ĐỘNG LẬT VERDICT] Judge kết luận fail nhưng toàn bộ trích dẫn làm bằng chứng đều "
            f"không có trong nguồn/thân bài (bịa hoặc suy diễn) - coi như không có căn cứ hợp lệ, "
            f"chuyển sang pass. Lý do gốc của judge: {ly_do_goc}"
        )

    return {
        "nhan_batch": nhan_batch,
        "loi": None,
        "cham": cham,
        "loi_dinh_dang": loi_dinh_dang,
        "hau_kiem_canh_bao": hau_kiem["chi_tiet_canh_bao"] if hau_kiem["can_soat_tay"] else [],
    }

async def cham_hinh_thuc(persona: dict, summary: str, ten_cac_nhom: list, day_du: bool,
                          client, semaphore, model_name: str = OSS_MODEL_NAME) -> dict:
    prompt = build_judge_prompt_hinh_thuc(persona, summary, ten_cac_nhom, day_du)
    ket_goi = await _goi_judge(prompt, HINH_THUC_JUDGE_MAX_TOKENS, client, semaphore, model_name)

    if ket_goi["loi"]:
        return {"loi": ket_goi["loi"], "raw_response": ket_goi["raw"]}

    cham = ket_goi["cham"]
    loi_dinh_dang = []
    for tc in TIEU_CHI_HINH_THUC:
        gt = cham.get(tc)
        if not isinstance(gt, dict) or "verdict" not in gt:
            loi_dinh_dang.append(tc)
            cham[tc] = {
                "verdict": "fail",
                "ly_do": "LỖI ĐỊNH DẠNG: judge trả về sai cấu trúc cho tiêu chí này, mặc định fail.",
            }

    cum_cam_con_sot = hau_kiem_cum_tu_cam(summary)
    if cum_cam_con_sot:
        ly_do_judge_goc = cham.get("trinh_bay_phu_hop", {}).get("ly_do", "")
        cham["trinh_bay_phu_hop"] = {
            "verdict": "fail",
            "ly_do": (
                f"[HẬU KIỂM TỰ ĐỘNG - GHI ĐÈ] Phát hiện cụm từ bị cấm còn sót trong bản tóm tắt: "
                f"{', '.join(repr(c) for c in cum_cam_con_sot)}. Lý do judge gốc (nếu có): {ly_do_judge_goc}"
            ),
        }

    return {"loi": None, "cham": cham, "loi_dinh_dang": loi_dinh_dang}


async def cham_1_persona(persona: dict, ket_qua_rss: dict, index_theo_link: dict, index_theo_title: dict,
                          client, semaphore, model_name: str = OSS_MODEL_NAME) -> dict:
    summary = ket_qua_rss.get("summary", "")
    if not summary:
        return {
            "id": persona.get("id"),
            "note": "Bỏ qua đánh giá - bản tóm tắt rỗng (không có tin khớp chu_de).",
        }

    cac_batch = ket_qua_rss.get("than_bai_theo_batch")
    if not cac_batch:
        return {
            "id": persona.get("id"),
            "note": (
                "Bỏ qua đánh giá - kết quả rss_personalize này KHÔNG có field 'than_bai_theo_batch' "
                "(có thể được sinh bằng bản rss_personalize.py cũ hơn bản đang dùng) - cần chạy lại "
                "rss_personalize cho persona này trước khi đánh giá."
            ),
        }

    nguon_g, thieu_g = lay_noi_dung_nguon_GB(
        ket_qua_rss.get("tin_gian_tiep", []), index_theo_link, index_theo_title
    )
    nguon_b, thieu_b = lay_noi_dung_nguon_GB(
        ket_qua_rss.get("bai_lien_quan", []), index_theo_link, index_theo_title
    )

    # --- Chấm chon_loc_phu_hop + nhat_quan theo TỪNG batch, song song ---
    ket_qua_batch = await asyncio.gather(*[
        cham_1_batch_nguon(persona, batch, nguon_g, nguon_b, client, semaphore, model_name)
        for batch in cac_batch
    ])

    # --- Chấm 4 tiêu chí hình thức, 1 lần ---
    so_bai_moi_nhom = ket_qua_rss.get("so_bai_moi_nhom", [])
    ten_cac_nhom = [n.get("chu_de", "") for n in so_bai_moi_nhom]
    day_du = ket_qua_rss.get("day_du")
    if day_du is None:
        day_du = summary.strip().split("\n\n")[0].strip().lower().startswith("về ") is False
    ket_qua_hinh_thuc = await cham_hinh_thuc(persona, summary, ten_cac_nhom, day_du, client, semaphore, model_name)

    cham_tong = {}
    canh_bao_loi_dinh_dang = []
    canh_bao_thieu_batch = []
    hau_kiem_tong = []

    for tc in TIEU_CHI_CAN_NGUON:
        cac_verdict = []
        cac_ly_do_fail = []
        for kb in ket_qua_batch:
            if kb.get("loi"):
                canh_bao_thieu_batch.append(f"[{kb.get('nhan_batch', '?')}] {kb['loi']}")
                continue
            v = kb["cham"].get(tc, {}).get("verdict", "fail")
            cac_verdict.append(v)
            if v == "fail":
                cac_ly_do_fail.append(f"[{kb['nhan_batch']}] {kb['cham'][tc].get('ly_do', '')}")
            if kb.get("loi_dinh_dang") and tc in kb["loi_dinh_dang"]:
                canh_bao_loi_dinh_dang.append(f"{tc} (batch {kb['nhan_batch']})")
            hau_kiem_tong.extend(kb.get("hau_kiem_canh_bao", []))

        if not cac_verdict:
            cham_tong[tc] = {"verdict": "fail", "ly_do": "Không có batch nào chấm được - xem canh_bao_thieu_batch."}
        else:
            so_pass = sum(1 for v in cac_verdict if v == "pass")
            ti_le_pass = so_pass / len(cac_verdict)
            if ti_le_pass >= NGUONG_TI_LE_PASS_BATCH:
                ly_do = f"Đạt {so_pass}/{len(cac_verdict)} batch (≥{int(NGUONG_TI_LE_PASS_BATCH * 100)}%)."
                if cac_ly_do_fail:
                    ly_do += " Batch fail (không ảnh hưởng verdict do đạt ngưỡng): " + " | ".join(cac_ly_do_fail)
                cham_tong[tc] = {"verdict": "pass", "ly_do": ly_do}
            else:
                cham_tong[tc] = {
                    "verdict": "fail",
                    "ly_do": (
                        f"Chỉ đạt {so_pass}/{len(cac_verdict)} batch "
                        f"(<{int(NGUONG_TI_LE_PASS_BATCH * 100)}%): " + " | ".join(cac_ly_do_fail)
                    ),
                }

    if ket_qua_hinh_thuc.get("loi"):
        canh_bao_thieu_batch.append(f"[hình thức] {ket_qua_hinh_thuc['loi']}")
        for tc in TIEU_CHI_HINH_THUC:
            cham_tong[tc] = {"verdict": "fail", "ly_do": "Không chấm được - xem canh_bao_thieu_batch."}
    else:
        for tc in TIEU_CHI_HINH_THUC:
            cham_tong[tc] = ket_qua_hinh_thuc["cham"].get(tc, {"verdict": "fail", "ly_do": "(thiếu)"})
        if ket_qua_hinh_thuc.get("loi_dinh_dang"):
            canh_bao_loi_dinh_dang.extend(f"{tc} (hình thức)" for tc in ket_qua_hinh_thuc["loi_dinh_dang"])

    so_dat = sum(1 for tc in TIEU_CHI if cham_tong.get(tc, {}).get("verdict") == "pass")

    ket_qua_cham = {
        "id": persona.get("id"),
        "tieu_chi": cham_tong,
        "so_tieu_chi_dat": so_dat,
        "verdict_cuoi": "DAT" if so_dat == len(TIEU_CHI) else "KHONG_DAT",
        "so_batch_da_cham_nguon": len(cac_batch),
    }
    if canh_bao_loi_dinh_dang:
        ket_qua_cham["canh_bao_loi_dinh_dang"] = (
            f"Các tiêu chí bị judge trả sai định dạng (đã mặc định fail): "
            f"{', '.join(canh_bao_loi_dinh_dang)}."
        )
    if canh_bao_thieu_batch:
        ket_qua_cham["canh_bao_loi_goi_judge"] = canh_bao_thieu_batch
    if thieu_g + thieu_b > 0:
        ket_qua_cham["canh_bao_thieu_nguon"] = (
            f"{thieu_g + thieu_b} tin gián tiếp/bài góc nhìn không khớp được với văn bản nguồn "
            f"(chỉ còn tiêu đề) - kết quả chấm có thể KHÔNG ĐÁNG TIN CẬY cho phần đó."
        )
    if hau_kiem_tong:
        ket_qua_cham["can_soat_tay"] = True
        ket_qua_cham["hau_kiem_canh_bao"] = hau_kiem_tong

    return ket_qua_cham


def in_ket_qua_cham(persona_id: str, cham: dict) -> None:
    """In nhanh kết quả chấm ra console, kèm tên tiêu chí fail nếu có, để
    dễ quan sát khi chạy hàng loạt mà không cần mở từng file json."""
    verdict = cham.get("verdict_cuoi")
    if verdict == "DAT":
        print(f" [{persona_id}] ĐẠT cả 6 tiêu chí.")
    elif verdict == "KHONG_DAT":
        fail_list = [
            tc for tc in TIEU_CHI
            if cham.get("tieu_chi", {}).get(tc, {}).get("verdict") == "fail"
        ]
        print(f" [{persona_id}] Phát hiện fail — rớt {len(fail_list)}/6 tiêu chí: {', '.join(fail_list)}")
    else:
        print(f" [{persona_id}] bỏ qua chấm — {cham.get('note', 'không rõ lý do')}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Đánh giá bản tóm tắt RSS bằng LLM Judge (OSS)")
    parser.add_argument("--id", type=str, help="id của persona, ví dụ NN0001")
    parser.add_argument("-n", "--so-luong", type=int, help="Chỉ đánh giá N kết quả đầu tiên")
    parser.add_argument("--variant", type=str, default=None,
                        help="ten bien the persona, neu co se doc/ghi vao thu muc con rieng")
    args = parser.parse_args()

    if args.variant:
        JSON_DIR = OUTPUT_DIR / "json" / args.variant
        EVAL_DIR = OUTPUT_DIR / "eval" / args.variant
    else:
        JSON_DIR = OUTPUT_DIR / "json"
        EVAL_DIR = OUTPUT_DIR / "eval"

    personas = load_personas(args.variant)
    persona_index = {p["id"]: p for p in personas}
    index_theo_link, index_theo_title = load_articles_index()

    EVAL_DIR.mkdir(parents=True, exist_ok=True)

    async def chay():
        client = tao_oss_client_async()
        semaphore = asyncio.Semaphore(OSS_MAX_CONCURRENCY_SUMMARY)

        if args.id:
            json_path = JSON_DIR / f"{args.id}.json"
            if not json_path.exists():
                raise SystemExit(f"Không tìm thấy kết quả rss_personalize cho id = {args.id}")
            with open(json_path, encoding="utf-8") as f:
                ket_qua_rss = json.load(f)
            persona = persona_index.get(args.id)
            if persona is None:
                raise SystemExit(f"Không tìm thấy persona có id = {args.id}")

            print(f"[{args.id}] đang chấm...")
            cham = await cham_1_persona(persona, ket_qua_rss, index_theo_link, index_theo_title, client, semaphore)

            out_path = EVAL_DIR / f"{args.id}.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(cham, f, ensure_ascii=False, indent=2)
            in_ket_qua_cham(args.id, cham)
            if cham.get("can_soat_tay"):
                print(f" [{args.id}] có {len(cham['hau_kiem_canh_bao'])} cảnh báo hậu kiểm - cần soát tay:")
                for cb in cham["hau_kiem_canh_bao"]:
                    print(f"      - {cb}")
        else:
            danh_sach_file = sorted(JSON_DIR.glob("*.json"))
            if args.so_luong:
                danh_sach_file = danh_sach_file[:args.so_luong]

            print("Tổng số kết quả cần chấm:", len(danh_sach_file))
            t_bat_dau = time.time()
            ket_qua_tong = {"dat": 0, "khong_dat": 0, "bo_qua": 0}

            async def xu_ly_mot_file(json_path):
                persona_id = json_path.stem
                out_path = EVAL_DIR / f"{persona_id}.json"
                if out_path.exists():
                    print(f"[{persona_id}] đã chấm rồi, bỏ qua.")
                    return
                persona = persona_index.get(persona_id)
                if persona is None:
                    print(f"[{persona_id}] không tìm thấy persona tương ứng, bỏ qua.")
                    return

                with open(json_path, encoding="utf-8") as f:
                    ket_qua_rss = json.load(f)
                print(f"[{persona_id}] đang chấm...")
                cham = await cham_1_persona(persona, ket_qua_rss, index_theo_link, index_theo_title, client, semaphore)
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(cham, f, ensure_ascii=False, indent=2)
                in_ket_qua_cham(persona_id, cham)

                if cham.get("verdict_cuoi") == "DAT":
                    ket_qua_tong["dat"] += 1
                elif cham.get("verdict_cuoi") == "KHONG_DAT":
                    ket_qua_tong["khong_dat"] += 1
                else:
                    ket_qua_tong["bo_qua"] += 1

            tasks = [xu_ly_mot_file(jp) for jp in danh_sach_file]
            await asyncio.gather(*tasks)

            print("\nXONG HẾT. Tổng thời gian:", round((time.time() - t_bat_dau) / 60, 1), "phút")
            print(f"ĐẠT cả 6 tiêu chí: {ket_qua_tong['dat']}")
            print(f"KHÔNG ĐẠT (thiếu ít nhất 1 tiêu chí): {ket_qua_tong['khong_dat']}")
            print(f"Bỏ qua (rỗng/lỗi/không có persona): {ket_qua_tong['bo_qua']}")

    asyncio.run(chay())