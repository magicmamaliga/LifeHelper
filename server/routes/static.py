from fastapi import APIRouter
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ..config import STATIC_DIR

router = APIRouter()

router.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
router.mount("/assets", StaticFiles(directory=f"{STATIC_DIR}/assets"), name="assets")


@router.get("/{full_path:path}")
def serve_react(full_path: str):
    return FileResponse(f"{STATIC_DIR}/index.html")
