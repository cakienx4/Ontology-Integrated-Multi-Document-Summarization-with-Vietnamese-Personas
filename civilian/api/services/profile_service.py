from pipeline.civilian.community import determine_community
from pipeline.civilian.worlds import build_worlds

from api.dependencies import get_persona_row

def get_profile(uuid: str) -> dict:
    row = get_persona_row(uuid)
    community = determine_community(row)
    worlds = build_worlds(row)
    return {
        "uuid": row.get("uuid", uuid),
        "raw_fields": row,
        "community": community,
        "worlds": worlds,
    }