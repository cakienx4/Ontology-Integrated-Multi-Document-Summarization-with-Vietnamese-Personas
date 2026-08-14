import json
import statistics
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = ROOT_DIR / "output" / "dataset"
README_FILE = ROOT_DIR / "output" / "dataset" / "README.md"


def uoc_luong_token(so_ky_tu):
    return round(so_ky_tu / 3.5)


def doc_dataset():
    mau = []
    for f_jsonl in sorted(DATASET_DIR.glob("*/*.jsonl")):
        with open(f_jsonl, "r", encoding="utf-8") as f:
            for dong in f:
                mau.append(json.loads(dong))
    return mau


def tinh_thong_ke(mau_theo_nhanh):
    do_dai_input = [len(m["messages"][1]["content"]) for m in mau_theo_nhanh]
    do_dai_output = [len(m["messages"][2]["content"]) for m in mau_theo_nhanh]
    return {
        "so_luong": len(mau_theo_nhanh),
        "input_min": min(do_dai_input),
        "input_max": max(do_dai_input),
        "input_trung_binh": round(statistics.mean(do_dai_input)),
        "output_min": min(do_dai_output),
        "output_max": max(do_dai_output),
        "output_trung_binh": round(statistics.mean(do_dai_output)),
    }


def main():
    mau = doc_dataset()
    nhanh_list = ["bao_chi", "hanh_chinh", "chinh_luan"]

    dong_bao_cao = ["# Thống kê dataset\n"]
    dong_bao_cao.append(f"Tổng số sample: {len(mau)}\n")

    dong_bao_cao.append("\n## Phân bố theo nhánh")
    for nhanh in nhanh_list:
        so_luong = len([m for m in mau if m["nhanh"] == nhanh])
        ty_le = round(so_luong / len(mau) * 100, 1) if mau else 0
        dong_bao_cao.append(f"- {nhanh}: {so_luong} ({ty_le}%)")

    for nhanh in nhanh_list:
        mau_nhanh = [m for m in mau if m["nhanh"] == nhanh]
        if not mau_nhanh:
            dong_bao_cao.append(f"\n## {nhanh}\nKhông có sample.\n")
            continue
        tk = tinh_thong_ke(mau_nhanh)
        dong_bao_cao.append(f"\n## {nhanh}")
        dong_bao_cao.append(f"- Số sample: {tk['so_luong']}")
        dong_bao_cao.append(
            f"- Độ dài input (ký tự): min {tk['input_min']} / max {tk['input_max']} / "
            f"trung bình {tk['input_trung_binh']}"
        )
        dong_bao_cao.append(
            f"- Độ dài input (ước lượng token, ~3.5 ký tự/token): min {uoc_luong_token(tk['input_min'])} / "
            f"max {uoc_luong_token(tk['input_max'])} / trung bình {uoc_luong_token(tk['input_trung_binh'])}"
        )
        dong_bao_cao.append(
            f"- Độ dài output (ký tự): min {tk['output_min']} / max {tk['output_max']} / "
            f"trung bình {tk['output_trung_binh']}"
        )

        theo_variant = {}
        for m in mau_nhanh:
            theo_variant.setdefault(m.get("variant", "?"), []).append(m)
        dong_bao_cao.append(f"- Phân bố theo variant:")
        for variant, ds in sorted(theo_variant.items()):
            ty_le_variant = round(len(ds) / len(mau_nhanh) * 100, 1)
            dong_bao_cao.append(f"  - {variant}: {len(ds)} ({ty_le_variant}%)")

        print(f"{nhanh}: {tk}")

    dong_bao_cao.append(
        "\n---\nLưu ý: ước lượng token chỉ mang tính tham khảo. "
        "Cần kiểm tra với tokenizer thực tế của model dự định fine-tune, "
        "và xem có cần cắt/lọc thêm theo giới hạn context của model đó hay không."
    )

    with open(README_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(dong_bao_cao))

    print(f"\nĐã ghi thống kê vào {README_FILE}")


if __name__ == "__main__":
    main()