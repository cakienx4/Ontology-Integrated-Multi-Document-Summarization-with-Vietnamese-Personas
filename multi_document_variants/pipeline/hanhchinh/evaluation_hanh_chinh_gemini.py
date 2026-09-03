import json
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from pipeline.utils_new import retry_generate, SUMMARY_MODEL_NAME

ROOT_DIR = Path(__file__).resolve().parents[2]

TIEU_CHI = [
    "chon_loc_phu_hop",
    "nhat_quan",
    "trinh_bay_phu_hop",
    "bo_cuc_uu_tien",
    "giong_dieu_phu_hop",
    "thai_do_dung_dan",
]

TANG_TEN = {0: "chuyên sâu", 1: "trung bình", 2: "nền"}


# ==== BƯỚC 1: LỌC MỤC RỖNG (dùng lại đúng điều kiện lọc bên personalize) ====

def loc_muc_hop_le(danh_sach_muc):
    ket_qua = []
    for m in danh_sach_muc:
        if m.get("heading") is None and not m.get("doan_van"):
            continue
        ket_qua.append(m)
    return ket_qua


# ==== BƯỚC 2: FORMAT MỤC GỐC THÀNH BLOCK [MỤC N] ====

def dinh_dang_danh_sach_muc(danh_sach_muc_loc):
    ds = ""
    for i, muc in enumerate(danh_sach_muc_loc, 1):
        noi_dung = "\n   ".join(muc.get("doan_van", []))
        tang = muc.get("tang_do_sau", 2)
        ds += (
            f"\n[MỤC {i}] (tầng độ sâu yêu cầu: {TANG_TEN.get(tang, 'nền')})\n"
            f"Tiêu đề: \"{muc.get('heading') or '(không có tiêu đề riêng)'}\"\n"
            f"Nội dung gốc: {noi_dung}\n"
        )
    return ds


# ==== BƯỚC 3: HẬU KIỂM PYTHON - PHÁT HIỆN ĐÁNH SỐ MỤC CÒN SÓT ====

MAU_DANH_SO_MUC = re.compile(
    r"(^|\n)\s*(mục\s*\d+[:.]|(\(?\d+[.)]\s){1}|[IVX]+[.)]\s)",
    re.IGNORECASE,
)


def hau_kiem_dinh_dang(summary):
    ly_do = []
    if MAU_DANH_SO_MUC.search(summary):
        ly_do.append(
            "Phát hiện mẫu đánh số/tiêu đề mục còn sót trong văn bản "
            "(regex khớp dạng 'Mục N:', '1.', 'I.' ở đầu dòng)."
        )
    return ly_do


def _trich_cac_doan_trich_dan(text):
    ket_qua = []
    ket_qua.extend(re.findall(r'"([^"]{5,})"', text))
    ket_qua.extend(re.findall(r'“([^”]{5,})”', text))
    return ket_qua


def _chuan_hoa(s):
    return re.sub(r"\s+", " ", s or "").strip().lower()


def hau_kiem_fail_reasons(cham, summary):
    canh_bao = []
    summary_chuan = _chuan_hoa(summary)

    for tc in ("bo_cuc_uu_tien", "giong_dieu_phu_hop"):
        ket = cham.get(tc)
        if not isinstance(ket, dict) or ket.get("verdict") != "fail":
            continue
        ly_do = ket.get("ly_do", "")
        cac_trich = _trich_cac_doan_trich_dan(ly_do)

        if not cac_trich:
            canh_bao.append(
                f"[{tc}] verdict fail nhưng KHÔNG trích dẫn câu cụ thể nào từ "
                f"bản tóm tắt làm bằng chứng - vi phạm quy tắc trích dẫn bắt "
                f"buộc, có khả năng judge nhận định cảm tính, cần soát tay."
            )
            continue

        for trich in cac_trich:
            if _chuan_hoa(trich) not in summary_chuan:
                canh_bao.append(
                    f"[{tc}] trích dẫn \"{trich[:60]}...\" KHÔNG có trong bản "
                    f"tóm tắt - có khả năng judge bịa nội dung."
                )

    return canh_bao


# ==== BƯỚC 4: DỰNG PROMPT ĐÁNH GIÁ ====

def build_judge_prompt(persona, ket_qua_tom_tat, danh_sach_muc_loc):
    danh_sach_muc_text = dinh_dang_danh_sach_muc(danh_sach_muc_loc)
    so_muc_hop_le = len(danh_sach_muc_loc)

    ho_so = f"""
Ngành/lĩnh vực: {persona.get('nganh_to', '')} - {persona.get('nganh_nho', '')}
Đơn vị công tác: {persona.get('to_chuc', '')}
Mô tả chung: {persona.get('mo_ta_chung', '')}
Style tổng thể được hệ thống gán: {ket_qua_tom_tat.get('style')}
""".strip()

    prompt = f"""Bạn là giám khảo đánh giá chất lượng bản tóm tắt cá nhân hóa văn bản
hành chính. Nhiệm vụ: chấm bản tóm tắt dưới đây theo ĐÚNG 6 tiêu chí, mỗi
tiêu chí trả về "verdict": "pass" hoặc "fail" kèm "ly_do" (trích dẫn cụ thể,
PHẢI dựa trên nội dung THỰC SỰ có trong [MỤC N] gốc hoặc trong bản tóm tắt,
KHÔNG được suy diễn nội dung không tồn tại).

HỒ SƠ NGƯỜI ĐỌC:
{ho_so}

VĂN BẢN GỐC, đã chia mục theo đúng thứ tự, mỗi mục có ghi tầng độ sâu mà hệ
thống YÊU CẦU áp dụng khi tóm tắt (đây là tầng ĐÚNG theo thiết kế, dùng làm
căn cứ chấm, không phải tầng do bản tóm tắt tự thể hiện):
{danh_sach_muc_text}

Văn bản có tổng {so_muc_hop_le} mục hợp lệ (đã loại mục rỗng không có nội
dung).

BẢN TÓM TẮT CẦN CHẤM:
\"\"\"
{ket_qua_tom_tat.get('summary')}
\"\"\"

ĐỊNH NGHĨA 6 TIÊU CHÍ:

1. chon_loc_phu_hop: Các mục có tầng "chuyên sâu" hoặc "trung bình" phải có
   nội dung tương ứng xuất hiện đầy đủ, không bỏ sót ý quan trọng, trong bản
   tóm tắt. Nếu phát hiện thiếu, PHẢI trích dẫn đúng [MỤC N] bị bỏ sót và nội
   dung cụ thể bị thiếu. TUYỆT ĐỐI KHÔNG được phàn nàn thiếu nội dung không
   có trong bất kỳ [MỤC N] nào ở trên - nếu nội dung đó không tồn tại trong
   văn bản gốc thì đây không phải lỗi.

2. nhat_quan: Văn phong, xưng hô, thuật ngữ không được mâu thuẫn giữa các
   đoạn khác nhau trong cùng bản tóm tắt (ví dụ không được vừa dùng thuật
   ngữ chuyên ngành không giải thích ở đoạn này, vừa giải thích lại đúng
   thuật ngữ đó ở đoạn khác một cách thiếu nhất quán).

3. trinh_bay_phu_hop: Bản tóm tắt PHẢI là văn xuôi liền mạch. FAIL nếu có
   bất kỳ dòng nào đánh số mục ("Mục 1:", "1.", "I."...), gạch đầu dòng liệt
   kê máy móc, hoặc chèn câu chú thích về quá trình viết bài (ví dụ: "(mục
   này được tóm gọn vì...)").

4. bo_cuc_uu_tien: Gồm 2 phần, PHẢI đánh giá riêng từng phần:
   (a) Thứ tự: các mục trong bản tóm tắt PHẢI đúng thứ tự [MỤC 1], [MỤC 2],
   ... như liệt kê ở trên - không được đảo thứ tự. LƯU Ý VỀ GỘP MỤC: quy tắc
   gộp nhiều mục tầng "nền" liên tiếp thành MỘT đoạn khái quát CHỈ áp dụng
   khi "Style tổng thể được hệ thống gán" (xem hồ sơ người đọc ở trên) là
   "binh_thuong" - trường hợp này việc gộp là ĐÚNG THIẾT KẾ, KHÔNG bị coi là
   lỗi thứ tự, miễn nội dung đoạn gộp vẫn phản ánh đúng trình tự các mục gốc.
   Nếu style là "chuyen_sau" hoặc "khong_chuyen_mon", các mục tầng "nền"
   HẠN CHẾ gộp - mỗi mục NÊN có đoạn/câu riêng; chỉ khi tự nhận thấy các đoạn 
   ấy có cùng nội dung nên gộp lại thì mới gộp 
   (b) Chi tiết theo tầng: mục tầng "chuyên sâu" PHẢI giữ lại chi tiết cụ
   thể có trong [MỤC N] gốc (số liệu, mốc thời gian, tên đơn vị chủ trì/
   phối hợp, nhiệm vụ cụ thể).
    LƯU Ý DÙNG CHUNG CHO MỌI STYLE VÀ MỌI TẦNG (kể cả tầng "chuyên sâu"): số
   hiệu, ký hiệu hoặc ngày ban hành của các văn bản viện dẫn (ví dụ
   "777/TTg-TCCV", "1186/KH-BGDĐT", "4054/BGDĐT-GDPT", "551-TB/TU"...) KHÔNG
   được tính là "chi tiết cần giữ" ở bất kỳ tiêu chí nào bên dưới. Việc bản
   tóm tắt lược bỏ các số hiệu này là ĐÚNG THIẾT KẾ, TUYỆT ĐỐI KHÔNG được coi
   là thiếu chi tiết hay căn cứ để fail - dù ở tầng hay style nào.

   Mục tầng "nền" xử lý KHÁC NHAU tùy "Style tổng thể được hệ thống gán":
    - style "binh_thuong": mục tầng nền PHẢI phản ánh được nội dung chính của
      mục đó bằng ngôn ngữ phổ thông, không đi sâu vào các chi tiết kỹ thuật,
      danh sách dài hoặc nhiệm vụ quá cụ thể.

      Toàn bộ các mục tầng nền cộng lại PHẢI bao quát đầy đủ các nhóm nội dung
      chính của văn bản theo đúng trình tự.

      Không bắt buộc giữ mọi số liệu, mốc thời gian, tên đơn vị hoặc nhiệm vụ
      chi tiết; tuy nhiên KHÔNG được lược bỏ cả một mục hoặc một nhóm nội dung
      lớn chỉ vì đó là tầng nền.

      Không fail chỉ vì đoạn dài hơn 1 câu hoặc gồm nhiều đoạn nếu nội dung vẫn
      dừng ở mức khái quát.
   - style "chuyen_sau" hoặc "khong_chuyen_mon": mục tầng nền PHẢI giữ lại
     chi tiết cụ thể (số liệu, mốc thời gian, tên đơn vị, nhiệm vụ cụ thể)
     giống như mục tầng chuyên sâu, KHÔNG được tóm chung chung/lược bỏ chi
     tiết - nếu phát hiện thiếu, PHẢI fail và trích dẫn cụ thể [MỤC N] cùng
     chi tiết bị thiếu, tương tự cách chấm cho mục tầng chuyên sâu.
    Vì bản tóm tắt là văn xuôi liền mạch không đánh số, hãy xác định đoạn/
    câu tương ứng với từng [MỤC N] dựa trên NỘI DUNG (chủ đề, tên cơ quan,
    nhiệm vụ được nhắc tới) trùng khớp với [MỤC N] đó, không dựa vào vị trí
    đánh số.
    Đối với mục tầng nền của style "binh_thuong", khi đánh giá cần ưu tiên tính
    bao quát hơn độ ngắn. Một mục được coi là đạt nếu người đọc có thể hiểu được
    mục đó đề cập tới vấn đề gì và các nhóm nội dung chính là gì, dù đã lược bỏ
    các chi tiết cụ thể. Chỉ fail khi bản tóm tắt bỏ hẳn một nhóm nội dung quan
    trọng hoặc chỉ phản ánh một phần rất nhỏ của mục gốc.
   QUY TẮC BẮT BUỘC: TUYỆT ĐỐI KHÔNG được fail phần (b) chỉ vì ấn tượng
   chung "độ dài tương đương" hay "chưa nổi bật". CHỈ được fail phần (b)
   khi chỉ ra được ÍT NHẤT MỘT chi tiết cụ thể (số liệu/mốc thời gian/tên
   đơn vị/nhiệm vụ cụ thể) CÓ trong [MỤC N] tầng chuyên sâu nhưng KHÔNG
   xuất hiện trong bản tóm tắt, và PHẢI trích nguyên văn câu trong bản tóm
   tắt (đặt trong dấu ngoặc kép) làm bằng chứng cho việc thiếu chi tiết đó.
   Nếu không trích dẫn được câu cụ thể trong bản tóm tắt, PHẢI để verdict
   là "pass".

5. giong_dieu_phu_hop: Đoạn ứng với mục tầng "chuyên sâu" phải dùng thuật
   ngữ hành chính/pháp lý/chuyên ngành tự nhiên, KHÔNG giải thích lại khái
   niệm cơ bản. Đoạn ứng với mục tầng "trung bình" phải dùng ngôn ngữ phổ
   thông, giải thích ngắn gọn nếu buộc dùng thuật ngữ. Đoạn ứng với mục tầng
   "nền" phải tóm tắt CHUNG CHUNG (không đi vào chi tiết cụ thể), dùng ngôn
   ngữ phổ thông đơn giản - không có giới hạn cứng về số câu, chỉ cần đảm
   bảo nội dung khái quát và ngôn ngữ đơn giản, dễ hiểu.
   LƯU Ý VĂN PHONG TẦNG NỀN THEO STYLE TỔNG THỂ (xem "Style tổng thể được hệ
   thống gán" trong hồ sơ người đọc ở trên):
   - style "chuyen_sau": người đọc có chuyên môn ở mục khác trong văn bản,
     nên các đoạn tầng nền ĐƯỢC PHÉP dùng các thuật ngữ hành chính PHỔ BIẾN,
     thông dụng (ví dụ "sáp nhập", "đề án", "Quyết định", "UBND", "tổ chức
     lại bộ máy") mà KHÔNG bị coi là lỗi - chỉ fail nếu dùng thuật ngữ
     CHUYÊN NGÀNH của một lĩnh vực cụ thể (không phải thuật ngữ hành chính
     phổ biến) mà không giải thích.
   - style "khong_chuyen_mon" hoặc "binh_thuong": các đoạn tầng nền PHẢI
     dùng ngôn ngữ phổ thông đơn giản hơn, hạn chế cả thuật ngữ hành chính
     phổ biến - nếu nhắc tới thì BẮT BUỘC phải có giải thích ngắn gọn đi
     kèm ngay trong câu; đây là điểm khác biệt so với style "chuyen_sau" và
     KHÔNG được áp cùng một tiêu chuẩn.
     QUY TẮC BẮT BUỘC: FAIL nếu tìm thấy bất kỳ thuật ngữ hành chính/pháp
     lý/chuyên ngành nào xuất hiện trong đoạn thuộc tầng "trung bình", hoặc
     tầng "nền" (khi style là "khong_chuyen_mon"/"binh_thuong"), mà KHÔNG có
     phần giải thích kèm theo trong cùng câu. Khi fail, PHẢI trích nguyên
     văn cụm từ thuật ngữ đó (đặt trong dấu ngoặc kép) làm bằng chứng. Nếu
     không trích dẫn được thuật ngữ cụ thể nào thiếu giải thích, PHẢI để
     verdict là "pass".

6. thai_do_dung_dan: Bản tóm tắt KHÔNG được tự suy luận, đánh giá, hoặc
   thêm nhận định KHÔNG có trong văn bản gốc. Chỉ trình bày lại nội dung đã
   có trong các [MỤC N], không bịa thêm ý.

Chỉ trả về JSON theo đúng định dạng sau, không markdown, không giải thích
thêm ngoài JSON:
{{
  "chon_loc_phu_hop": {{"verdict": "pass", "ly_do": "..."}},
  "nhat_quan": {{"verdict": "pass", "ly_do": "..."}},
  "trinh_bay_phu_hop": {{"verdict": "pass", "ly_do": "..."}},
  "bo_cuc_uu_tien": {{"verdict": "pass", "ly_do": "..."}},
  "giong_dieu_phu_hop": {{"verdict": "pass", "ly_do": "..."}},
  "thai_do_dung_dan": {{"verdict": "pass", "ly_do": "..."}}
}}"""

    return prompt


# ==== BƯỚC 5: GỌI LLM CHẤM + HẬU KIỂM ====

def cham_1_ban_tom_tat(persona, ket_qua_tom_tat, client, model_name=SUMMARY_MODEL_NAME):
    danh_sach_muc_goc = ket_qua_tom_tat.get("danh_sach_muc_voi_tang", [])
    danh_sach_muc_loc = loc_muc_hop_le(danh_sach_muc_goc)

    if "danh_sach_muc_voi_tang" not in ket_qua_tom_tat:
        return {
            "id": persona.get("id"),
            "note": (
                "Bỏ qua đánh giá - file summary này thiếu field "
                "'danh_sach_muc_voi_tang' (được tạo TRƯỚC khi personalize có patch "
                "lưu field này). Cần chạy lại tom_tat_hanh_chinh_cho_persona cho "
                "văn bản/persona này rồi mới chấm được."
            ),
        }

    if not danh_sach_muc_loc:
        return {
            "id": persona.get("id"),
            "note": (
                "Bỏ qua đánh giá - danh_sach_muc_voi_tang rỗng sau khi lọc mục "
                "hợp lệ (0 mục có nội dung). Kiểm tra lại bước extract/personalize "
                "cho văn bản này, có thể lỗi trích xuất docx."
            ),
        }

    summary = ket_qua_tom_tat.get("summary", "")
    if not summary:
        return {
            "id": persona.get("id"),
            "note": "Bỏ qua đánh giá - bản tóm tắt rỗng.",
        }

    prompt = build_judge_prompt(persona, ket_qua_tom_tat, danh_sach_muc_loc)

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
            "note": "LỖI: không parse được JSON từ model, xem raw_response.",
            "raw_response": raw,
        }
    if not isinstance(cham, dict):
        return {
            "id": persona.get("id"),
            "note": (
                "LỖI: judge trả về JSON không đúng dạng object (nhận được "
                f"{type(cham).__name__} thay vì dict) - xem raw_response."
            ),
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
        "file": ket_qua_tom_tat.get("file"),
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

    ly_do_hau_kiem = hau_kiem_dinh_dang(summary) + hau_kiem_fail_reasons(cham, summary)
    if ly_do_hau_kiem:
        ket_qua_cham["can_soat_tay"] = True
        ket_qua_cham["hau_kiem_canh_bao"] = ly_do_hau_kiem

    return ket_qua_cham


def in_ket_qua_cham(persona_id, cham):
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

    parser = argparse.ArgumentParser(description="Đánh giá bản tóm tắt hành chính bằng LLM Judge")
    parser.add_argument("--file", required=True, help="tên file docx văn bản hành chính (không cần đường dẫn đầy đủ)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--id", help="id của persona, ví dụ NN0001")
    group.add_argument("--so-luong", type=int, help="chấm từ persona đầu tiên đến persona thứ n")
    parser.add_argument("--variant", type=str, default=None, help="ten bien the persona")
    args = parser.parse_args()

    duong_dan_file = Path(args.file)
    if not duong_dan_file.exists():
        duong_dan_file = ROOT_DIR / "data" / "hanh_chinh" / duong_dan_file
    ten_file_goc = duong_dan_file.stem

    if args.variant:
        SUMMARY_DIR = ROOT_DIR / "output" / "hanh_chinh" / "summary" / args.variant / ten_file_goc
        EVAL_DIR = ROOT_DIR / "output" / "hanh_chinh" / "eval" / args.variant / ten_file_goc
    else:
        SUMMARY_DIR = ROOT_DIR / "output" / "hanh_chinh" / "summary" / ten_file_goc
        EVAL_DIR = ROOT_DIR / "output" / "hanh_chinh" / "eval" / ten_file_goc
    EVAL_DIR.mkdir(parents=True, exist_ok=True)

    if not SUMMARY_DIR.exists():
        raise SystemExit(f"Không tìm thấy thư mục summary cho văn bản này: {SUMMARY_DIR}")

    ten_file_persona = f"state_profiles_{args.variant}.json" if args.variant else "state_profiles_nt_nn_tc_kn_cd_ch.json"
    duong_dan_persona = ROOT_DIR / "data" / "profile_variants" / ten_file_persona
    with open(duong_dan_persona, encoding="utf-8") as f:
        personas = json.load(f)
    persona_index = {p["id"]: p for p in personas}

    if args.id:
        personas_can_cham = [args.id]
    else:
        personas_can_cham = [p["id"] for p in personas[:args.so_luong]]

    client = genai.Client(api_key=API_KEY)

    tong = len(personas_can_cham)
    t_bat_dau = time.time()
    thong_ke_dat = 0
    thong_ke_khong_dat = 0
    thong_ke_bo_qua = 0

    for i, persona_id in enumerate(personas_can_cham, start=1):
        out_path = EVAL_DIR / f"{persona_id}.json"
        if out_path.exists():
            print(f"[{i}/{tong}] {persona_id} đã chấm rồi -> bỏ qua")
            continue

        summary_path = SUMMARY_DIR / f"{persona_id}.json"
        if not summary_path.exists():
            print(f"[{i}/{tong}] {persona_id} chưa có file summary -> bỏ qua")
            thong_ke_bo_qua += 1
            continue

        persona = persona_index.get(persona_id)
        if persona is None:
            print(f"[{i}/{tong}] {persona_id} không tìm thấy trong profile -> bỏ qua")
            thong_ke_bo_qua += 1
            continue

        with open(summary_path, encoding="utf-8") as f:
            ket_qua_tom_tat = json.load(f)

        print(f"[{i}/{tong}] {persona_id} đang chấm...")
        cham = cham_1_ban_tom_tat(persona, ket_qua_tom_tat, client)

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
    print(f"KHÔNG ĐẠT: {thong_ke_khong_dat}")
    print(f"Bỏ qua: {thong_ke_bo_qua}")