import json
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline.profiles.generate_state_profiles import TAXONOMY, FIELD_ORDER, build_profile, build_mo_ta_chung
from pipeline.profiles.enrich_state_profiles import goi_llm, lay_chuc_danh

MA_TRUONG = {
    "nganh_to": "nt", "nganh_nho": "nn", "to_chuc": "tc",
    "kinh_nghiem": "kn", "chu_de": "cd", "cau_hoi_truoc_mat": "ch",
}

DANH_SACH_BIEN_THE = [
    ["nganh_to"],
    ["nganh_to", "nganh_nho"],
    ["nganh_to", "chu_de"],
    ["nganh_to", "cau_hoi_truoc_mat"],
    ["nganh_to", "nganh_nho", "to_chuc"],
    ["nganh_to", "nganh_nho", "chu_de"],
    ["nganh_to", "chu_de", "cau_hoi_truoc_mat"],
    ["nganh_to", "nganh_nho", "to_chuc", "kinh_nghiem"],
    ["nganh_to", "nganh_nho", "to_chuc", "chu_de"],
    ["nganh_to", "nganh_nho", "chu_de", "cau_hoi_truoc_mat"],
    ["nganh_to", "nganh_nho", "to_chuc", "kinh_nghiem", "chu_de"],
    ["nganh_to", "nganh_nho", "to_chuc", "chu_de", "cau_hoi_truoc_mat"],
    ["nganh_to", "nganh_nho", "kinh_nghiem", "chu_de", "cau_hoi_truoc_mat"],
    FIELD_ORDER,
]


def ten_file_bien_the(truong_list):
    ma = [MA_TRUONG[t] for t in truong_list]
    return "state_profiles_" + "_".join(ma) + ".json"


def sinh_tap_id_coverage(seed=42):
    import random
    rng = random.Random(seed)
    profiles = []
    idx = 1
    for nganh_to, info in TAXONOMY.items():
        for nganh_nho in info["nganh_nho"].keys():
            gioi_tinh = rng.choice(["Nam", "Nữ"])
            p = build_profile(idx, nganh_to, gioi_tinh, rng, nganh_nho=nganh_nho)
            profiles.append(p)
            idx += 1
    return profiles


def loc_truong(profile, truong_list):
    ket_qua = {"id": profile["id"]}
    for t in truong_list:
        ket_qua[t] = profile[t]
    return ket_qua


def tao_prompt_mo_ta_bien_the(profile, truong_list):
    co_kinh_nghiem = "kinh_nghiem" in truong_list
    chuc_danh = lay_chuc_danh(profile.get("kinh_nghiem", "")) if co_kinh_nghiem else ""
    mo_dau = f"Một {chuc_danh}" if chuc_danh else "Một cán bộ"

    dong_thong_tin = []
    if "nganh_to" in truong_list:
        dong_thong_tin.append(f'- Ngành: {profile["nganh_to"]}')
    if "nganh_nho" in truong_list:
        dong_thong_tin.append(f'- Lĩnh vực chuyên trách: {profile["nganh_nho"]}')
    if "to_chuc" in truong_list:
        dong_thong_tin.append(f'- Tổ chức/Nơi công tác: {profile["to_chuc"]}')
    if "kinh_nghiem" in truong_list:
        dong_thong_tin.append(f'- Kinh nghiệm: {profile["kinh_nghiem"]}')
    if "chu_de" in truong_list:
        dong_thong_tin.append(f'- Chủ đề quan tâm: {", ".join(profile["chu_de"])}')
    if "cau_hoi_truoc_mat" in truong_list:
        dong_thong_tin.append(f'- Mối quan tâm hiện tại: {profile["cau_hoi_truoc_mat"]}')

    ghi_chu_mo_dau = (
        f" (dùng ĐÚNG nguyên văn chức danh này)" if chuc_danh
        else " (không có thông tin chức danh cụ thể, dùng cụm mở đầu chung này, KHÔNG tự bịa chức danh)"
    )

    return f'''
    Viết một đoạn mô tả persona bằng tiếng Việt, giọng văn kiểu Nemotron-Personas (ngôi thứ 3,
    KHÔNG dùng đại từ nhân xưng: "tôi", "ông", "bà", "anh", "chị", "họ").

    Đoạn văn CHỈ được dùng đúng những thông tin liệt kê dưới đây, TUYỆT ĐỐI KHÔNG tự bịa thêm
    thông tin không có trong danh sách (đây là bản mô tả rút gọn, chỉ có một số trường):
    {chr(10).join(dong_thong_tin)}

    Câu đầu tiên bắt đầu bằng "{mo_dau}"{ghi_chu_mo_dau}.

    YÊU CẦU BẮT BUỘC về độ dài và độ đầy đủ:
- Dù chỉ có {len(dong_thong_tin)} thông tin ở trên, đoạn văn vẫn PHẢI viết đầy đủ, diễn giải
  rõ ràng — TUYỆT ĐỐI KHÔNG viết qua loa, cụt lủn kiểu liệt kê. Với mỗi thông tin đã cho, hãy
  diễn giải thêm về ý nghĩa, vai trò, hoặc bối cảnh của thông tin đó trong công việc của nhân
  vật (dựa trên suy luận hợp lý từ chính thông tin đã cho, KHÔNG thêm sự kiện/số liệu/chi tiết
  mới nằm ngoài danh sách trên).
- Số lượng thông tin càng nhiều thì đoạn văn càng phải dài hơn tương ứng: tối thiểu 3-4 câu
  nếu chỉ có 1-2 thông tin; tối thiểu 6-7 câu nếu có 4-6 thông tin — luôn đảm bảo mọi thông
  tin trong danh sách trên đều được thể hiện đầy đủ, rõ ràng, không bỏ sót.
- TUYỆT ĐỐI KHÔNG lặp lại cùng một ý bằng cách diễn đạt khác ở nhiều câu (ví dụ: không được
  vừa nói "tuân thủ quy định pháp luật" ở câu này rồi lại nói "đảm bảo tính minh bạch, đúng
  quy trình" ở câu khác nếu 2 ý đó thực chất là một). Mỗi câu phải mang thêm một ý MỚI.
- TRÁNH các cụm từ sáo rỗng, khẩu hiệu chung chung không gắn với thông tin cụ thể đã cho (ví
  dụ: "tận tụy", "minh bạch, hiệu quả", "đóng góp vào sự ổn định và phát triển", "cầu nối quan
  trọng") trừ khi cụm đó thực sự cần thiết để diễn giải MỘT thông tin cụ thể trong danh sách
  trên. Ưu tiên nhắc lại và triển khai xoay quanh chính tên ngành/lĩnh vực/tổ chức cụ thể đã
  cho, thay vì nói chung chung về "công tác hành chính" nói chung.

    Chỉ trả về đoạn mô tả, không đánh số, không giải thích gì thêm.
    '''


def la_loi_het_quota(e):
    text = str(e).lower()
    return "resource_exhausted" in text or "429" in text or "quota" in text


def sinh_bien_the(truong_list, coverage_profiles, da_co=None):
    da_co = da_co or {}
    ket_qua = list(da_co.values())
    con_lai = [p for p in coverage_profiles if p["id"] not in da_co]
    if not con_lai:
        print("Bien the nay da xong het tu lan chay truoc, bo qua.")
        return ket_qua

    for p in con_lai:
        p_loc = loc_truong(p, truong_list)
        p_loc["mo_ta_chung"] = build_mo_ta_chung(p, "Nam", truong_list=truong_list)
        try:
            p_loc["mo_ta_chung"] = goi_llm(tao_prompt_mo_ta_bien_the(p, truong_list))
            print("Da xong id", p["id"])
        except Exception as e:
            if la_loi_het_quota(e):
                print("HET QUOTA GEMINI HOM NAY - dung lai giua chung, id", p["id"],
                      "va cac id sau se tu chay tiep vao lan sau.")
                return ket_qua
            print("Loi enrich LLM cho id", p["id"], "->", e, "- giu ban template")
        ket_qua.append(p_loc)
        time.sleep(1)
    return ket_qua


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--id", help="Chi chay cho 1 id (vi du NN001), de test nhanh truoc khi chay full")
    parser.add_argument("--variant", help="Chi chay cho 1 bien the, theo ma ten file (vi du 'nt_nn_tc')")
    args = parser.parse_args()

    ROOT_DIR = Path(__file__).resolve().parents[3]
    DATA_DIR = ROOT_DIR / "data"
    OUT_DIR = DATA_DIR / "profile_variants"
    OUT_DIR.mkdir(exist_ok=True)

    coverage_profiles = sinh_tap_id_coverage(seed=42)
    print(f"Da sinh {len(coverage_profiles)} profile coverage "
          f"(id tu {coverage_profiles[0]['id']} den {coverage_profiles[-1]['id']})")

    if args.id:
        coverage_profiles = [p for p in coverage_profiles if p["id"] == args.id]
        if not coverage_profiles:
            raise ValueError(f"Khong tim thay id {args.id}")

    danh_sach_can_chay = DANH_SACH_BIEN_THE
    if args.variant:
        danh_sach_can_chay = [
            tl for tl in DANH_SACH_BIEN_THE
            if ten_file_bien_the(tl) == f"state_profiles_{args.variant}.json"
        ]
        if not danh_sach_can_chay:
            raise ValueError(f"Khong tim thay bien the {args.variant}")

    for truong_list in danh_sach_can_chay:
        ten_file = ten_file_bien_the(truong_list)
        duong_dan_json = OUT_DIR / ten_file

        da_co = {}
        if duong_dan_json.exists():
            with open(duong_dan_json, "r", encoding="utf-8") as f:
                da_co = {p["id"]: p for p in json.load(f)}

        print(f"--- Dang sinh bien the: {ten_file} ({truong_list}) "
              f"- da co {len(da_co)}/{len(coverage_profiles)} tu truoc ---")
        ket_qua = sinh_bien_the(truong_list, coverage_profiles, da_co=da_co)

        with open(duong_dan_json, "w", encoding="utf-8") as f:
            json.dump(ket_qua, f, ensure_ascii=False, indent=2)
        print(f"Da ghi {len(ket_qua)}/{len(coverage_profiles)} profile -> {duong_dan_json}")

        if len(ket_qua) < len(coverage_profiles):
            print("Bien the nay chua xong (co the do het quota) - dung script tai day. "
                  "Chay lai lenh cu vao lan sau se tu tiep tuc.")
            break