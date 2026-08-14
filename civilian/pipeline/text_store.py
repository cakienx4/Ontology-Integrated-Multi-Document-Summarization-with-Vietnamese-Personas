import os
import re

def load_custom_texts(path: str) -> dict:
    """
    Đọc document/text.txt, tách thành nhiều văn bản theo marker:
        ### TEXT_ID: <id>
        <nội dung>
    Nếu file không có marker nào (văn bản cũ, single blob) -> coi toàn bộ
    là 1 văn bản với id mặc định "text_1" (tương thích ngược).
    """
    if not os.path.isfile(path):
        return {}

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if "### TEXT_ID:" not in content:
        stripped = content.strip()
        return {"text_1": stripped} if stripped else {}

    parts = re.split(r"^### TEXT_ID:\s*(.+)$", content, flags=re.MULTILINE)
    texts = {}
    for i in range(1, len(parts), 2):
        text_id = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if body:
            texts[text_id] = body
    return texts


def append_custom_text(path: str, text_id: str, content: str):
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n### TEXT_ID: {text_id}\n{content.strip()}\n")