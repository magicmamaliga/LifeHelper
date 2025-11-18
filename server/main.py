import os
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .audio.capture import start_audio_streamer, stop_threads
from .audio.shutdown import save_transcript_and_audio_on_shutdown
from .routes import root, live, ask, static
from .routes.static import static_root, assets_root

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 FastAPI starting...")
    start_audio_streamer()

    yield

    print("🛑 Stopping threads...")
    stop_threads()
    time.sleep(1.5)
    save_transcript_and_audio_on_shutdown()
    print("👋 FastAPI shutdown complete.")

app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(root.router)
app.include_router(live.router)
app.include_router(ask.router)

# Serve assets normally
app.mount("/assets", StaticFiles(directory=assets_root), name="assets")

# Serve index.html and all static files from root
app.mount("/", StaticFiles(directory=static_root, html=True), name="root")





# --- CATCH-ALL ROUTE FOR REACT ---
@app.get("/{full_path:path}")
async def serve_react(full_path: str):
    # Always return index.html for front-end routing
    return FileResponse(os.path.join(static_root, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
