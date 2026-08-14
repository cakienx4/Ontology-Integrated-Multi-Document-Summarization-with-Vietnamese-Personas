"""
Khung đánh giá gồm 7 tiêu chí:
1. Giữ đúng lập trường, không suy diễn/thiên lệch
2. Dùng đúng trình tự: Vấn đề -> Luận điểm -> Luận cứ -> Kết luận
3. Đầy đủ luận điểm cốt lõi, không bỏ sót thông điệp chính
4. Bảo toàn mối quan hệ lập luận
5. Giữ tính thuyết phục
6. Cá nhân hóa đúng cách - trọng tâm/chi tiết/diễn đạt + mức độ chuyên môn
7. Mạch lạc, tự nhiên
"""

import json
import argparse
import asyncio
from pathlib import Path

from pipeline.utils import retry_generate_async, OSS_MODEL_NAME, tao_oss_client_async, OSS_MAX_CONCURRENCY
from pipeline.chinhluan.chinh_luan_personalize import _dinh_dang_danh_sach_luan_diem

ROOT_DIR = Path(__file__).resolve().parents[2]

DUONG_DAN_BAI_MAC_DINH = "output/chinh_luan/phan_tich_lap_luan/tung_bai"
DUONG_DAN_SUMMARY_MAC_DINH = "output/chinh_luan/summary"
DUONG_DAN_OUTPUT_MAC_DINH = "output/chinh_luan/eval"

TEN_TIEU_CHI = {
    1: "Giữ đúng lập trường, không suy diễn/thiên lệch",
    2: "Đúng trình tự Vấn đề -> Luận điểm -> Luận cứ -> Kết luận",
    3: "Đầy đủ luận điểm cốt lõi, không bỏ sót thông điệp chính",
    4: "Bảo toàn quan hệ lập luận",
    5: "Giữ tính thuyết phục",
    6: "Cá nhân hóa đúng cách (trọng tâm/chi tiết/diễn đạt + mức chuyên môn)",
    7: "Mạch lạc, tự nhiên",
}

PROMPT_DANH_GIA = """Bạn là chuyên gia thẩm định văn bản chính luận tiếng Việt, được giao nhiệm vụ
đánh giá 1 bản tóm tắt cá nhân hóa so với bài chính luận gốc.

BÀI GỐC (đã đánh số theo đoạn):
{noi_dung_da_danh_so}

CẤU TRÚC LẬP LUẬN ĐÃ PHÂN TÍCH SẴN TỪ BÀI GỐC (dùng làm căn cứ đối chiếu):
Vấn đề: {van_de}

Danh sách luận điểm (đánh số để đối chiếu):
{danh_sach_luan_diem_text}

Kết luận và lời kêu gọi gốc: {ket_luan_va_loi_keu_goi}

BẢN TÓM TẮT ĐÃ CÁ NHÂN HÓA (persona có văn phong "{style}", định dạng {dinh_dang_hien_thi}):
{ban_tom_tat}

NHIỆM VỤ: đánh giá bản tóm tắt theo đúng 7 tiêu chí dưới đây. Với MỖI tiêu chí, PHẢI trích
dẫn bằng chứng cụ thể (ngắn gọn) từ CẢ bài gốc lẫn bản tóm tắt để chứng minh nhận định -
KHÔNG được kết luận "đạt"/"không đạt" mà không có bằng chứng kèm theo.

Tiêu chí 1 - Giữ đúng lập trường, không suy diễn/thiên lệch: bản tóm tắt có giữ đúng quan
điểm, thái độ của tác giả đối với vấn đề không? Có câu/ý nào bị AI thêm vào (không có căn cứ
trong bài gốc), hoặc bị trung lập hóa/đảo ngược so với lập trường gốc không?

Tiêu chí 2 - Đúng trình tự lập luận: bản tóm tắt có thể hiện rõ mạch Vấn đề -> Luận điểm ->
Luận cứ -> Kết luận (dù ở định dạng đầy đủ hay vào thẳng vấn đề) không, hay bị đảo lộn/rời rạc?

Tiêu chí 3 - Đầy đủ luận điểm: BẮT BUỘC liệt kê lại TỪNG luận điểm trong danh sách ở trên
(theo đúng số thứ tự), với mỗi luận điểm ghi rõ có xuất hiện trong bản tóm tắt hay không
(dù chỉ ở mức rút gọn) và trích câu/cụm trong bản tóm tắt thể hiện luận điểm đó (nếu có).

Tiêu chí 4 - Bảo toàn quan hệ lập luận: với MỖI luận điểm có ghi "quan_he" khác null ở trên,
kiểm tra bản tóm tắt có dùng từ nối/cấu trúc câu thể hiện đúng quan hệ đó (nhân quả/phản
biện/bổ sung) với luận điểm liên quan hay không, hay viết thành 2 ý rời rạc không liên kết.

Tiêu chí 5 - Giữ tính thuyết phục: bản tóm tắt có còn giữ được sức thuyết phục của bài gốc
không (dẫn chứng, lý lẽ nối tiếp chặt chẽ), hay đã biến thành liệt kê sự kiện khô khan?

Tiêu chí 6 - Cá nhân hóa đúng cách: việc điều chỉnh trọng tâm/độ chi tiết/cách diễn đạt có
hợp lý với văn phong "{style}" không? Nếu văn phong yêu cầu giải thích thuật ngữ (style
"khong_chuyen_mon" hoặc "binh_thuong"), MỌI thuật ngữ chính trị/hành chính/pháp lý/đối ngoại/
tên viết tắt tổ chức xuất hiện trong bản tóm tắt đã có giải thích ngay trong câu chưa?

Tiêu chí 7 - Mạch lạc, tự nhiên: văn phong có trôi chảy, không bị liệt kê máy móc, không còn
dấu vết định dạng thô (như "Luận điểm 1:", "ĐOẠN N", gạch đầu dòng) không?

Chỉ trả về JSON theo đúng cấu trúc sau, không thêm chữ nào khác ngoài JSON:
{{
  "tieu_chi_1": {{"dat": true, "bang_chung_bai_goc": "...", "bang_chung_ban_tom_tat": "...", "ly_do_neu_khong_dat": null}},
  "tieu_chi_2": {{"dat": true, "bang_chung_bai_goc": "...", "bang_chung_ban_tom_tat": "...", "ly_do_neu_khong_dat": null}},
  "tieu_chi_3": {{
    "dat": true,
    "kiem_tra_tung_luan_diem": [
      {{"so_thu_tu": 1, "co_xuat_hien": true, "bang_chung_ban_tom_tat": "..."}}
    ],
    "ly_do_neu_khong_dat": null
  }},
  "tieu_chi_4": {{
    "dat": true,
    "kiem_tra_tung_quan_he": [
      {{"luan_diem_so": 2, "quan_he": "nhan_qua", "co_the_hien": true, "bang_chung_ban_tom_tat": "..."}}
    ],
    "ly_do_neu_khong_dat": null
  }},
  "tieu_chi_5": {{"dat": true, "bang_chung_bai_goc": "...", "bang_chung_ban_tom_tat": "...", "ly_do_neu_khong_dat": null}},
  "tieu_chi_6": {{"dat": true, "bang_chung_ban_tom_tat": "...", "ly_do_neu_khong_dat": null}},
  "tieu_chi_7": {{"bang_chung_ban_tom_tat": "...", "dat": true, "ly_do_neu_khong_dat": null}}
}}
"""


def _lay_dinh_dang_hien_thi(day_du: bool) -> str:
    return "đầy đủ (tiêu đề + mở-thân-kết)" if day_du else "vào thẳng vấn đề"


def build_prompt_danh_gia(bai: dict, ket_qua_ca_nhan_hoa: dict) -> str:
    phan_tich = bai.get("phan_tich_lap_luan", {})
    danh_sach_luan_diem_text = _dinh_dang_danh_sach_luan_diem(phan_tich)

    return PROMPT_DANH_GIA.format(
        noi_dung_da_danh_so=bai.get("noi_dung_da_danh_so", ""),
        van_de=phan_tich.get("van_de", ""),
        danh_sach_luan_diem_text=danh_sach_luan_diem_text,
        ket_luan_va_loi_keu_goi=phan_tich.get("ket_luan_va_loi_keu_goi", ""),
        style=ket_qua_ca_nhan_hoa.get("style", ""),
        dinh_dang_hien_thi=_lay_dinh_dang_hien_thi(ket_qua_ca_nhan_hoa.get("day_du", False)),
        ban_tom_tat=ket_qua_ca_nhan_hoa.get("summary", ""),
    ).strip()


async def goi_llm_danh_gia(client, semaphore, bai: dict, ket_qua_ca_nhan_hoa: dict, model: str = OSS_MODEL_NAME) -> dict:
    prompt = build_prompt_danh_gia(bai, ket_qua_ca_nhan_hoa)

    async def _call():
        return await client.models.generate_content(
            model=model,
            contents=prompt,
            config={
                "temperature": 0.0,
                "response_mime_type": "application/json",
            },
        )

    async with semaphore:
        response = await retry_generate_async(_call)
    raw = response.text.strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print(f"Bài {bai.get('id')} — persona {ket_qua_ca_nhan_hoa.get('id')}: LLM trả về JSON không hợp lệ, cần kiểm tra thủ công.")
        return {"loi_parse": True, "raw_text": raw}


# ==== HẬU KIỂM: Đối chiếu với can_soat_tay từ bước personalize ====
# CHỈ để báo hiệu thêm, KHÔNG tự động đảo ngược verdict của judge - dùng nguyên tắc "hau_kiem_fail_reasons".

def hau_kiem(danh_gia: dict, ket_qua_ca_nhan_hoa: dict, so_luan_diem_goc: int) -> list:
    ly_do_can_soat_tay = []

    if danh_gia.get("loi_parse"):
        return ["LLM judge trả về JSON không hợp lệ, không đánh giá được."]

    tieu_chi_3 = danh_gia.get("tieu_chi_3", {})
    kiem_tra_luan_diem = tieu_chi_3.get("kiem_tra_tung_luan_diem", [])
    if len(kiem_tra_luan_diem) != so_luan_diem_goc:
        ly_do_can_soat_tay.append(
            f"Judge chỉ kiểm tra {len(kiem_tra_luan_diem)}/{so_luan_diem_goc} luận điểm gốc "
            f"- có thể đã bỏ sót khi đối chiếu."
        )

    luan_diem_nghi_thieu_tu_personalize = ket_qua_ca_nhan_hoa.get("luan_diem_nghi_thieu", [])
    if luan_diem_nghi_thieu_tu_personalize and tieu_chi_3.get("dat"):
        ly_do_can_soat_tay.append(
            f"Bước personalize đã nghi thiếu luận điểm số {luan_diem_nghi_thieu_tu_personalize} "
            f"(hậu kiểm lexical), nhưng judge lại chấm tiêu chí 3 là đạt - cần rà tay đối chiếu."
        )

    acronym_nghi_thieu_tu_personalize = ket_qua_ca_nhan_hoa.get("acronym_nghi_thieu", [])
    tieu_chi_6 = danh_gia.get("tieu_chi_6", {})
    if acronym_nghi_thieu_tu_personalize and tieu_chi_6.get("dat"):
        ly_do_can_soat_tay.append(
            f"Bước personalize đã nghi các từ viết tắt {acronym_nghi_thieu_tu_personalize} chưa "
            f"giải thích, nhưng judge lại chấm tiêu chí 6 là đạt - cần rà tay đối chiếu."
        )

    return ly_do_can_soat_tay


def tinh_ket_qua_chung(danh_gia: dict) -> bool:
    if danh_gia.get("loi_parse"):
        return False
    return all(
        danh_gia.get(f"tieu_chi_{i}", {}).get("dat") is True
        for i in range(1, 8)
    )

# ==== CLI ====

async def chay_danh_gia(client, semaphore, bai_id: str, persona_id: str, duong_dan_bai: str,
                        duong_dan_summary: str, duong_dan_output: str, model: str = OSS_MODEL_NAME):
    duong_dan_bai_dir = ROOT_DIR / duong_dan_bai if not Path(duong_dan_bai).is_absolute() else Path(duong_dan_bai)
    duong_dan_bai_file = duong_dan_bai_dir / f"{bai_id}.json"
    if not duong_dan_bai_file.exists():
        raise SystemExit(f"Không tìm thấy file phân tích lập luận tại {duong_dan_bai_file}")
    with open(duong_dan_bai_file, encoding="utf-8") as f:
        bai = json.load(f)

    duong_dan_summary_file = ROOT_DIR / duong_dan_summary / bai_id / f"{persona_id}.json"
    if not duong_dan_summary_file.exists():
        raise SystemExit(f"Không tìm thấy bản tóm tắt tại {duong_dan_summary_file}")
    with open(duong_dan_summary_file, encoding="utf-8") as f:
        ket_qua_ca_nhan_hoa = json.load(f)

    if ket_qua_ca_nhan_hoa.get("loi"):
        raise SystemExit(f"Bản tóm tắt {duong_dan_summary_file} bị lỗi từ bước personalize: {ket_qua_ca_nhan_hoa['loi']}")

    danh_gia = await goi_llm_danh_gia(client, semaphore, bai, ket_qua_ca_nhan_hoa, model=model)

    so_luan_diem_goc = len(bai.get("phan_tich_lap_luan", {}).get("danh_sach_luan_diem", []))
    ly_do_can_soat_tay = hau_kiem(danh_gia, ket_qua_ca_nhan_hoa, so_luan_diem_goc)
    dat_tat_ca = tinh_ket_qua_chung(danh_gia)

    ket_qua = {
        "bai_id": bai_id,
        "persona_id": persona_id,
        "dat_tat_ca_7_tieu_chi": dat_tat_ca,
        "can_soat_tay": bool(ly_do_can_soat_tay),
        "ly_do_can_soat_tay": ly_do_can_soat_tay,
        "danh_gia_chi_tiet": danh_gia,
    }

    duong_dan_out = ROOT_DIR / duong_dan_output / bai_id
    duong_dan_out.mkdir(parents=True, exist_ok=True)
    out_file = duong_dan_out / f"{persona_id}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(ket_qua, f, ensure_ascii=False, indent=2)

    ket_qua_hien_thi = "ĐẠT" if dat_tat_ca else "CHƯA ĐẠT"
    print(f"Bài {bai_id} — persona {persona_id}: {ket_qua_hien_thi}")
    if ly_do_can_soat_tay:
        print("Cần rà tay:")
        for ly_do in ly_do_can_soat_tay:
            print(f"  - {ly_do}")
    for i in range(1, 8):
        tc = danh_gia.get(f"tieu_chi_{i}", {})
        trang_thai = "✓" if tc.get("dat") else "✗"
        print(f"  {trang_thai} Tiêu chí {i}: {TEN_TIEU_CHI[i]}")
    print(f"Đã ghi: {out_file}")

async def _chay_danh_gia_1_persona(client, semaphore, bai_id, persona_id, duong_dan_bai,
                                   duong_dan_summary, duong_dan_output, model, i, tong, out_file, bo_qua_da_co):
    if bo_qua_da_co and out_file.exists():
        print(f"[{i}/{tong}] {persona_id} đã có kết quả đánh giá -> bỏ qua")
        return

    print(f"\n[{i}/{tong}] Đang đánh giá persona {persona_id}...")
    try:
        await chay_danh_gia(client, semaphore, bai_id, persona_id, duong_dan_bai,
                            duong_dan_summary, duong_dan_output, model)
    except SystemExit as loi:
        print(f"Bỏ qua {persona_id} do lỗi: {loi}")


async def chay_danh_gia_toan_bo_bai(client, semaphore, bai_id: str, duong_dan_bai: str, duong_dan_summary: str,
                                    duong_dan_output: str, model: str = OSS_MODEL_NAME,
                                    bo_qua_da_co: bool = True):
    duong_dan_summary_dir = ROOT_DIR / duong_dan_summary / bai_id
    if not duong_dan_summary_dir.exists():
        raise SystemExit(f"Không tìm thấy thư mục tóm tắt {duong_dan_summary_dir}")

    file_summary_list = sorted(duong_dan_summary_dir.glob("*.json"))
    if not file_summary_list:
        raise SystemExit(f"Không có file tóm tắt nào trong {duong_dan_summary_dir}")

    duong_dan_out_dir = ROOT_DIR / duong_dan_output / bai_id
    duong_dan_out_dir.mkdir(parents=True, exist_ok=True)

    tong = len(file_summary_list)
    tasks = []
    for i, file_summary in enumerate(file_summary_list, start=1):
        persona_id = file_summary.stem
        out_file = duong_dan_out_dir / f"{persona_id}.json"
        tasks.append(_chay_danh_gia_1_persona(
            client, semaphore, bai_id, persona_id, duong_dan_bai, duong_dan_summary,
            duong_dan_output, model, i, tong, out_file, bo_qua_da_co,
        ))

    await asyncio.gather(*tasks)

def main():
    parser = argparse.ArgumentParser(description="Đánh giá bản tóm tắt cá nhân hóa chính luận theo 7 tiêu chí")
    parser.add_argument("--bai-id", required=True, help="id bài chính luận, ví dụ CL0075")
    parser.add_argument(
        "--persona-id", default=None,
        help="..."
    )
    parser.add_argument("--bai-input", default=DUONG_DAN_BAI_MAC_DINH)
    parser.add_argument("--summary-input", default=DUONG_DAN_SUMMARY_MAC_DINH)
    parser.add_argument("--output-dir", default=DUONG_DAN_OUTPUT_MAC_DINH)
    parser.add_argument("--model", default=OSS_MODEL_NAME)
    parser.add_argument("--variant", type=str, default=None, help="ten bien the persona")
    args = parser.parse_args()

    if args.variant:
        args.summary_input = f"{args.summary_input}/{args.variant}"
        args.output_dir = f"{args.output_dir}/{args.variant}"

    async def chay():
        client = tao_oss_client_async()
        semaphore = asyncio.Semaphore(OSS_MAX_CONCURRENCY)

        if args.persona_id:
            await chay_danh_gia(
                client, semaphore, args.bai_id, args.persona_id,
                args.bai_input, args.summary_input, args.output_dir,
                args.model,
            )
        else:
            await chay_danh_gia_toan_bo_bai(
                client, semaphore, args.bai_id,
                args.bai_input, args.summary_input, args.output_dir,
                args.model,
            )

    asyncio.run(chay())

if __name__ == "__main__":
    main()