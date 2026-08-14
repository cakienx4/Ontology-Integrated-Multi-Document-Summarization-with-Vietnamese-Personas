import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = ROOT_DIR / "output" / "dataset"

NHANH_HOP_LE = {"bao_chi", "hanh_chinh", "chinh_luan"}
FIELD_BAT_BUOC = {"id", "nhanh", "persona_id", "nguon_goc", "messages"}
ROLE_DUNG_THU_TU = ["system", "user", "assistant"]


def kiem_tra_1_dong(so_dong, dong_raw):
    loi = []
    try:
        sample = json.loads(dong_raw)
    except json.JSONDecodeError as e:
        return [f"Dòng {so_dong}: JSON không hợp lệ - {e}"], None

    thieu_field = FIELD_BAT_BUOC - sample.keys()
    if thieu_field:
        loi.append(f"Dòng {so_dong}: thiếu field {thieu_field}")

    if sample.get("nhanh") not in NHANH_HOP_LE:
        loi.append(f"Dòng {so_dong}: giá trị 'nhanh' không hợp lệ - {sample.get('nhanh')}")

    messages = sample.get("messages", [])
    if len(messages) != 3:
        loi.append(f"Dòng {so_dong}: messages phải có đúng 3 phần tử, hiện có {len(messages)}")
    else:
        for i, role_dung in enumerate(ROLE_DUNG_THU_TU):
            if messages[i].get("role") != role_dung:
                loi.append(f"Dòng {so_dong}: message thứ {i} phải có role='{role_dung}', hiện là '{messages[i].get('role')}'")
            noi_dung = messages[i].get("content", "")
            if not noi_dung or not noi_dung.strip():
                loi.append(f"Dòng {so_dong}: message thứ {i} (role={role_dung}) rỗng")

    return loi, sample.get("id")


def main():
    toan_bo_loi = []
    id_da_gap = {}
    tong_dong = 0

    for f_jsonl in sorted(DATASET_DIR.glob("*/*.jsonl")):
        with open(f_jsonl, "r", encoding="utf-8") as f:
            for so_dong_trong_file, dong_raw in enumerate(f, start=1):
                tong_dong += 1
                loi, sample_id = kiem_tra_1_dong(f"{f_jsonl.relative_to(DATASET_DIR)}:{so_dong_trong_file}", dong_raw)
                toan_bo_loi.extend(loi)
                if sample_id:
                    if sample_id in id_da_gap:
                        toan_bo_loi.append(
                            f"{f_jsonl.relative_to(DATASET_DIR)}:{so_dong_trong_file}: id '{sample_id}' bị trùng với {id_da_gap[sample_id]}"
                        )
                    else:
                        id_da_gap[sample_id] = f"{f_jsonl.relative_to(DATASET_DIR)}:{so_dong_trong_file}"

    print(f"Tổng số dòng: {tong_dong}")
    print(f"Tổng số id duy nhất: {len(id_da_gap)}")

    if toan_bo_loi:
        print(f"\nTìm thấy {len(toan_bo_loi)} lỗi:")
        for loi in toan_bo_loi:
            print(f"  - {loi}")
    else:
        print("\nKhông tìm thấy lỗi nào. Dataset hợp lệ.")


if __name__ == "__main__":
    main()