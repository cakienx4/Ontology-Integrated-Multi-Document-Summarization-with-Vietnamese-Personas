import json
import sys
import asyncio
from pathlib import Path

from pipeline.utils import retry_generate_async, tao_oss_client_async, OSS_MODEL_NAME, OSS_MAX_CONCURRENCY
from pipeline.hanhchinh.hanh_chinh_extract import xu_ly_1_file

ROOT_DIR = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT_DIR / "data" / "profile_variants" / "state_profiles_nt_nn_tc_kn_cd_ch.json"

def lay_danh_sach_nganh(duong_dan_profile=PROFILE_PATH):
    with open(duong_dan_profile, "r", encoding="utf-8") as f:
        du_lieu = json.load(f)

    nganh_to_set = set()
    nganh_to_sang_nganh_nho = {}

    for persona in du_lieu:
        nganh_to = persona.get("nganh_to")
        nganh_nho = persona.get("nganh_nho")
        if not nganh_to:
            continue
        nganh_to_set.add(nganh_to)
        nganh_to_sang_nganh_nho.setdefault(nganh_to, set()).add(nganh_nho)

    # Chuyển set sang list để dễ đưa vào prompt
    nganh_to_sang_nganh_nho = {
        k: sorted(v) for k, v in nganh_to_sang_nganh_nho.items()
    }
    return sorted(nganh_to_set), nganh_to_sang_nganh_nho


def tao_prompt_khop_nganh_gop(danh_sach_doi_tuong, danh_sach_nganh_to, nganh_to_sang_nganh_nho, trich_yeu=None):
    danh_sach_nganh_text = ""
    for nganh_to in danh_sach_nganh_to:
        danh_sach_nho = nganh_to_sang_nganh_nho.get(nganh_to, [])
        danh_sach_nganh_text += f"- {nganh_to}: {', '.join(danh_sach_nho)}\n"

    danh_sach_doi_tuong_text = ""
    for i, doi_tuong in enumerate(danh_sach_doi_tuong):
        danh_sach_doi_tuong_text += f"{i}. \"{doi_tuong['text']}\"\n"

    boi_canh_text = ""
    if trich_yeu:
        boi_canh_text = f"""Ngữ cảnh chung: văn bản này có trích yếu (chủ đề) là:
"{trich_yeu}"
Hãy dùng ngữ cảnh này để khớp ngành chính xác hơn, đặc biệt khi câu đối 
tượng thi hành chỉ nêu chung chung (vd "các Sở, Ban, ngành") mà không 
nêu tên cơ quan cụ thể - trong trường hợp đó, chỉ chọn nganh_to/nganh_nho 
THỰC SỰ liên quan đến chủ đề trích yếu, không liệt kê tất cả.

"""

    prompt = f"""Bạn là trợ lý phân loại hành chính. Dưới đây là danh sách 
các câu mô tả đối tượng thi hành trích từ MỘT văn bản hành chính, mỗi 
câu đánh số thứ tự:

{boi_canh_text}{danh_sach_doi_tuong_text}

Danh sách ngành (nganh_to) và các ngành nhỏ (nganh_nho) tương ứng:
{danh_sach_nganh_text}

Nhiệm vụ: Với TỪNG câu theo đúng số thứ tự, xác định câu đó khớp với 
(những) nganh_to và nganh_nho nào trong danh sách trên. 

QUY TẮC BẮT BUỘC (đọc kỹ để phân biệt 2 tình huống khác nhau):

1. CÂU CHUNG CHUNG - không nêu tên cơ quan/chức danh cụ thể nào (vd 
   "các Sở, ban, ngành Thành phố", "các cơ quan, đơn vị", "Thủ trưởng 
   các đơn vị", "UBND các xã, phường"):
   - Nếu KHÔNG có ngữ cảnh chung (trích yếu) ở trên: BẮT BUỘC liệt kê 
     TẤT CẢ nganh_to có trong danh sách, do_tin_cay = "trung bình".
     TUYỆT ĐỐI KHÔNG được để nganh_to_khop rỗng trong trường hợp này - 
     câu chung chung nghĩa là áp dụng rộng, không phải không áp dụng.
   - Nếu CÓ ngữ cảnh chung (trích yếu): dùng nó để thu hẹp, chỉ chọn 
     ngành thực sự liên quan đến chủ đề.

2. CÂU NÊU TÊN CƠ QUAN/CHỨC DANH CỤ THỂ (vd "Sở Xây dựng", "Sở Quy 
   hoạch - Kiến trúc", "Giám đốc Sở Tài chính"):
   - Nếu có ngành trong danh sách khớp đúng bản chất: chọn ngành đó, do_tin_cay = "cao".
   - Nếu KHÔNG có ngành nào trong danh sách thực sự khớp đúng bản chất 
     (ví dụ "Sở Xây dựng" khi danh sách không có ngành xây dựng): 
     TUYỆT ĐỐI KHÔNG chọn đại ngành gần giống. Trả về nganh_to_khop 
     và nganh_nho_khop là mảng rỗng [], do_tin_cay là 
     "khong_co_nganh_phu_hop". Đây là trường hợp DUY NHẤT được phép để 
     trống - chỉ áp dụng khi câu nêu tên CƠ QUAN CỤ THỂ, KHÔNG áp dụng 
     cho câu chung chung ở mục 1.

3. Nếu câu chỉ nêu tên cơ quan với vai trò là ĐẦU MỐI NHẬN/TỔNG HỢP 
   BÁO CÁO (ví dụ "gửi báo cáo về Sở X để tổng hợp", "qua Sở X", "báo 
   cáo UBND Thành phố (qua Sở X)"), KHÔNG được coi đó là ngành của đối 
   tượng thi hành. Chỉ khớp ngành dựa trên đối tượng thi hành thực sự 
   (chủ thể phải thực hiện nhiệm vụ), bỏ qua ngành của cơ quan đầu mối 
   nhận báo cáo. Nếu sau khi bỏ cơ quan đầu mối, câu chỉ còn phần chung 
   chung, áp dụng quy tắc 1 (liệt kê hết).

   VÍ DỤ CỤ THỂ: câu "UBND Thành phố yêu cầu các sở, ngành, địa phương, 
   đơn vị nghiêm túc triển khai... nếu có khó khăn, vướng mắc, cơ quan, 
   đơn vị báo cáo UBND Thành phố (qua Sở Giáo dục và Đào tạo)" - chủ 
   thể phải thực hiện nhiệm vụ là "các sở, ngành, địa phương, đơn vị" 
   (chung chung), còn "Sở Giáo dục và Đào tạo" chỉ là nơi tổng hợp báo 
   cáo hộ UBND Thành phố, KHÔNG phải đối tượng thi hành chính của câu 
   này. Trường hợp này PHẢI áp dụng quy tắc 1 - liệt kê TẤT CẢ nganh_to, 
   TUYỆT ĐỐI KHÔNG chỉ chọn riêng "Giáo dục - Đào tạo".

4. Mỗi câu xử lý độc lập, không suy luận chéo giữa các câu.

Chỉ trả về JSON, không giải thích, không markdown, đúng định dạng sau 
(mảng có đúng số phần tử bằng số câu, đúng thứ tự). Ví dụ minh họa 3 
tình huống:
[
  {{
    "stt": 0,
    "nganh_to_khop": ["ten nganh to cu the"],
    "nganh_nho_khop": ["ten nganh nho cu the"],
    "do_tin_cay": "cao"
  }},
  {{
    "stt": 1,
    "nganh_to_khop": ["nganh 1", "nganh 2", "... liệt kê hết tất cả nganh_to"],
    "nganh_nho_khop": [],
    "do_tin_cay": "trung bình"
  }},
  {{
    "stt": 2,
    "nganh_to_khop": [],
    "nganh_nho_khop": [],
    "do_tin_cay": "khong_co_nganh_phu_hop"
  }}
]"""
    return prompt


async def goi_llm_khop_nganh_gop(client, semaphore, danh_sach_doi_tuong, danh_sach_nganh_to, nganh_to_sang_nganh_nho, trich_yeu=None, model_name: str = OSS_MODEL_NAME):
    if not danh_sach_doi_tuong:
        return []

    prompt = tao_prompt_khop_nganh_gop(
        danh_sach_doi_tuong, danh_sach_nganh_to, nganh_to_sang_nganh_nho, trich_yeu=trich_yeu
    )

    async def _call():
        return await client.models.generate_content(
            model=model_name,
            contents=prompt,
            config={
                "temperature": 0.0,
                "response_mime_type": "application/json",
            },
        )

    async with semaphore:
        response = await retry_generate_async(_call)
    text_tra_ve = response.text.strip()

    try:
        ket_qua_list = json.loads(text_tra_ve)
    except json.JSONDecodeError:
        print("LỖI PARSE JSON khi khớp ngành gộp cho văn bản")
        print(f"Text trả về: {text_tra_ve}")
        ket_qua_list = [
            {"stt": i, "nganh_to_khop": [], "nganh_nho_khop": [], "do_tin_cay": "thap"}
            for i in range(len(danh_sach_doi_tuong))
        ]

    if len(ket_qua_list) != len(danh_sach_doi_tuong):
        print(f"CẢNH BÁO: số kết quả ({len(ket_qua_list)}) không khớp "
              f"số đối tượng thi hành đầu vào ({len(danh_sach_doi_tuong)})")

    return ket_qua_list

async def chay_khop_persona_cho_van_ban(client, semaphore, ket_qua_extract, duong_dan_profile=PROFILE_PATH):
    danh_sach_doi_tuong_goc = ket_qua_extract.get("doi_tuong_thi_hanh", [])

    trich_yeu = None
    danh_sach_doi_tuong = []
    chi_so_goc_theo_vi_tri_loc = []
    for chi_so_goc, dt in enumerate(danh_sach_doi_tuong_goc):
        if dt.get("nguon") == "trich_yeu":
            trich_yeu = dt.get("text")
        else:
            danh_sach_doi_tuong.append(dt)
            chi_so_goc_theo_vi_tri_loc.append(chi_so_goc)

    if trich_yeu is None:
        print("CẢNH BÁO: không trích được trích yếu/tên văn bản làm ngữ cảnh "
              "chung - các câu đối tượng thi hành chung chung sẽ bị liệt kê "
              "TẤT CẢ nganh_to, độ chính xác khớp ngành sẽ thấp cho văn bản này.")

    danh_sach_nganh_to, nganh_to_sang_nganh_nho = lay_danh_sach_nganh(duong_dan_profile)

    ket_qua_khop_list = await goi_llm_khop_nganh_gop(
        client, semaphore, danh_sach_doi_tuong, danh_sach_nganh_to, nganh_to_sang_nganh_nho,
        trich_yeu=trich_yeu
    )

    ket_qua_cuoi_cung = []
    for i, doi_tuong in enumerate(danh_sach_doi_tuong):
        if i < len(ket_qua_khop_list):
            ket_qua_khop = ket_qua_khop_list[i]
        else:
            ket_qua_khop = {"nganh_to_khop": [], "nganh_nho_khop": [], "do_tin_cay": "thap"}

        danh_sach_id_khop, danh_sach_id_khop_ca_nganh_nho = loc_persona_theo_ket_qua_khop(
            ket_qua_khop, duong_dan_profile
        )

        ket_qua_cuoi_cung.append({
            "nguon": doi_tuong.get("nguon"),
            "text": doi_tuong.get("text"),
            "chi_so_doi_tuong_goc": chi_so_goc_theo_vi_tri_loc[i],
            "nganh_to_khop": ket_qua_khop.get("nganh_to_khop", []),
            "nganh_nho_khop": ket_qua_khop.get("nganh_nho_khop", []),
            "do_tin_cay": ket_qua_khop.get("do_tin_cay", "thap"),
            "danh_sach_persona_id_khop": danh_sach_id_khop,
            "danh_sach_persona_id_khop_ca_nganh_nho": danh_sach_id_khop_ca_nganh_nho,
        })

    return ket_qua_cuoi_cung


def loc_persona_theo_ket_qua_khop(ket_qua_khop, duong_dan_profile=PROFILE_PATH):
    with open(duong_dan_profile, "r", encoding="utf-8") as f:
        du_lieu = json.load(f)

    nganh_to_khop = set(ket_qua_khop.get("nganh_to_khop", []))
    nganh_nho_khop = set(ket_qua_khop.get("nganh_nho_khop", []))

    danh_sach_id_khop = []
    danh_sach_id_khop_ca_nganh_nho = []
    for persona in du_lieu:
        if persona.get("nganh_to") in nganh_to_khop:
            danh_sach_id_khop.append(persona.get("id"))
            # đánh dấu riêng những persona khớp CẢ nganh_nho cụ thể,
            # dùng để tăng độ tin cậy, không dùng để loại bớt id ở trên
            if nganh_nho_khop and persona.get("nganh_nho") in nganh_nho_khop:
                danh_sach_id_khop_ca_nganh_nho.append(persona.get("id"))

    return danh_sach_id_khop, danh_sach_id_khop_ca_nganh_nho

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Cách dùng: python -m pipeline.hanhchinh.hanh_chinh_persona_match <đường_dẫn_file_docx>")
        sys.exit(1)

    duong_dan = Path(sys.argv[1])

    if not duong_dan.exists():
        duong_dan = ROOT_DIR / "data" / "hanh_chinh" / duong_dan

    print(f"Đang trích xuất văn bản hành chính từ: {duong_dan}")
    ket_qua_extract = xu_ly_1_file(str(duong_dan))

    print(f"Loại văn bản: {ket_qua_extract.get('loai_van_ban')}")
    print(f"Số lượng đối tượng thi hành: {len(ket_qua_extract.get('doi_tuong_thi_hanh', []))}")
    print("Đang gọi LLM khớp persona theo ngành...")

    async def chay():
        client = tao_oss_client_async()
        semaphore = asyncio.Semaphore(OSS_MAX_CONCURRENCY)
        return await chay_khop_persona_cho_van_ban(client, semaphore, ket_qua_extract)

    ket_qua_khop = asyncio.run(chay())

    print("\n===== KẾT QUẢ KHỚP PERSONA =====")
    for item in ket_qua_khop:
        print(f"\nNguồn: {item['nguon']}")
        print(f"Text: {item['text']}")
        print(f"Nganh_to khớp: {item['nganh_to_khop']}")
        print(f"Nganh_nho khớp: {item['nganh_nho_khop']}")
        print(f"Độ tin cậy: {item['do_tin_cay']}")
        print(f"Số persona khớp: {len(item['danh_sach_persona_id_khop'])}")

    ten_file_json = ROOT_DIR / "output" / "hanh_chinh" / "persona_match" / f"{duong_dan.stem}.json"
    ten_file_json.parent.mkdir(parents=True, exist_ok=True)
    with open(ten_file_json, "w", encoding="utf-8") as f:
        json.dump(ket_qua_khop, f, ensure_ascii=False, indent=2)

    print(f"\nĐã lưu kết quả JSON tại: {ten_file_json}")