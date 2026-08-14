import requests
import feedparser
import csv
import time
import re
from bs4 import BeautifulSoup
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = ROOT_DIR / "data" / "chinh_luan"

CATEGORIES = {
    "xa-luan-1176": "Xã luận",
    "binh-luan-phe-phan-1180": "Bình luận",
}

BASE_URL = "https://nhandan.vn/rss/{}.rss"
HEADERS = {"User-Agent": "Mozilla/5.0"}

ID_PREFIX = "CL"
ID_DIGITS = 4

CSV_PATH = DATA_DIR / "nhandan_chinhluan.csv"
JSON_PATH = DATA_DIR / "nhandan_chinhluan.json"
FIELDNAMES = ["id", "category_slug", "category_name", "title", "summary", "link", "content"]


def clean_summary(raw_html):
    text = re.sub(r"<a[^>]*>.*?</a>", "", raw_html, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()

def _la_dong_gach_ngang(text):
    """Nhan dien dong phan cach kieu '-----------------------------'."""
    return bool(re.fullmatch(r"[-–—\s]{5,}", text.strip()))


def _la_dong_ghi_chu_xem_bao(text):
    """Nhan dien dong ghi chu kieu '(★) Xem Báo Nhân Dân từ số ra ngày ...'."""
    text_sach = text.strip().lower()
    return text_sach.startswith("(★)") or "xem báo nhân dân từ số" in text_sach


def _la_dong_ky_ten_tac_gia(text):
    """
    Heuristic nhan dien dong ky ten tac gia o cuoi bai (vi du 'HÀ NHÂN - VŨ ANH'):
    it tu, toan chu hoa, khong ket thuc bang dau cau ket cau.
    CHI ap dung cho dong cuoi cung con lai sau khi da loc gach ngang/ghi chu -
    khong quet toan bo doan van vi co the trung voi cau ngan hop le trong bai.
    """
    text_sach = text.strip()
    if not text_sach:
        return False
    if len(text_sach.split()) > 6:
        return False
    if text_sach[-1] in ".!?":
        return False
    if text_sach != text_sach.upper():
        return False
    return True


def _loc_doan_thua_cuoi_bai(danh_sach_doan):
    """
    Loc bo cac dong thua o CUOI danh sach doan (gach ngang, ghi chu Xem Bao,
    ten tac gia ky cuoi) - duyet tu cuoi len, dung ngay khi gap doan noi dung that
    de khong lo xoa nham cau ket luan hop le cua bai.
    """
    ket_qua = list(danh_sach_doan)
    while ket_qua:
        doan_cuoi = ket_qua[-1]
        if _la_dong_gach_ngang(doan_cuoi) or _la_dong_ghi_chu_xem_bao(doan_cuoi):
            ket_qua.pop()
            continue
        if _la_dong_ky_ten_tac_gia(doan_cuoi):
            ket_qua.pop()
            continue
        break
    return ket_qua

def fetch_content(article_url):
    """Lấy nội dung bài viết từ URL Báo Nhân Dân dựa theo cấu trúc DOM thực tế."""
    try:
        resp = requests.get(article_url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Ưu tiên lấy trực tiếp thẻ bài viết chính xác theo class & itemprop trong ảnh
        content_div = (
            soup.find("div", class_="article__body")
            or soup.find("div", attrs={"itemprop": "articleBody"})
            or soup.select_one("div.main.col.content.col")
        )

        # Fallback nếu cấu trúc bài viết dạng khác
        if content_div is None:
            content_div = soup.select_one("div.detail-content, div.content, article")

        if content_div is None:
            print(f"  [!] Không tìm thấy vùng nội dung cho {article_url}")
            return ""

        paragraphs = content_div.find_all("p")
        texts = []
        for p in paragraphs:
            text = p.get_text(" ", strip=True)
            if not text:
                continue

            # Bỏ chú thích ảnh (thường chứa class Image/caption/fig-caption)
            p_classes = p.get("class", [])
            if any(cls in ["Image", "caption", "fig-caption"] for cls in p_classes):
                continue

            # Bỏ đoạn căn phải (tác giả, nguồn)
            style = p.get("style", "")
            if "text-align:right" in style.replace(" ", ""):
                continue

            texts.append(text)

        texts = _loc_doan_thua_cuoi_bai(texts)

        return "\n".join(texts)

    except Exception as e:
        print(f"Lỗi lấy nội dung {article_url}: {e}")
        return ""

def fetch_category(slug, category_name):
    url = BASE_URL.format(slug)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"Lỗi khi lấy RSS {slug}: {e}")
        return []

    feed = feedparser.parse(resp.content)
    rows = []
    for entry in feed.entries:
        link = entry.get("link", "")
        rows.append({
            "category_slug": slug,
            "category_name": category_name,
            "title": entry.get("title", ""),
            "summary": clean_summary(entry.get("summary", "")),
            "link": link,
            "content": fetch_content(link),
        })
    print(f"  -> lấy được {len(rows)} bài từ {category_name}")
    return rows


def _doc_du_lieu_cu():
    """Đọc file JSON đã có (nếu có) để tái sử dụng id theo link, tránh việc
    crawl lại (do RSS đổi nội dung theo thời gian) làm xáo trộn id của các
    bài đã tồn tại trong dataset."""
    if not JSON_PATH.exists():
        return {}
    with open(JSON_PATH, encoding="utf-8") as f:
        du_lieu_cu = json.load(f)
    return {bai["link"]: bai["id"] for bai in du_lieu_cu if bai.get("link") and bai.get("id")}


def gan_id(rows: list, id_theo_link_cu: dict) -> list:
    so_id_da_dung = {
        int(v[len(ID_PREFIX):]) for v in id_theo_link_cu.values()
        if v.startswith(ID_PREFIX) and v[len(ID_PREFIX):].isdigit()
    }
    so_tiep_theo = max(so_id_da_dung, default=0) + 1

    for row in rows:
        link = row.get("link")
        if link in id_theo_link_cu:
            row["id"] = id_theo_link_cu[link]
        else:
            row["id"] = f"{ID_PREFIX}{so_tiep_theo:0{ID_DIGITS}d}"
            so_tiep_theo += 1

    return rows


def main():
    print("Bắt đầu crawl các chuyên mục chính luận Nhân Dân (toàn bộ bài trong RSS)...")
    id_theo_link_cu = _doc_du_lieu_cu()

    all_rows = []
    for slug, name in CATEGORIES.items():
        print(f"Đang lấy: {name} ({slug})")
        rows = fetch_category(slug, name)
        all_rows.extend(rows)
        time.sleep(0.5)

    all_rows = gan_id(all_rows, id_theo_link_cu)

    print(f"Tổng cộng lấy được {len(all_rows)} bài "
          f"({len(id_theo_link_cu)} bài đã có id từ trước, phần còn lại được gán id mới)")

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with open(CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(all_rows)

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(all_rows, f, ensure_ascii=False, indent=2)

    print(f"Đã ghi file CSV: {CSV_PATH}")
    print(f"Đã ghi file JSON: {JSON_PATH}")

if __name__ == "__main__":
    main()
