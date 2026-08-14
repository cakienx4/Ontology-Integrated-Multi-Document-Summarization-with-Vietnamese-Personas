import sys
from pathlib import Path

import pandas as pd
from fastapi import HTTPException
from google import genai
from google.genai import types

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.ontology_context import load_graph
from pipeline.civilian.summarizer_gpt import get_client as get_gpt_client
from api.config import settings

DATA_CSV = PROJECT_ROOT / "data" / "sample50.csv"
TTL_PATH = PROJECT_ROOT / "ontology" / "persona_analysis_3.ttl"


class AppState:
    def __init__(self):
        self.df: pd.DataFrame | None = None
        self.g = None
        self.gemini_client: genai.Client | None = None
        self.gpt_client = None

    def load(self):
        if settings.gemini_api_key:
            self.gemini_client = genai.Client(
                api_key=settings.gemini_api_key,
                http_options=types.HttpOptions(timeout=60000),
            )
        else:
            print("[WARNING] Chưa set GEMINI_API_KEY — engine 'gemini' sẽ không dùng được, "
                  "chỉ 'gpt_oss' hoạt động.")

        try:
            self.gpt_client = get_gpt_client()
        except Exception as e:
            print(f"[WARNING] Không khởi tạo được client gpt-oss: {e} — engine 'gpt_oss' sẽ không dùng được.")

        if not self.gemini_client and not self.gpt_client:
            raise RuntimeError(
                "Không có engine nào khả dụng — thiếu GEMINI_API_KEY và client gpt-oss cũng lỗi."
            )

        self.df = pd.read_csv(DATA_CSV)
        self.g = load_graph(str(TTL_PATH))

app_state = AppState()

def get_persona_row(uuid: str) -> dict:
    match = app_state.df[app_state.df["uuid"] == uuid]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy uuid={uuid}")
    row = match.iloc[0]
    return {k: (v.item() if hasattr(v, "item") else v) for k, v in row.to_dict().items()}