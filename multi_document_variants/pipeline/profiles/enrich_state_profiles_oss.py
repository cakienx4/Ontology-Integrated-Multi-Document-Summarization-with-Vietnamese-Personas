import random
import json
import re
import asyncio
from pipeline.utils_new import retry_generate_async, OSS_MODEL_NAME, tao_oss_client_async, OSS_MAX_CONCURRENCY
from pipeline.profiles.generate_state_profiles import save_csv
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"

MAX_RETRY_ATTEMPTS = 5

async def goi_llm_async(client, prompt):
    async def _call():
        return await client.models.generate_content(
            model=OSS_MODEL_NAME,
            contents=prompt,
            config={"temperature": 0.9},
        )
    response = await retry_generate_async(_call)
    return response.text.strip()


def lay_chuc_danh(kinh_nghiem_text: str) -> str:
    """
    Tach chinh xac cum chuc danh tu cau kinh_nghiem, vi du:
    "...hien dang dam nhiem vi tri Truong phong." -> "Truong phong"
    Dung chung logic voi lay_chuc_vu() trong rss_personalize_gemini.py.
    """
    match = re.search(r"đảm nhiệm vị trí (.+?)\.", kinh_nghiem_text or "")
    return match.group(1).strip() if match else ""

# 4 khuon cau truc khac nhau cho mo_ta_chung, moi profile duoc gan ngau nhien 1 khuon
# (chon ngau nhien bang code, KHONG de LLM tu chon, vi LLM luon hoi tu ve 1 kieu quen thuoc)
CAU_TRUC_MO_TA = [
    {
        "ten": "to_chuc_kinh_nghiem_truoc",
        "huong_dan": (
            "Câu 1: 'Một {chuc_danh}' + nêu tổ chức công tác + số năm kinh nghiệm trong ngành.\n"
            "Câu 2: kiến thức chuyên môn/năng lực nổi bật liên quan tới ngành.\n"
            "Câu cuối: mối quan tâm/trách nhiệm hiện tại (dựa trên phần 'Mối quan tâm hiện tại')."
        ),
    },
    {
        "ten": "moi_quan_tam_len_dau",
        "huong_dan": (
            "Câu 1: 'Một {chuc_danh}' + nêu THẲNG mối quan tâm/trách nhiệm hiện tại ngay trong câu này "
            "(dựa trên phần 'Mối quan tâm hiện tại'). TUYỆT ĐỐI KHÔNG nhắc tổ chức hay số năm kinh "
            "nghiệm ở câu 1.\n"
            "Câu 2: mới nêu tổ chức công tác và số năm kinh nghiệm.\n"
            "Câu cuối: kiến thức chuyên môn/năng lực nổi bật."
        ),
    },
    {
        "ten": "chuyen_mon_truoc",
        "huong_dan": (
            "Câu 1: 'Một {chuc_danh}' + kiến thức chuyên môn/thế mạnh nổi bật trong ngành. KHÔNG nêu "
            "tổ chức hay số năm kinh nghiệm ở câu này.\n"
            "Câu 2: nêu tổ chức công tác, số năm kinh nghiệm lồng vào GIỮA câu (không đặt ở đầu câu).\n"
            "Câu cuối: mối quan tâm hiện tại."
        ),
    },
    {
        "ten": "kinh_nghiem_va_quan_tam_dau",
        "huong_dan": (
            "Câu 1: 'Một {chuc_danh}' + số năm kinh nghiệm. KHÔNG nêu tên tổ chức ở câu này.\n"
            "Câu 2: nêu mối quan tâm hiện tại, xen kẽ nhắc tên tổ chức công tác trong câu này.\n"
            "Câu cuối: kiến thức chuyên môn/năng lực nổi bật."
        ),
    },
]

# cac cum tu bi lam dung qua nhieu, can tranh lap lai
CUM_TU_HAN_CHE = [
    "với bề dày", "hiện đang", "hiện nay", "vị trí này", "chuyên gia này",
    "cán bộ này", "sở hữu",
]


def chon_khuon_mo_ta(profile_id: str) -> dict:
    """Chon 1 khuon cau truc co dinh theo id, de tai lap duoc ket qua khi chay lai."""
    rng = random.Random(profile_id)
    return rng.choice(CAU_TRUC_MO_TA)


def tao_prompt_mo_ta(profile):
    chuc_danh = lay_chuc_danh(profile.get("kinh_nghiem", ""))
    khuon = chon_khuon_mo_ta(profile["id"])
    huong_dan_cau_truc = khuon["huong_dan"].format(chuc_danh=chuc_danh)

    prompt = f''' 
Viết một đoạn mô tả persona bằng tiếng Việt, dài TỐI THIỂU 3 câu (có thể 3, 4 hoặc 5 câu), theo
đúng giọng văn của các ví dụ sau (ví dụ bằng tiếng Anh, khi viết vẫn phải viết tiếng Việt, chỉ
áp dụng giọng văn):
- "A software developer who is looking for a way to simplify the integration of GPRS technology into their embedded system designs. They are interested in developing a stable and efficient software stack for an embedded system."
- "A land reclamation expert who is interested in the history, current practices, and future implications of land reclamation in different regions around the world. This person is knowledgeable about the environmental, social, and economic impacts of land reclamation."

Chức danh CHÍNH XÁC của người này là: "{chuc_danh}"

CẤU TRÚC BẮT BUỘC cho đoạn văn này (PHẢI theo đúng thứ tự nội dung dưới đây, không được đổi
sang thứ tự khác):
{huong_dan_cau_truc}

Quy tắc BẮT BUỘC khác:
1. Câu 1 phải bắt đầu bằng "Một {chuc_danh}" — dùng ĐÚNG NGUYÊN VĂN, không diễn giải lại, không
   đổi thành chức danh/từ khác.
2. TUYỆT ĐỐI KHÔNG dùng đại từ nhân xưng: "tôi", "ông", "bà", "anh", "chị", "họ".
3. HẠN CHẾ TỐI ĐA các cụm từ sau (chỉ dùng nếu thực sự cần thiết, không lạm dụng):
   {", ".join(f'"{c}"' for c in CUM_TU_HAN_CHE)}.
   Thay vào đó, hãy sáng tạo cách diễn đạt khác để nhắc lại chủ thể hoặc dẫn dắt câu.
4. Trước khi trả lời, tự rà lại: câu 1 có đúng nguyên văn chức danh không, có sót đại từ nhân
   xưng không, có đang dùng lại các cụm từ bị hạn chế ở mục 3 không.

Thông tin để viết:
- Tổ chức/Nơi công tác: {profile["to_chuc"]}
- Ngành: {profile["nganh_to"]} - {profile["nganh_nho"]}
- Kinh nghiệm: {profile["kinh_nghiem"]}
- Mối quan tâm hiện tại: {profile["cau_hoi_truoc_mat"]}

Chỉ trả về đoạn mô tả, không đánh số câu, không giải thích gì thêm.
    '''
    return prompt


def tao_prompt_cau_hoi(profile):
    return f'''Một cán bộ làm trong lĩnh vực {profile.get("nganh_nho", "")} thuộc ngành {profile.get("nganh_to", "")}, đang công tác tại {profile.get("to_chuc", "")}.

Hãy viết 1 CÂU KHẲNG ĐỊNH (không phải câu hỏi) mô tả khuynh hướng/xu hướng quan tâm chính sách hiện tại của người này.

Quy tắc BẮT BUỘC:
- KHÔNG được viết dưới dạng câu hỏi: không dùng dấu chấm hỏi "?", không bắt đầu bằng "Làm thế nào", "Như thế nào", "Tại sao", "Cần làm gì", v.v.
- Câu phải mang tính định hướng/khuynh hướng, bắt đầu bằng một cụm mở đầu tương tự (có thể đổi từ ngữ cho tự nhiên, không bắt buộc chép nguyên văn): "Có xu hướng ưu tiên theo dõi...", "Có khuynh hướng tập trung vào việc nắm bắt...", "Đặc biệt chú trọng đến...", "Đang dành sự quan tâm sát sao đến...", "Thường xuyên cập nhật thông tin về...".
- TUYỆT ĐỐI KHÔNG dùng đại từ nhân xưng: không "tôi", "ông", "bà", "anh", "chị", "họ", "người này". Để chủ ngữ ẩn, câu bắt đầu thẳng bằng cụm mở đầu ở trên.
- Nội dung phải là một chủ đề/vấn đề chính sách cụ thể, sát với ngành và tổ chức công tác, không viết chung chung.
- Chỉ trả về đúng 1 câu, không giải thích gì thêm, không đánh số.'''


async def xu_ly_mot_profile(client, semaphore, p):
    async with semaphore:
        try:
            p["cau_hoi_truoc_mat"] = await goi_llm_async(client, tao_prompt_cau_hoi(p))
            p["mo_ta_chung"] = await goi_llm_async(client, tao_prompt_mo_ta(p))
            print("Da xong profile:", p.get("id"))
        except Exception as e:
            print("Loi khi goi LLM cho profile", p.get("id"), "->", e)
        return p


async def sinh_lai_bang_llm_async(danh_sach_profile):
    client = tao_oss_client_async()
    semaphore = asyncio.Semaphore(OSS_MAX_CONCURRENCY)
    tasks = [xu_ly_mot_profile(client, semaphore, p) for p in danh_sach_profile]
    ket_qua = await asyncio.gather(*tasks)
    return ket_qua


if __name__ == "__main__":
    with open(DATA_DIR / "state_profiles.json", "r", encoding="utf-8") as f:
        profiles = json.load(f)

    profiles_moi = asyncio.run(sinh_lai_bang_llm_async(profiles))

    with open(DATA_DIR / "state_profiles.json", "w", encoding="utf-8") as f:
        json.dump(profiles_moi, f, ensure_ascii=False, indent=2)

    save_csv(profiles_moi, str(DATA_DIR / "state_profiles.csv"))

    print("Xong roi, da ghi state_profiles.json va .csv")