import sys
import os
from fastapi import APIRouter
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ..config import STATIC_DIR



def resource_path(relative_path):
    """
    Correct resource path resolver for both dev and PyInstaller.
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, "_MEIPASS"):
        base_path = os.path.dirname(sys.executable)
    else:
        # <-- IMPORTANT FIX: use project root, not the folder of this file
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
    return os.path.normpath(os.path.join(base_path, relative_path))


# Absolute static folder path
static_root = resource_path(STATIC_DIR)
assets_root = os.path.join(static_root, "assets")

