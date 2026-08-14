from pipeline.civilian.worlds import build_worlds

from api.dependencies import get_persona_row

def get_inference(uuid: str) -> dict:
    row = get_persona_row(uuid)
    worlds = build_worlds(row)
    return {"uuid": row.get("uuid", uuid), "worlds": worlds}