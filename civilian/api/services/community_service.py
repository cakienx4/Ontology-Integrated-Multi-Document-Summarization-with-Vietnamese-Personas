from pipeline.civilian.community import determine_community

from api.dependencies import get_persona_row

def get_community(uuid: str) -> dict:
    row = get_persona_row(uuid)
    community = determine_community(row)
    return {"uuid": row.get("uuid", uuid), "community": community}