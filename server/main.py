import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .audio.capture import start_audio_streamer, stop_threads
from .audio.shutdown import save_transcript_and_audio_on_shutdown
from .routes import root, live, ask, static


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
app.include_router(static.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
