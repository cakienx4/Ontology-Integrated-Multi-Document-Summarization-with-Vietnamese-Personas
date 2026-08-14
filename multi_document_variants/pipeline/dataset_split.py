import json
import random
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = ROOT_DIR / "output" / "dataset"
OUTPUT_DIR = ROOT_DIR / "output" / "dataset"

TY_LE_VAL = 0.2
SEED = 42


def doc_dataset():
    mau = []
    for f_jsonl in sorted(DATASET_DIR.glob("*/*.jsonl")):
        with open(f_jsonl, "r", encoding="utf-8") as f:
            for dong in f:
                mau.append(json.loads(dong))
    return mau


def chia_theo_nhanh(mau):
    theo_nhanh = {}
    for m in mau:
        theo_nhanh.setdefault(m["nhanh"], []).append(m)

    train, val = [], []
    for nhanh, danh_sach in theo_nhanh.items():
        danh_sach_shuffle = danh_sach[:]
        random.Random(SEED).shuffle(danh_sach_shuffle)

        so_val = max(1, round(len(danh_sach_shuffle) * TY_LE_VAL)) if len(danh_sach_shuffle) >= 2 else 0
        val_nhanh = danh_sach_shuffle[:so_val]
        train_nhanh = danh_sach_shuffle[so_val:]

        train += train_nhanh
        val += val_nhanh

        print(f"{nhanh}: tổng {len(danh_sach_shuffle)} -> train {len(train_nhanh)}, val {len(val_nhanh)}")
        if len(danh_sach_shuffle) < 10:
            print(f"  CẢNH BÁO: nhánh '{nhanh}' có ít sample ({len(danh_sach_shuffle)}), tập val có thể không đại diện đủ")

    return train, val


def ghi_jsonl(duong_dan, danh_sach):
    with open(duong_dan, "w", encoding="utf-8") as f:
        for m in danh_sach:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")


def main():
    mau = doc_dataset()
    train, val = chia_theo_nhanh(mau)

    random.Random(SEED).shuffle(train)
    random.Random(SEED + 1).shuffle(val)

    ghi_jsonl(OUTPUT_DIR / "train_split.jsonl", train)
    ghi_jsonl(OUTPUT_DIR / "val_split.jsonl", val)

    print(f"\nTổng: train {len(train)} / val {len(val)}")
    print(f"Đã lưu tại {OUTPUT_DIR / 'train_split.jsonl'} và {OUTPUT_DIR / 'val_split.jsonl'}")


if __name__ == "__main__":
    main()