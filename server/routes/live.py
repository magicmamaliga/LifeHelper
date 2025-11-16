from fastapi import APIRouter
from urllib.parse import unquote
from datetime import datetime

from ..audio.state import get_live_transcript

router = APIRouter(prefix="/api")

@router.get("/live")
def get_live(since: str = None):
    transcript = get_live_transcript()

    if not since:
        return {"segments": transcript[-100:]}

    try:
        since_dt = datetime.strptime(unquote(since), "%Y-%m-%dT%H:%M:%S")
        filtered = [
            t for t in transcript
            if datetime.strptime(t["timestamp"], "%Y-%m-%dT%H:%M:%S") > since_dt
        ]
        return {"segments": filtered}
    except Exception:
        return {"error": "Invalid 'since' format. Expected YYYY-MM-DDTHH:MM:SS"}
