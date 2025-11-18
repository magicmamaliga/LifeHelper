# lifehelper.spec
import os
from PyInstaller.utils.hooks import collect_submodules

project_root = os.path.abspath(".")
whisper_cli = os.path.join(project_root, "whisper", "whisper-cli.exe")
base_model = os.path.join(project_root, "whisper", "models", "ggml-base.en.bin")
frontend_dist = os.path.join(project_root, "dist")

datas = []

# Include only ggml-base.en.bin
if os.path.isfile(base_model):
    datas.append((base_model, "whisper/models"))

# Include frontend build
if os.path.isdir(frontend_dist):
    datas.append((frontend_dist, "dist"))

binaries = []

# Whisper binary next to lifehelper.exe
if os.path.isfile(whisper_cli):
    binaries.append((whisper_cli, "."))

a = Analysis(
    ["lifehelper.py"],
    pathex=[project_root],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        *collect_submodules("server"),
        "platformdirs",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="lifehelper",
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="lifehelper",
)
