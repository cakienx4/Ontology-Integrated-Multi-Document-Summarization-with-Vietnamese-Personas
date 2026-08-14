import json
import json
import argparse
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]

DUONG_DAN_INPUT_MAC_DINH = str(ROOT_DIR / "data" / "chinh_luan" / "nhandan_chinhluan.json")
DUONG_DAN_OUTPUT_MAC_DINH = str(ROOT_DIR / "output" / "chinh_luan" / "extracted" / "chinh_luan_da_tach_doan.json")


def xac_dinh_loai_chinh_luan(category_slug: str, category_name: str) -> str:
    slug = (category_slug or "").lower()
    ten = (category_name or "").lower()

    if "xa-luan" in slug or "xã luận" in ten or "xa luan" in ten:
        return "xa_luan"
    if "binh-luan" in slug or "bình luận" in ten or "binh luan" in ten:
        return "binh_luan_phe_phan"
    return "khac"


def la_dong_ky_ten_nguon(dong: str) -> bool:
    dong_sach = dong.strip()
    if not dong_sach:
        return False
    if len(dong_sach.split()) > 4:
        return False
    if dong_sach[-1] in ".!?":
        return False
    if dong_sach != dong_sach.upper():
        return False
    return True


def tach_doan_van(noi_dung: str):
    if not noi_dung:
        return [], None

    dong_list = [d.strip() for d in noi_dung.split("\n") if d.strip()]
    if not dong_list:
        return [], None

    nguon_ky_ten = None
    if la_dong_ky_ten_nguon(dong_list[-1]):
        nguon_ky_ten = dong_list[-1]
        dong_list = dong_list[:-1]

    return dong_list, nguon_ky_ten


def dinh_dang_doan_van(doan_list: list) -> str:
    khoi_text = []
    for idx, doan in enumerate(doan_list, start=1):
        khoi_text.append(f"[ĐOẠN {idx}] {doan}")
    return "\n\n".join(khoi_text)


def xu_ly_mot_bai(bai_goc: dict) -> dict:
    noi_dung_goc = bai_goc.get("content") or bai_goc.get("summary") or ""
    doan_list, nguon_ky_ten = tach_doan_van(noi_dung_goc)

    return {
        "id": bai_goc.get("id"),
        "category_slug": bai_goc.get("category_slug"),
        "category_name": bai_goc.get("category_name"),
        "loai_chinh_luan": xac_dinh_loai_chinh_luan(
            bai_goc.get("category_slug"), bai_goc.get("category_name")
        ),
        "title": bai_goc.get("title"),
        "summary": bai_goc.get("summary"),
        "link": bai_goc.get("link"),
        "nguon_ky_ten": nguon_ky_ten,
        "so_doan": len(doan_list),
        "danh_sach_doan": doan_list,
        "noi_dung_da_danh_so": dinh_dang_doan_van(doan_list),
    }


def doc_va_xu_ly_file(duong_dan_input: str, duong_dan_output: str, id_loc: str = None):
    with open(duong_dan_input, "r", encoding="utf-8") as f:
        danh_sach_bai_goc = json.load(f)

    ket_qua = []
    for bai_goc in danh_sach_bai_goc:
        if id_loc and bai_goc.get("id") != id_loc:
            continue
        bai_da_xu_ly = xu_ly_mot_bai(bai_goc)
        ket_qua.append(bai_da_xu_ly)
        print(f"Đã xử lý bài {bai_da_xu_ly['id']} — loại: {bai_da_xu_ly['loai_chinh_luan']} — số đoạn: {bai_da_xu_ly['so_doan']}")

    if id_loc and not ket_qua:
        print(f"Không tìm thấy bài có id = {id_loc} trong file input.")
        return

    os.makedirs(os.path.dirname(duong_dan_output), exist_ok=True)
    with open(duong_dan_output, "w", encoding="utf-8") as f:
        json.dump(ket_qua, f, ensure_ascii=False, indent=2)

    print(f"Đã ghi {len(ket_qua)} bài chính luận đã tách đoạn vào: {duong_dan_output}")


def main():
    parser = argparse.ArgumentParser(description="Tách đoạn văn bản chính luận từ file JSON crawl RSS nhandan.vn")
    parser.add_argument("--input", default=DUONG_DAN_INPUT_MAC_DINH, help="Đường dẫn file JSON gốc")
    parser.add_argument("--output", default=DUONG_DAN_OUTPUT_MAC_DINH, help="Đường dẫn file JSON output")
    parser.add_argument("--id", default=None, help="Chỉ xử lý 1 bài theo id (để test nhanh)")
    args = parser.parse_args()

    doc_va_xu_ly_file(args.input, args.output, args.id)


if __name__ == "__main__":
    main()