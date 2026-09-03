import json
import os
import time
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from pipeline.utils_new import retry_generate, SUMMARY_MODEL_NAME

ROOT_DIR = Path(__file__).resolve().parents[3]
MD_ROOT = ROOT_DIR / "multi_document_variants"
SHARED_ROOT = ROOT_DIR / "shared"

DATA_DIR = MD_ROOT / "data" / "bao_chi"
OUTPUT_DIR = MD_ROOT / "output" / "bao_chi" / "rss_summary"
JSON_DIR = OUTPUT_DIR / "json"
EVAL_DIR = OUTPUT_DIR / "eval"

PERSONAS_PATH = MD_ROOT / "data" / "profile_variants" / "state_profiles_nt_nn_tc_kn_cd_ch.json"
ARTICLES_PATH = DATA_DIR / "vnexpress_rss_snapshot_3007.json"

TIEU_CHI = [
    "chon_loc_phu_hop",
    "nhat_quan",
    "trinh_bay_phu_hop",
    "bo_cuc_uu_tien",
    "giong_dieu_phu_hop",
    "thai_do_dung_dan",
]

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


def lay_noi_dung_nguon(ranked_items: list, index_theo_link: dict, index_theo_title: dict) -> tuple:
    ket_qua = []
    so_khong_tim_thay = 0
    for item in ranked_items:
        goc = index_theo_link.get(item.get("link")) or index_theo_title.get(item.get("title"))
        if goc:
            noi_dung = goc.get("content") or goc.get("summary", "")
            ket_qua.append({
                "title": goc.get("title", ""),
                "noi_dung": noi_dung,
                "genre": item.get("genre"),
            })
        else:
            so_khong_tim_thay += 1
            ket_qua.append({
                "title": item.get("title", ""),
                "noi_dung": "(không tìm thấy nội dung gốc - chỉ còn tiêu đề)",
                "genre": item.get("genre"),
            })
    return ket_qua, so_khong_tim_thay

def _format_nguon(nguon_list: list, nhan: str, prefix: str) -> str:
    if not nguon_list:
        return f"{nhan}: (không có)"
    dong = [f"{nhan}:"]
    for i, n in enumerate(nguon_list, 1):
        dong.append(f"{prefix}{i}. [{n['genre']}] {n['title']}\n{n['noi_dung']}")
    return "\n".join(dong)

def _tach_doan_van(summary: str) -> list:
    return [d.strip() for d in summary.split("\n\n") if d.strip()]


def _dinh_dang_doan_van(doan_list: list) -> str:
    return "\n\n".join(f"[ĐOẠN {i}]\n{d}" for i, d in enumerate(doan_list, 1))

def _trich_cac_doan_trich_dan(text: str) -> list:
    ket_qua = []
    ket_qua.extend(re.findall(r'"([^"]{5,})"', text))
    ket_qua.extend(re.findall(r'“([^”]{5,})”', text))
    return ket_qua


def _chuan_hoa(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip().lower()


def hau_kiem_fail_reasons(cham: dict, summary: str, nguon_chinh: list, nguon_gian_tiep: list,
                          nguon_bai: list) -> dict:
    canh_bao = []
    summary_chuan = _chuan_hoa(summary)
    nguon_text_chuan = _chuan_hoa(
        " ".join((n.get("noi_dung", "") + " " + n.get("title", ""))
                 for n in nguon_chinh + nguon_gian_tiep + nguon_bai)
    )
    so_c, so_g, so_b = len(nguon_chinh), len(nguon_gian_tiep), len(nguon_bai)

    for tc, ket in cham.items():
        if not isinstance(ket, dict) or ket.get("verdict") != "fail":
            continue
        ly_do = ket.get("ly_do", "")

        for tien_to, so_str in re.findall(r"\b([CGB])(\d+)\b", ly_do):
            so = int(so_str)
            if tien_to == "C" and so > so_c:
                canh_bao.append(f"[{tc}] trích mã C{so} không tồn tại (nhóm chính chỉ có {so_c} tin).")
            if tien_to == "G" and so > so_g:
                canh_bao.append(f"[{tc}] trích mã G{so} không tồn tại (nhóm gián tiếp chỉ có {so_g} tin).")
            if tien_to == "B" and so > so_b:
                canh_bao.append(f"[{tc}] trích mã B{so} không tồn tại (nhóm góc nhìn chỉ có {so_b} bài).")

        for trich in _trich_cac_doan_trich_dan(ly_do):
            if _chuan_hoa(trich) not in summary_chuan:
                canh_bao.append(
                    f"[{tc}] trích dẫn \"{trich[:60]}...\" KHÔNG có trong bản tóm tắt - "
                    f"có khả năng judge bịa nội dung."
                )

        if any(tu in ly_do.lower() for tu in ["bỏ sót", "bỏ qua", "thiếu nội dung", "không đề cập"]):
            cac_trich = _trich_cac_doan_trich_dan(ly_do)
            if not cac_trich:
                canh_bao.append(
                    f"[{tc}] verdict fail với lý do bỏ sót/thiếu nhưng KHÔNG trích dẫn bằng chứng cụ "
                    f"thể nào (vi phạm QUY TẮC TRÍCH DẪN BẮT BUỘC) - có khả năng judge hallucinate, "
                    f"cần soát tay."
                )
            for trich in cac_trich:
                trich_chuan = _chuan_hoa(trich)
                if trich_chuan and trich_chuan not in nguon_text_chuan:
                    canh_bao.append(
                        f"[{tc}] cho rằng bản tóm tắt bỏ sót \"{trich[:60]}...\" nhưng nội dung này "
                        f"KHÔNG tìm thấy trong văn bản nguồn - có khả năng judge suy diễn nội dung "
                        f"không tồn tại."
                    )

    return {"can_soat_tay": bool(canh_bao), "chi_tiet_canh_bao": canh_bao}

def build_judge_prompt(persona: dict, nguon_chinh: list, nguon_gian_tiep: list, nguon_bai: list,
                        summary: str, thong_ke: dict) -> str:
    ho_so = f"""
Vai trò: {persona.get('kinh_nghiem', '')}
Đơn vị công tác: {persona.get('to_chuc', '')}
Ngành: {persona.get('nganh_to', '')} - {persona.get('nganh_nho', '')}
Chủ đề quan tâm (ưu tiên từ cao xuống thấp): {', '.join(persona.get('chu_de', []))}
Khuynh hướng/mối quan tâm trước mắt: {persona.get('cau_hoi_truoc_mat', '')}
Mô tả chung: {persona.get('mo_ta_chung', '')}
""".strip()

    nguon_text = (
        _format_nguon(nguon_chinh, "VĂN BẢN NGUỒN - nhóm tin chính (đúng chu_de persona)", "C")
        + "\n\n"
        + _format_nguon(nguon_gian_tiep, "VĂN BẢN NGUỒN - nhóm tin liên quan gián tiếp", "G")
        + "\n\n"
        + _format_nguon(nguon_bai, "VĂN BẢN NGUỒN - nhóm bài góc nhìn/phân tích liên quan (không phải tin thời sự)", "B")
    )

    ghi_chu_danh_so = """
LƯU Ý QUAN TRỌNG VỀ ĐÁNH SỐ: ba danh sách trên đánh số ĐỘC LẬP với 3 tiền tố khác nhau — "C1,
C2..." cho nhóm tin chính, "G1, G2..." cho nhóm tin gián tiếp, "B1, B2..." cho nhóm bài góc
nhìn/phân tích. LUÔN dùng đúng tiền tố khi trích dẫn trong ly_do (ví dụ "C4", không viết trống
"tin 4"), để tránh nhầm lẫn giữa các danh sách. Tin gián tiếp (G) được PHÉP bị lược bỏ hoàn toàn
khỏi bản tóm tắt nếu ít giá trị — KHÔNG được coi việc thiếu một tin G nào đó là lỗi
chon_loc_phu_hop hay trinh_bay_phu_hop; tin nhóm chính (C) bắt buộc đủ 1 tin - 1 đoạn, TRỪ
trường hợp 2 tin C.. được xác nhận cùng nói về MỘT SỰ KIỆN CỤ THỂ (xem quy tắc xác nhận trùng sự
kiện bên dưới) thì được phép gộp hợp lệ. Nhóm bài góc nhìn/phân tích (B) là nội dung THAM KHẢO
THÊM, không bắt buộc, có thể có 0, 1 hoặc 2 bài tuỳ ngày — KHÔNG được coi việc thiếu/ít bài nhóm
B, hoặc việc nhóm B hoàn toàn không xuất hiện, là lỗi chon_loc_phu_hop hay bo_cuc_uu_tien. CHỈ
đoạn ĐẦU TIÊN ứng với nhóm B trong bản tóm tắt bắt đầu bằng cụm "Góc nhìn liên quan:" — nếu nhóm
B có nhiều hơn 1 bài (B1, B2...), các đoạn B tiếp theo KHÔNG lặp lại cụm này, mà là các đoạn LIÊN
TIẾP ngay sau đoạn có prefix đó, luôn nằm ở CUỐI CÙNG bản tóm tắt (đúng bằng số bài trong nhóm B).
KHÔNG được coi việc các đoạn B sau đoạn đầu không có cụm "Góc nhìn liên quan:" là lỗi thiếu nhất
quán hay lỗi trình bày. Toàn bộ các đoạn thuộc nhóm B đều KHÔNG tính vào yêu cầu "1 tin - 1 đoạn"
áp dụng cho nhóm chính.

MỘT SỐ ĐOẠN DẠNG LIỆT KÊ NGẮN CŨNG LÀ HỢP LỆ, KHÔNG PHẢI LỖI GỘP ĐOẠN: đoạn mở đầu bằng cụm "Các
tin khác đáng chú ý:" được PHÉP liệt kê NHIỀU tin G khác nhau (nhiều mã G cùng xuất hiện) trong
CÙNG một đoạn — đây là cách trình bày CHỦ ĐÍCH cho các tin gián tiếp giá trị thấp, hoàn toàn KHÁC
với việc gộp sai 2 tin C của nhóm chính. TUYỆT ĐỐI KHÔNG được áp dụng quy tắc "xác nhận trùng sự
kiện" hay đòi hỏi tách riêng từng tin G thành 1 đoạn cho đoạn liệt kê này, và KHÔNG được kết luận
fail (chon_loc_phu_hop, trinh_bay_phu_hop hay bo_cuc_uu_tien) chỉ vì phát hiện nhiều mã G cùng
nằm trong 1 đoạn dạng liệt kê "Các tin khác đáng chú ý:". Tương tự, nếu bản tóm tắt có từ 2 đoạn
"Góc nhìn liên quan:" trở lên, việc chúng dùng chung một cụm mở đầu GIỐNG NHAU về câu chữ KHÔNG
phải là bằng chứng của lỗi gộp/trùng lặp — mỗi đoạn B ứng với MỘT bài riêng biệt (một mã B khác
nhau), chỉ coi là lỗi nếu nội dung THỰC SỰ trùng lặp (cùng nói về cùng một bài, cùng luận điểm),
không phải chỉ vì trùng cụm mở đầu.
""".strip()

    doan_list = _tach_doan_van(summary)
    doan_van_text = _dinh_dang_doan_van(doan_list)

    canh_bao_it_tin = ""
    if thong_ke.get("so_tin_chinh", 0) == 0:
        canh_bao_it_tin = f"""
    - CẢNH BÁO ĐẶC BIỆT: nhóm tin chính (đúng chu_de chuyên môn của persona) KHÔNG CÓ tin nào đạt
      ngưỡng phù hợp trong đợt tin này. Đây là tình huống hợp lệ do dữ liệu ngày hôm đó không có tin
      đúng chuyên môn, KHÔNG phải lỗi của bước sinh bài. Trong trường hợp này, việc bản tóm tắt dùng
      các tin thuộc nhóm gián tiếp có genre trùng với chu_de persona làm nội dung chính thay thế là
      cách xử lý ĐÚNG và nên được chấm "pass" cho chon_loc_phu_hop nếu các tin đó thực sự là lựa
      chọn phù hợp nhất trong số các tin gián tiếp hiện có — KHÔNG được yêu cầu bản tóm tắt phải có
      nội dung "đúng chuyên môn hơn" nếu nội dung đó không tồn tại trong nguồn đã cho.
    """

    thong_ke_text = f"""
    THỐNG KÊ CƠ HỌC (tính tự động, không phải cảm nhận của giám khảo):
    - Số tin trong nhóm chính (BẮT BUỘC mỗi tin 1 đoạn riêng trong phần THÂN BÀI): {thong_ke.get('so_tin_chinh')}
    - Tổng số đoạn văn thực tế đếm được trong TOÀN BỘ bản tóm tắt (kể cả mở bài, kết luận, tin
      gián tiếp): {thong_ke.get('so_doan_thuc_te')}
    - LƯU Ý: con số này CAO HƠN số tin nhóm chính là BÌNH THƯỜNG...(giữ nguyên như cũ)...
    {canh_bao_it_tin}- Ghi chú từ bước sinh bài (nếu có): {thong_ke.get('note') or '(không có)'}
    """.strip()

    prompt = f"""
Bạn là giám khảo đánh giá bản tóm tắt tin tức cá nhân hóa theo persona công chức/nhà nước.

HỒ SƠ PERSONA:
{ho_so}

{nguon_text}

{ghi_chu_danh_so}

{thong_ke_text}

BẢN TÓM TẮT CẦN CHẤM (đã được TÁCH SẴN thành {len(doan_list)} đoạn văn theo đúng dấu xuống dòng
trống trong văn bản gốc, đánh số [ĐOẠN 1], [ĐOẠN 2]... — đây là ranh giới đoạn CHÍNH XÁC, không
cần tự suy đoán):
{doan_van_text}

BƯỚC BẮT BUỘC TRƯỚC KHI CHẤM (chỉ để bạn tự suy luận, KHÔNG in ra kết quả): trước tiên, xác
định trong bản tóm tắt đâu là đoạn mở bài, đâu là đoạn kết luận, đâu là (các) đoạn tin gián
tiếp ở cuối, đâu là (các) đoạn thuộc nhóm B ở cuối cùng (đoạn đầu tiên của nhóm B có prefix
"Góc nhìn liên quan:", các đoạn B tiếp theo ngay sau đó KHÔNG lặp lại prefix nhưng vẫn thuộc
nhóm B) — những đoạn này được phép tồn tại thêm, KHÔNG tính vào yêu cầu "1 tin - 1 đoạn".
Sau khi loại các đoạn đó ra, chỉ còn lại phần THÂN BÀI ứng với nhóm tin chính: với MỖI tin C1,
C2... trong nhóm chính, xác định nó khớp với [ĐOẠN mấy] trong danh sách đã đánh số ở trên (dùng
đúng số đoạn đã cho, KHÔNG tự chia lại đoạn theo cách đọc riêng của bạn). Nếu 2 tin khớp với
CÙNG một số [ĐOẠN], đó là gộp đoạn thật — trích rõ số đoạn đó làm bằng chứng. Nếu 2 tin khớp với
2 số [ĐOẠN] khác nhau (kể cả liền kề, kể cả không có câu "Chuyển sang nhóm..." ở giữa vì cùng
nhóm chủ đề thì không cần câu đó), thì đó KHÔNG phải lỗi gộp — không được kết luận fail.
Kiểm tra thêm: nếu bản tóm tắt có từ 2 nhóm chủ đề trở lên, xác nhận MỖI lần chuyển nhóm đều có
câu dẫn báo hiệu (không chỉ lần đầu) — thiếu bất kỳ lần nào thì bo_cuc_uu_tien mặc định "fail".
Nếu xác nhận có gộp đoạn thật (2 tin C.. cùng khớp 1 số [ĐOẠN]), bước tiếp theo BẮT BUỘC: mở lại
nội dung nguồn của đúng 2 tin đó (mục VĂN BẢN NGUỒN ở trên, dùng mã C.. để tra) và đối chiếu xem
chúng có cùng nói về MỘT SỰ KIỆN CỤ THỂ hay không — cùng tên riêng/đơn vị/địa điểm liên quan,
cùng mốc thời gian, cùng hành động hoặc quyết định đang được nhắc đến.
- Nếu ĐÚNG là cùng một sự kiện (tin này chỉ đưa thêm chi tiết/góc nhìn cho cùng sự việc ở tin
  kia): đây là gộp HỢP LỆ — KHÔNG được kết luận fail cho chon_loc_phu_hop, trinh_bay_phu_hop hay
  bo_cuc_uu_tien chỉ vì lý do "gộp 2 tin". Chỉ được fail nếu đoạn văn gộp đó thực sự thiếu một
  chi tiết quan trọng của MỘT trong hai nguồn — khi đó phải nêu rõ chi tiết bị thiếu, kèm mã C..
  tương ứng làm bằng chứng.
- Nếu là HAI sự kiện khác nhau (khác chủ thể, khác thời điểm, khác nội dung cụ thể dù cùng lĩnh
  vực) bị gộp chung, hoặc một trong hai bị bỏ hẳn không xuất hiện ở đoạn nào: đây là gộp/bỏ SAI
  QUY TẮC — kết luận fail cho chon_loc_phu_hop, trích rõ cả 2 mã C.. liên quan và nêu điểm khác
  biệt cụ thể giữa hai sự kiện (ví dụ khác chủ thể/khác mốc thời gian) làm bằng chứng.

Chấm bản tóm tắt trên theo đúng 6 tiêu chí sau, mỗi tiêu chí trả về "pass" hoặc "fail"
kèm lý do ngắn gọn (tối đa 2 câu, tiếng Việt có dấu):

1. chon_loc_phu_hop: Bản tóm tắt có ưu tiên chọn chi tiết/dữ kiện liên quan trực tiếp
   đến chu_de và khuynh hướng quan tâm của persona không, có bỏ sót chi tiết quan trọng
   đúng chuyên môn không, có giữ nhiều chi tiết không liên quan không. Riêng với các đoạn
   gộp 2 tin C.. cùng một sự kiện: áp dụng đúng theo QUY TẮC XÁC NHẬN TRÙNG SỰ KIỆN ở trên,
   không tự động coi gộp là lỗi.
2. nhat_quan: Mọi thông tin trong bản tóm tắt có đúng với văn bản nguồn không (không bịa
   thêm số liệu/sự kiện), các câu trong bản tóm tắt có mâu thuẫn nhau không, có gán cho
   persona đặc điểm/quan điểm không có trong hồ sơ không.
3. trinh_bay_phu_hop: Độ dài có vượt quá văn bản nguồn không; nếu tin đúng chuyên môn
   persona thì có dùng thuật ngữ/bố cục kiểu chuyên gia không, nếu tin KHÔNG đúng chuyên
   môn persona thì có trình bày ở mức phổ thông, không lạm dụng thuật ngữ chuyên ngành
   không cần thiết không; câu văn có rõ ràng mạch lạc, không lặp ý không.
4. bo_cuc_uu_tien: Nội dung liên quan nhất với persona có được đặt lên đầu/nổi bật không,
   nội dung phụ có được đẩy xuống sau hoặc lược bớt không.
5. giong_dieu_phu_hop: Giọng điệu có phù hợp với vị trí công tác và mục đích sử dụng
   (tham mưu/theo dõi chuyên ngành) của persona không, có quá suồng sã hoặc quá hoa mỹ
   không cần thiết không; bản tóm tắt có GIỮ ĐÚNG tính chất định hướng/khuynh hướng của
   mối quan tâm persona mà KHÔNG biến thành câu hỏi trực tiếp hay lời khuyên/kêu gọi
   hành động lộ liễu không.
6. thai_do_dung_dan: Bản tóm tắt có giữ thái độ khách quan trung lập không, có câu phán
   xét/thiên vị/suy diễn động cơ không, có tôn trọng đúng mực vai trò persona không.

Với MỖI tiêu chí (cả pass lẫn fail), ly_do PHẢI nêu ít nhất 1 ví dụ cụ thể: một chi
tiết/câu trong bản tóm tắt, đối chiếu với một chi tiết tương ứng trong hồ sơ persona
hoặc văn bản nguồn (dùng mã C../G.. khi trích dẫn tin nguồn). Không được viết lý do
chung chung không có dẫn chứng cụ thể.

QUY TẮC TRÍCH DẪN BẮT BUỘC: mọi ly_do khẳng định bản tóm tắt có lỗi (verdict "fail") PHẢI trích
một cụm từ/câu NGẮN thực sự có trong bản tóm tắt làm bằng chứng, đặt trong dấu ngoặc kép, kèm mã
tin (C.. hoặc G..) tương ứng nếu liên quan đến một tin cụ thể. Nếu không thể trích dẫn cụ thể
như vậy, KHÔNG được kết luận "fail" cho tiêu chí đó — chuyển sang "pass".

QUY TẮC RIÊNG CHO CÁO BUỘC "GỘP ĐOẠN" HOẶC "BỎ SÓT TIN": nếu ly_do khẳng định có tin bị gộp
chung đoạn với tin khác (ví dụ "gộp C3 và C4 vào cùng một đoạn"), BẮT BUỘC phải trích nguyên
văn đoạn văn đó trong bản tóm tắt và chỉ ra rõ cả hai nội dung của 2 tin cùng xuất hiện trong
đúng đoạn văn đó. Nếu không trích ra được một đoạn văn cụ thể chứa CẢ HAI nội dung, thì KHÔNG
được kết luận có gộp đoạn — phải chuyển sang "pass" cho tiêu chí đó. Tương tự, nếu khẳng định
có tin C.. bị bỏ sót hoàn toàn, phải xác nhận đã rà soát TOÀN BỘ các đoạn trong thân bài (không
chỉ đọc lướt) trước khi kết luận.

QUY TẮC CHỐNG SUY DIỄN NGUỒN KHÔNG TỒN TẠI: nếu ly_do phê bình bản tóm tắt "bỏ sót" một chủ
đề/nội dung nào đó, BẮT BUỘC phải chỉ ra đúng mã tin (C.. hoặc G..) trong hai danh sách VĂN BẢN
NGUỒN đã cho ở trên có chứa đúng nội dung bị cho là bỏ sót đó. Nếu rà soát toàn bộ danh sách
nguồn mà KHÔNG tìm thấy tin nào khớp, thì đây là suy diễn sai — TUYỆT ĐỐI không được dùng làm lý
do fail. Hồ sơ persona (chu_de, khuynh hướng, mô tả) chỉ mô tả MỐI QUAN TÂM của người đọc, KHÔNG
đảm bảo rằng ngày hôm đó có tin tức thực tế đúng mối quan tâm đó — bản tóm tắt chỉ có thể tóm
tắt những gì THỰC SỰ tồn tại trong hai danh sách nguồn đã cho, không hơn.

QUY TẮC MẶC ĐỊNH KHI CHẤM: bạn PHẢI đóng vai giám khảo khó tính. Nếu phân vân giữa "pass" và
"fail" ở bất kỳ tiêu chí nào, LUÔN chọn "fail" — "pass" chỉ được chọn khi có bằng chứng rõ ràng,
cụ thể, không có ngoại lệ đáng ngờ nào. Không được chấm "pass" chỉ vì văn phong trôi chảy hoặc
"đọc có vẻ ổn" — phải đối chiếu với văn bản nguồn và hồ sơ persona ở TỪNG câu quan trọng.

CHỈ trả về một đối tượng JSON đúng định dạng sau, không thêm lời dẫn, không dùng markdown.
Bước đối chiếu ở trên bạn PHẢI tự thực hiện trong suy luận nội bộ để xác định verdict và viết
ly_do cho chính xác, nhưng TUYỆT ĐỐI KHÔNG in danh sách đối chiếu đó ra trong kết quả trả về.
Kết quả JSON CHỈ được chứa ĐÚNG 6 khóa (chon_loc_phu_hop, nhat_quan, trinh_bay_phu_hop,
bo_cuc_uu_tien, giong_dieu_phu_hop, thai_do_dung_dan), mỗi khóa là MỘT OBJECT có ĐÚNG 2 trường
"verdict" và "ly_do" — không thêm khóa nào khác, không có khóa nào mang giá trị mảng/list:
{{
  "chon_loc_phu_hop": {{"verdict": "pass hoặc fail", "ly_do": "..."}},
  "nhat_quan": {{"verdict": "pass hoặc fail", "ly_do": "..."}},
  "trinh_bay_phu_hop": {{"verdict": "pass hoặc fail", "ly_do": "..."}},
  "bo_cuc_uu_tien": {{"verdict": "pass hoặc fail", "ly_do": "..."}},
  "giong_dieu_phu_hop": {{"verdict": "pass hoặc fail", "ly_do": "..."}},
  "thai_do_dung_dan": {{"verdict": "pass hoặc fail", "ly_do": "..."}}
}}
""".strip()

    return prompt


def cham_1_persona(persona: dict, ket_qua_rss: dict, index_theo_link: dict, index_theo_title: dict, client,
                    model_name: str = SUMMARY_MODEL_NAME) -> dict:
    summary = ket_qua_rss.get("summary", "")
    if not summary:
        return {
            "id": persona.get("id"),
            "note": "Bỏ qua đánh giá - bản tóm tắt rỗng (không có tin khớp chu_de).",
        }

    nguon_chinh, thieu_1 = lay_noi_dung_nguon(ket_qua_rss.get("ranked_articles", []), index_theo_link, index_theo_title)
    nguon_gian_tiep, thieu_2 = lay_noi_dung_nguon(ket_qua_rss.get("tin_gian_tiep", []), index_theo_link,
                                                  index_theo_title)
    nguon_bai, thieu_3 = lay_noi_dung_nguon(ket_qua_rss.get("bai_lien_quan", []), index_theo_link, index_theo_title)
    for n in nguon_bai:
        n["genre"] = "Góc nhìn"
    tong_bai = len(ket_qua_rss.get("ranked_articles", [])) + len(ket_qua_rss.get("tin_gian_tiep", [])) + len(
        ket_qua_rss.get("bai_lien_quan", []))
    tong_thieu = thieu_1 + thieu_2 + thieu_3

    thong_ke = {
        "so_tin_chinh": len(ket_qua_rss.get("ranked_articles", [])),
        "so_doan_thuc_te": ket_qua_rss.get("so_doan_thuc_te"),
        "note": ket_qua_rss.get("note"),
    }
    prompt = build_judge_prompt(persona, nguon_chinh, nguon_gian_tiep, nguon_bai, summary, thong_ke)

    def _call():
        return client.models.generate_content(
            model=model_name,
            contents=prompt,
            config={
                "temperature": 0.0,
                "response_mime_type": "application/json",
            },
        )

    response = retry_generate(_call)

    raw = response.text.strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        cham = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "id": persona.get("id"),
            "note": "LỖI: không parse được JSON từ Gemini, xem raw_response.",
            "raw_response": raw,
        }

    loi_dinh_dang = []
    for tc in TIEU_CHI:
        gt = cham.get(tc)
        if not isinstance(gt, dict) or "verdict" not in gt:
            loi_dinh_dang.append(tc)
            cham[tc] = {
                "verdict": "fail",
                "ly_do": "LỖI ĐỊNH DẠNG: judge trả về sai cấu trúc cho tiêu chí này, mặc định fail.",
            }

    so_dat = sum(1 for tc in TIEU_CHI if cham.get(tc, {}).get("verdict") == "pass")

    ket_qua_cham = {
        "id": persona.get("id"),
        "tieu_chi": cham,
        "so_tieu_chi_dat": so_dat,
        "verdict_cuoi": "DAT" if so_dat == len(TIEU_CHI) else "KHONG_DAT",
    }
    if loi_dinh_dang:
        ket_qua_cham["canh_bao_loi_dinh_dang"] = (
            f"Các tiêu chí bị judge trả sai định dạng (đã mặc định fail): {', '.join(loi_dinh_dang)}. "
            f"raw_response đã lưu riêng để soát tay."
        )
        ket_qua_cham["raw_response_loi"] = raw

    if tong_thieu > 0:
        ket_qua_cham["canh_bao_thieu_nguon"] = (
            f"{tong_thieu}/{tong_bai} bài không khớp được với văn bản nguồn "
            f"(chỉ còn tiêu đề) - kết quả chấm có thể KHÔNG ĐÁNG TIN CẬY."
        )

    hau_kiem = hau_kiem_fail_reasons(cham, summary, nguon_chinh, nguon_gian_tiep, nguon_bai)
    if hau_kiem["can_soat_tay"]:
        ket_qua_cham["can_soat_tay"] = True
        ket_qua_cham["hau_kiem_canh_bao"] = hau_kiem["chi_tiet_canh_bao"]

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
    from google import genai

    API_KEY = os.getenv("GEMINI_API_KEY")

    parser = argparse.ArgumentParser(description="Đánh giá bản tóm tắt RSS bằng LLM Judge (Gemini)")
    parser.add_argument("--id", type=str, help="id của persona, ví dụ NN0001")
    parser.add_argument("-n", "--so-luong", type=int, help="Chỉ đánh giá N kết quả đầu tiên")
    parser.add_argument("--variant", type=str, default=None, help="ten bien the persona")
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
    client = genai.Client(api_key=API_KEY)

    EVAL_DIR.mkdir(parents=True, exist_ok=True)

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
        cham = cham_1_persona(persona, ket_qua_rss, index_theo_link, index_theo_title, client)

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
        thong_ke_dat = 0
        thong_ke_khong_dat = 0
        thong_ke_bo_qua = 0

        for json_path in danh_sach_file:
            persona_id = json_path.stem
            out_path = EVAL_DIR / f"{persona_id}.json"
            if out_path.exists():
                print(f"[{persona_id}] đã chấm rồi, bỏ qua.")
                continue

            persona = persona_index.get(persona_id)
            if persona is None:
                print(f"[{persona_id}] không tìm thấy persona tương ứng, bỏ qua.")
                continue

            with open(json_path, encoding="utf-8") as f:
                ket_qua_rss = json.load(f)
            time.sleep(10)
            print(f"[{persona_id}] đang chấm...")
            cham = cham_1_persona(persona, ket_qua_rss, index_theo_link, index_theo_title, client)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(cham, f, ensure_ascii=False, indent=2)
            in_ket_qua_cham(persona_id, cham)
            if cham.get("verdict_cuoi") == "DAT":
                thong_ke_dat += 1
            elif cham.get("verdict_cuoi") == "KHONG_DAT":
                thong_ke_khong_dat += 1
            else:
                thong_ke_bo_qua += 1


        print("\nXONG HẾT. Tổng thời gian:", round((time.time() - t_bat_dau) / 60, 1), "phút")
        print(f"ĐẠT cả 6 tiêu chí: {thong_ke_dat}")
        print(f"KHÔNG ĐẠT (thiếu ít nhất 1 tiêu chí): {thong_ke_khong_dat}")
        print(f"Bỏ qua (rỗng/lỗi/không có persona): {thong_ke_bo_qua}")