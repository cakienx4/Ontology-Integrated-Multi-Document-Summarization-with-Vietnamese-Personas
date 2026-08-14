import os
import sys
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pipeline.text_store import append_custom_text

TEXT_STORE_PATH = os.path.join(PROJECT_ROOT, "document", "text_2.txt")


def add_text_interactive():
    mode = input("Thêm văn bản mới vào danh sách hiện có (a) hay xóa hết và bắt đầu lại (w)? [a/w]: ").strip().lower()
    if mode == "w" and os.path.isfile(TEXT_STORE_PATH):
        os.remove(TEXT_STORE_PATH)
        print("Đã xóa toàn bộ văn bản cũ.")

    text_id = input("Nhập text_id (Enter để bắt đầu): ").strip()
    if not text_id:
        text_id = f"text_{int(time.time())}"

    print("Dán/nhập nội dung văn bản. Kết thúc bằng một dòng chỉ chứa: END")
    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)

    content = "\n".join(lines).strip()
    if not content:
        print("Văn bản rỗng — không lưu.")
        return

    append_custom_text(TEXT_STORE_PATH, text_id, content)
    print(f"Đã lưu text_id='{text_id}' vào {TEXT_STORE_PATH}")


if __name__ == "__main__":
    add_text_interactive()