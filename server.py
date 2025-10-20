import os
import io
import json
import time
import queue
import threading
import tempfile
import subprocess
from datetime import datetime
from contextlib import asynccontextmanager
from urllib.parse import unquote

import numpy as np
import sounddevice as sd
import soundfile as sf
from scipy.io.wavfile import write as write_wav
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import whisper

# -------------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------------

SAMPLE_RATE = 16000
CHUNK_SECONDS = 3
WHISPER_CPP_PATH = r"C:\Users\Mate\Desktop\whisper.cpp\build\bin\whisper-cli.exe"
WHISPER_MODEL = r"C:\Users\Mate\Desktop\whisper.cpp\models\ggml-base.en.bin"

DEVICE_INDEX = next(
    i for i, d in enumerate(sd.query_devices()) if "CABLE Output" in d["name"]
)

# -------------------------------------------------------------------
# GLOBAL STATE
# -------------------------------------------------------------------

_audio_q = queue.Queue()
AUDIO_BUFFER = []  # accumulated audio
live_transcript = []  # [{"timestamp": str, "text": str}]
stop_threads = False

client = OpenAI()  # Uses OPENAI_API_KEY
_whisper_model = whisper.load_model("base")

# -------------------------------------------------------------------
# WHISPER.CPP TRANSCRIPTION
# -------------------------------------------------------------------

def transcribe_with_whisper_cpp(audio_data: bytes) -> str:
    """Run whisper.cpp binary on given WAV audio data."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_wav:
        tmp_wav.write(audio_data)
        tmp_path = tmp_wav.name

    txt_path = tmp_path.replace(".wav", ".txt")
    cmd = [
        WHISPER_CPP_PATH, "-m", WHISPER_MODEL,
        "-f", tmp_path, "-otxt", "-of", tmp_path[:-4], "-t", "8"
    ]

    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    # Handle forced exit or Ctrl+C
    if result.returncode == 3221225786:
        print("⚠️ whisper.cpp interrupted; skipping cleanup.")
        cleanup_temp_files(tmp_path, txt_path)
        return ""

    if result.returncode != 0:
        print(f"⚠️ whisper.cpp failed ({result.returncode}): {result.stderr.decode(errors='ignore')}")
        cleanup_temp_files(tmp_path, txt_path)
        return ""

    text = ""
    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            text = f.read().strip()
    except FileNotFoundError:
        pass

    cleanup_temp_files(tmp_path, txt_path)
    return text


def cleanup_temp_files(*paths):
    """Helper to safely delete temporary files."""
    for path in paths:
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass


# -------------------------------------------------------------------
# AUDIO CAPTURE AND TRANSCRIPTION THREADS
# -------------------------------------------------------------------

def _audio_callback(indata, frames, time_info, status):
    """Callback fired when new audio is available."""
    _audio_q.put(indata.copy())
    AUDIO_BUFFER.append(indata.copy())


def _capture_loop():
    """Continuously capture audio from the configured input device."""
    global stop_threads
    with sd.InputStream(
        channels=1,
        samplerate=SAMPLE_RATE,
        device=DEVICE_INDEX,
        callback=_audio_callback,
        dtype="float32"
    ):
        print("🎙 Listening... (Ctrl+C to stop)")
        while not stop_threads:
            time.sleep(0.1)
    print("🛑 Audio capture stopped.")


def _transcribe_worker():
    """
    Continuously process queued audio and transcribe when a full sentence or max duration is reached.
    Uses adaptive silence detection to capture natural phrases/sentences.
    """
    global stop_threads
    print("🔊 Transcription thread started (sentence-level mode).")

    buffer = np.zeros((0, 1), dtype=np.float32)

    # --- Configurable parameters ---
    max_samples = SAMPLE_RATE * 7           # hard upper limit (safety)
    silence_threshold = 0.005              # lower = less sensitive; adapt to mic noise
    silence_window = int(SAMPLE_RATE * 0.2) # analyze every 200ms
    silence_required = 0.8                  # how long quiet must last before we finalize
    min_sentence_length = 1.8               # must have at least this much speech
    trailing_pad = int(SAMPLE_RATE * 0.3)   # keep extra 0.5s after silence

    # --- Internal counters ---
    silence_counter = 0
    speech_detected = False
    silence_limit = int(silence_required / 0.2)

    def current_rms(x):
        return np.sqrt(np.mean(np.square(x)))

    while not stop_threads:
        try:
            data = _audio_q.get(timeout=1)
            buffer = np.concatenate((buffer, data))

            # calculate recent energy
            if len(buffer) >= silence_window:
                recent = buffer[-silence_window:]
                rms = current_rms(recent)

                # detect speech vs silence
                if rms > silence_threshold:
                    silence_counter = 0
                    speech_detected = True
                else:
                    if speech_detected:  # only count silence after we had speech
                        silence_counter += 1

                # finalize when we’ve had real speech and silence long enough
                total_duration = len(buffer) / SAMPLE_RATE
                if (
                    speech_detected
                    and silence_counter >= silence_limit
                    and total_duration >= min_sentence_length
                ):
                    end_idx = min(len(buffer) + trailing_pad, len(buffer))
                    segment = np.squeeze(buffer[:end_idx])
                    buffer = np.zeros((0, 1), dtype=np.float32)
                    silence_counter = 0
                    speech_detected = False
                    transcribe_segment(segment)
                    continue

                # force transcription at hard max
                if len(buffer) >= max_samples:
                    segment = np.squeeze(buffer[:max_samples])
                    buffer = buffer[max_samples:]
                    silence_counter = 0
                    speech_detected = False
                    transcribe_segment(segment)
                    continue

        except queue.Empty:
            time.sleep(0.05)

    print("🧵 Transcription thread exited.")


def transcribe_segment(segment: np.ndarray):
    """Convert a segment to text via whisper.cpp and append if valid."""
    wav_buf = io.BytesIO()
    sf.write(wav_buf, segment, SAMPLE_RATE, format="WAV")
    text = transcribe_with_whisper_cpp(wav_buf.getvalue())

    if not valid_text(text):
        return

    ts = datetime.now().isoformat(timespec='seconds')
    live_transcript.append({"timestamp": ts, "text": text})
    print(f"[{ts}] {text}")

def valid_text(text: str) -> bool:
    """Filter out meaningless or silent segments."""
    if not text:
        return False
    t = text.strip().lower()
    if t in ("[blank_audio]", "[blank]", "(silence)", "[ silence ]"):
        return False
    if t in ("you", "uh", "ah", "a", "hmm"):
        return False
    return True


def start_audio_streamer():
    """Start background audio and transcription threads."""
    threading.Thread(target=_capture_loop, daemon=True).start()
    threading.Thread(target=_transcribe_worker, daemon=True).start()


# -------------------------------------------------------------------
# FASTAPI APP
# -------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and graceful shutdown handler."""
    global stop_threads
    print("🚀 FastAPI starting...")
    start_audio_streamer()

    yield  # app runs

    print("🛑 Stopping threads...")
    stop_threads = True
    time.sleep(1.5)
    save_transcript_and_audio()
    print("👋 FastAPI shutdown complete.")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # local dev
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "FastAPI is running"}


@app.get("/live")
def get_live(since: str = None):
    """Return live transcript since a given timestamp (optional)."""
    if not since:
        return {"segments": live_transcript[-100:]}

    try:
        since_dt = datetime.strptime(unquote(since), "%Y-%m-%dT%H:%M:%S")
        filtered = [
            t for t in live_transcript
            if datetime.strptime(t["timestamp"], "%Y-%m-%dT%H:%M:%S") > since_dt
        ]
        return {"segments": filtered}
    except Exception:
        return {"error": "Invalid 'since' format. Expected YYYY-MM-DDTHH:MM:SS"}


@app.post("/ask")
async def ask_ai(request: Request):
    """Ask an AI interview-style question."""
    data = await request.json()
    question = data.get("question", "").strip()
    if not question:
        return {"answer": "(No question text received)"}

    completion = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {"role": "system", "content": "You are in a Java interview. Be concise, natural, and realistic."},
            {"role": "user", "content": question},
        ]
    )
    return {"answer": completion.choices[0].message.content}


# -------------------------------------------------------------------
# SAVE ON SHUTDOWN
# -------------------------------------------------------------------

def save_transcript_and_audio():
    """Persist transcript and audio to disk when shutting down."""
    if not live_transcript and not AUDIO_BUFFER:
        print("Nothing to save.")
        return

    timestamp = datetime.now().isoformat(timespec='seconds').replace(":", "-")

    if live_transcript:
        with open(f"transcript_live_{timestamp}.json", "w", encoding="utf-8") as f:
            json.dump(live_transcript, f, ensure_ascii=False, indent=2)
        print("💾 Transcript saved.")

    if AUDIO_BUFFER:
        audio_data = np.concatenate(AUDIO_BUFFER, axis=0)
        write_wav(f"audio_live_{timestamp}.wav", SAMPLE_RATE, audio_data)
        print("🎧 Audio saved.")


# -------------------------------------------------------------------
# ENTRY POINT
# -------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
