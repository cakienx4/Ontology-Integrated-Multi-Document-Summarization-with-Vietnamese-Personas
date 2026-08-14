import requests
import feedparser
import csv
import time
import re
from bs4 import BeautifulSoup
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone

VN_TZ = timezone(timedelta(hours=7))

def _ngay_dang_vn(entry):
    """Tra ve date() theo gio Viet Nam cua entry RSS, hoac None neu entry khong co pub date."""
    parsed = entry.get("published_parsed")
    if not parsed:
        return None
    dt_utc = datetime(*parsed[:6], tzinfo=timezone.utc)
    return dt_utc.astimezone(VN_TZ).date()

ROOT_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT_DIR / "multi_document_variants" / "data" / "bao_chi"

# map slug RSS -> tên chuyên mục (để sau đối chiếu với genre)
CATEGORIES = {
    "thoi-su": "Thời sự",
    "the-gioi": "Thế giới",
    "kinh-doanh": "Kinh doanh",
    "phap-luat": "Pháp luật",
    "giao-duc": "Giáo dục",
    "khoa-hoc-cong-nghe": "Khoa học công nghệ",
    "suc-khoe": "Sức khỏe",
    "the-thao": "Thể thao",
    "giai-tri": "Giải trí",
    "du-lich": "Du lịch",
    "gia-dinh": "Đời sống",
    "bat-dong-san": "Bất động sản",
    "oto-xe-may": "Xe",
    "goc-nhin": "Góc nhìn",
    "tam-diem": "Tâm điểm",
}

BASE_URL = "https://vnexpress.net/rss/{}.rss"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def clean_summary(raw_html):
    text = re.sub(r"<a[^>]*>.*?</a>", "", raw_html, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()

def fetch_content(article_url):
    try:
        resp = requests.get(article_url, headers=HEADERS, timeout=10)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        article = soup.find("article", class_="fck_detail")
        if article is None:
            return ""

        paragraphs = article.find_all("p")

        texts = []
        for p in paragraphs:
            text = p.get_text(" ", strip=True)

            if not text:
                continue

            if "class" in p.attrs and "Image" in p["class"]:
                continue

            style = p.get("style", "")
            if "text-align:right" in style.replace(" ", ""):
                continue

            texts.append(text)

        return "\n".join(texts)

    except Exception as e:
        print(f"Lỗi lấy nội dung {article_url}: {e}")
        return ""

def fetch_category(slug, category_name, ngay_hop_le):
    url = BASE_URL.format(slug)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"Lỗi khi lấy {slug}: {e}")
        return []

    feed = feedparser.parse(resp.content)
    rows = []
    so_bi_loai_ngay = 0
    for entry in feed.entries:
        ngay_dang = _ngay_dang_vn(entry)
        if ngay_dang not in ngay_hop_le:
            so_bi_loai_ngay += 1
            continue

        link = entry.get("link", "")

        rows.append({
            "category_slug": slug,
            "category_name": category_name,
            "title": entry.get("title", ""),
            "summary": clean_summary(entry.get("summary", "")),
            "pub_date": ngay_dang.isoformat(),
            "link": link,
            "content": fetch_content(link),
        })

    print(f"  -> giữ {len(rows)} bài, loại {so_bi_loai_ngay} bài ngoài khung ngày")
    return rows


def main():
    hom_nay = datetime.now(VN_TZ).date()
    ngay_hop_le = {hom_nay - timedelta(days=i) for i in range(5)}
    print(f"Khung ngày hợp lệ: {sorted(ngay_hop_le)}")

    all_rows = []
    for slug, name in CATEGORIES.items():
        print(f"Đang lấy: {name} ({slug})")
        rows = fetch_category(slug, name, ngay_hop_le)
        all_rows.extend(rows)
        time.sleep(0.5)

    print(f"Tổng cộng lấy được {len(all_rows)} bài")

    with open(DATA_DIR / "vnexpress_rss_snapshot_3007.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["category_slug", "category_name", "title", "summary", "pub_date", "link", "content"])
        writer.writeheader()
        writer.writerows(all_rows)

    with open(DATA_DIR / "vnexpress_rss_snapshot_3007.json", "w", encoding="utf-8") as f:
        json.dump(all_rows, f, ensure_ascii=False, indent=2)

    print(f"Đã ghi ra {DATA_DIR / 'vnexpress_rss_snapshot_2707.csv'} và .json")


if __name__ == "__main__":
    main()