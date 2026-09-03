import json
import argparse
import os
import asyncio
from pathlib import Path

from pipeline.utils import retry_generate_async, OSS_MODEL_NAME, tao_oss_client_async, OSS_MAX_CONCURRENCY

ROOT_DIR = Path(__file__).resolve().parents[2]

DUONG_DAN_INPUT_MAC_DINH = "output/chinh_luan/extracted/chinh_luan_da_tach_doan.json"
DUONG_DAN_OUTPUT_MAC_DINH = "output/chinh_luan/phan_tich_lap_luan/chinh_luan_da_phan_tich.json"

PROMPT_PHAN_TICH = """Bạn là chuyên gia phân tích lập luận văn bản chính luận tiếng Việt.

Dưới đây là một bài {loai_chinh_luan_hien_thi} đã được đánh số theo đoạn:

{noi_dung_da_danh_so}

Nhiệm vụ: phân tích cấu trúc lập luận của bài viết theo đúng trình tự Vấn đề -> Luận điểm -> Luận cứ -> Kết luận.
Yêu cầu:
- KHÔNG diễn giải lại nội dung, chỉ trích xuất và tóm lược ngắn gọn từng phần dựa trên văn bản gốc.
- LIỆT KÊ ĐẦY ĐỦ mọi luận điểm có trong bài, KHÔNG được tự đánh giá luận điểm nào quan trọng hơn
  hay có thể lược bỏ - việc này KHÔNG thuộc phạm vi phân tích này.
- Trường "luan_cu_lien_quan" ghi rõ luận điểm đó được chứng minh ở đoạn nào, dùng đúng định dạng "ĐOẠN N".
- Trường "quan_he" CHỈ được gán "nhan_qua", "phan_bien", hoặc "bo_sung" khi văn bản gốc CÓ từ nối hoặc
  cụm từ liên kết tường minh thể hiện quan hệ đó (ví dụ: "vì vậy", "do đó", "tuy nhiên", "trái lại",
  "bên cạnh đó", "ngoài ra", "không chỉ... mà còn"...). TUYỆT ĐỐI KHÔNG gán quan hệ chỉ vì 2 luận điểm
  đứng gần nhau hoặc cùng thuộc một chủ đề chung - nếu không có liên kết ngôn ngữ rõ ràng, PHẢI để "quan_he": null.
  Nhiều bài chính luận liệt kê song song nhiều lĩnh vực hợp tác/vấn đề độc lập với nhau - đây là trường hợp
  BÌNH THƯỜNG và PHẢI để null, không phải lỗi thiếu sót.
- Nếu "quan_he" khác null, trường "quan_he_voi_luan_diem_so" PHẢI ghi rõ số thứ tự (bắt đầu từ 1)
  của luận điểm trong "danh_sach_luan_diem" mà nó có quan hệ - không được để trống nếu quan_he khác null.
- "ket_luan_va_loi_keu_goi" phải giữ đúng tinh thần và lập trường gốc của tác giả, không được suy diễn thêm.

Chỉ trả về JSON theo đúng cấu trúc sau, không thêm chữ nào khác ngoài JSON:
{{
  "van_de": "...",
  "danh_sach_luan_diem": [
    {{
      "luan_diem": "...",
      "luan_cu_lien_quan": ["ĐOẠN 2", "ĐOẠN 3"],
      "quan_he": null,
      "quan_he_voi_luan_diem_so": null
    }}
  ],
  "ket_luan_va_loi_keu_goi": "..."
}}
"""

LOAI_CHINH_LUAN_HIEN_THI = {
    "xa_luan": "xã luận",
    "binh_luan_phe_phan": "bình luận - phê phán",
    "khac": "chính luận",
}


async def goi_llm_phan_tich_async(client, semaphore, bai_da_tach_doan: dict, model: str = OSS_MODEL_NAME) -> dict:
    noi_dung_da_danh_so = bai_da_tach_doan.get("noi_dung_da_danh_so", "")
    if not noi_dung_da_danh_so.strip():
        print(f"Bài {bai_da_tach_doan.get('id')} không có nội dung đã đánh số, bỏ qua.")
        return {}

    loai = bai_da_tach_doan.get("loai_chinh_luan", "khac")
    prompt = PROMPT_PHAN_TICH.format(
        loai_chinh_luan_hien_thi=LOAI_CHINH_LUAN_HIEN_THI.get(loai, "chính luận"),
        noi_dung_da_danh_so=noi_dung_da_danh_so,
    )

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
        print(f"Bài {bai_da_tach_doan.get('id')}: LLM trả về JSON không hợp lệ, cần kiểm tra thủ công.")
        return {"loi_parse": True, "raw_text": raw}


async def xu_ly_mot_bai(client, semaphore, bai, model):
    phan_tich = await goi_llm_phan_tich_async(client, semaphore, bai, model=model)
    bai_moi = dict(bai)
    bai_moi["phan_tich_lap_luan"] = phan_tich
    so_luan_diem = len(phan_tich.get("danh_sach_luan_diem", []))
    print(f"Đã phân tích bài {bai.get('id')} — {so_luan_diem} luận điểm.")
    return bai_moi


async def xu_ly_toan_bo_file_async(duong_dan_input: str, duong_dan_output: str, id_loc: str = None, model: str = OSS_MODEL_NAME):
    with open(duong_dan_input, "r", encoding="utf-8") as f:
        danh_sach_bai = json.load(f)

    if id_loc:
        danh_sach_bai = [b for b in danh_sach_bai if b.get("id") == id_loc]

    if id_loc and not danh_sach_bai:
        print(f"Không tìm thấy bài có id = {id_loc}.")
        return

    client = tao_oss_client_async()
    semaphore = asyncio.Semaphore(OSS_MAX_CONCURRENCY)

    tasks = [xu_ly_mot_bai(client, semaphore, bai, model) for bai in danh_sach_bai]
    ket_qua = await asyncio.gather(*tasks)

    os.makedirs(os.path.dirname(duong_dan_output), exist_ok=True)
    with open(duong_dan_output, "w", encoding="utf-8") as f:
        json.dump(ket_qua, f, ensure_ascii=False, indent=2)

    print(f"Đã ghi {len(ket_qua)} bài đã phân tích lập luận vào: {duong_dan_output}")


def main():
    parser = argparse.ArgumentParser(description="Phân tích cấu trúc lập luận bài chính luận")
    parser.add_argument("--input", default=DUONG_DAN_INPUT_MAC_DINH)
    parser.add_argument("--output", default=DUONG_DAN_OUTPUT_MAC_DINH)
    parser.add_argument("--id", default=None, help="Chỉ xử lý 1 bài theo id (để test nhanh)")
    parser.add_argument("--model", default=OSS_MODEL_NAME)
    args = parser.parse_args()

    asyncio.run(xu_ly_toan_bo_file_async(args.input, args.output, args.id, args.model))


if __name__ == "__main__":
    main()