# server.py
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import whisper
import tempfile
import os
import soundfile as sf
import io

import threading
import time
import queue
import sounddevice as sd
import numpy as np
import whisper
from fastapi import Query
from urllib.parse import unquote
from datetime import datetime
import json
from contextlib import asynccontextmanager
import subprocess
import numpy as np
from scipy.io.wavfile import write as write_wav

AUDIO_BUFFER = []   # list of numpy arrays

SAMPLE_RATE = 16000
CHUNK_SECONDS = 3
# DEVICE_INDEX = None   # None = default input; set to loopback device if you want system audio
DEVICE_INDEX = next(i for i, d in enumerate(sd.query_devices()) if "CABLE Output" in d["name"])
# shared queue for audio chunks
_audio_q = queue.Queue()
# load whisper model once
_whisper_model = whisper.load_model("base")

live_transcript = []  # global list to hold timestamped text
stop_threads = False

WHISPER_CPP_PATH = r"C:\Users\Mate\Desktop\whisper.cpp\build\bin\whisper-cli.exe"
WHISPER_MODEL = r"C:\Users\Mate\Desktop\whisper.cpp\models\ggml-base.en.bin"

def transcribe_with_whisper_cpp(audio_data, sample_rate=16000):
    """Transcribe raw audio bytes with whisper.cpp binary."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_wav:
        tmp_wav.write(audio_data)
        tmp_path = tmp_wav.name

    txt_path = tmp_path.replace(".wav", ".txt")

    cmd = [
        WHISPER_CPP_PATH,
        "-m", WHISPER_MODEL,
        "-f", tmp_path,
        "-otxt",
        "-of", tmp_path.replace(".wav", ""),
        "-t", "8",
    ]

    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    # Handle known shutdown signal (0xC000013A)
    if result.returncode == 3221225786:
        print("⚠️ whisper.cpp interrupted by shutdown signal, ignoring.")
        try:
            os.remove(tmp_path)
            if os.path.exists(txt_path):
                os.remove(txt_path)
        except OSError:
            pass
        return ""

    if result.returncode != 0:
        print(f"⚠️ whisper.cpp failed (exit {result.returncode}): {result.stderr.decode('utf-8', errors='ignore')}")
        try:
            os.remove(tmp_path)
            if os.path.exists(txt_path):
                os.remove(txt_path)
        except OSError:
            pass
        return ""

    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            text = f.read().strip()
    except FileNotFoundError:
        text = ""

    os.remove(tmp_path)
    if os.path.exists(txt_path):
        os.remove(txt_path)

    return text



def _audio_callback(indata, frames, time_info, status):
    # called by sounddevice whenever new audio arrives
    _audio_q.put(indata.copy())
    AUDIO_BUFFER.append(indata.copy())  # keep for saving later


SAMPLE_RATE = 16000          # Hz


def _transcribe_worker():
    """Continuously pull audio from the queue and transcribe it with whisper.cpp."""
    global stop_threads
    print("🔊 Audio capture thread started.")
    buffer = np.zeros((0, 1), dtype=np.float32)
    chunk_samples = SAMPLE_RATE * CHUNK_SECONDS

    while not stop_threads:
        try:
            data = _audio_q.get(timeout=1)
            buffer = np.concatenate((buffer, data))

            # once enough audio is accumulated → transcribe
            if len(buffer) >= chunk_samples:
                segment = np.squeeze(buffer[:chunk_samples])
                buffer = buffer[chunk_samples:]  # keep remainder

                # convert numpy array → WAV bytes
                wav_buf = io.BytesIO()
                sf.write(wav_buf, segment, SAMPLE_RATE, format="WAV")
                wav_data = wav_buf.getvalue()

                # call whisper.cpp binary
                text = transcribe_with_whisper_cpp(wav_data)

                 # --- FILTERING LOGIC ---
                if not text:
                    continue  # skip empty output
                if text in ("[BLANK_AUDIO]", "[BLANK]", "(silence)", "[ Silence ]"):
                    continue  # skip placeholder tags
                if text.lower() in ("you", "uh", "ah", "a", "hmm"):
                    continue  # skip filler syllables

                # --- If passed all filters, append ---

                if text:
                    ts = datetime.now().isoformat(timespec='seconds')
                    entry = {"timestamp": ts, "text": text}
                    live_transcript.append(entry)
                    print(f"[{ts}] {text}")

        except queue.Empty:
            # no new audio right now, just wait
            time.sleep(0.05)
            continue

def _capture_loop():
    global stop_threads
    with sd.InputStream(
        channels=1,
        samplerate=SAMPLE_RATE,
        device=DEVICE_INDEX,
        callback=_audio_callback,
        dtype="float32"
    ):
        print("🎙  Listening... (Ctrl+C to stop server)")
        while not stop_threads:
            time.sleep(1)
    print("🛑 Audio capture stopped.")


# Load model once at startup (choose "base", "small", "medium", "large")
whisper_model = whisper.load_model("small")  # good balance for CPU-only
# Create app with lifespan


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup actions ---
    print("🚀 FastAPI starting up...")
    global stop_threads
    
    # (You can start your background audio capture thread here if needed)
    start_audio_streamer()

    yield  # ⬅️ app runs between startup and shutdown
    stop_threads = True
    time.sleep(1.5)  # give threads time to exit cleanly
    save_transcript_and_audio_on_shutdown()

    print("👋 FastAPI shutting down...")

app = FastAPI(lifespan=lifespan)

@app.get("/")
def root():
    return {"message": "FastAPI is running"}

@app.get("/live")
def get_live(since: str = None):
    try:
        if since:
            since_decoded = unquote(since)
            # Accept timestamps like "2025-10-15T12:58:42"
            since_dt = datetime.strptime(since_decoded, "%Y-%m-%dT%H:%M:%S")
            filtered = [
                t for t in live_transcript
                if datetime.strptime(t["timestamp"], "%Y-%m-%dT%H:%M:%S") > since_dt
            ]
            return {"segments": filtered}
        else:
            return {"segments": live_transcript[-100:]}
    except Exception as e:
        print("Error parsing 'since':", e)
        return {"error": "Invalid 'since' format. Expected YYYY-MM-DDTHH:MM:SS"}


def start_audio_streamer():
    """Start both the capture stream and the transcription thread."""
    threading.Thread(target=_transcribe_worker, daemon=True).start()
    threading.Thread(target=_capture_loop, daemon=True).start()

def save_transcript_and_audio_on_shutdown():

    print("💾 Saving transcript and audio on shutdown...")

    if not live_transcript and not AUDIO_BUFFER:
        print("Nothing to save.")
        return

    timestamp = datetime.now().isoformat(timespec='seconds').replace(":", "-")
    base = f"{timestamp}"

    # --- Save transcript ---
    if live_transcript:
        filename = f"transcript_live_{base}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(live_transcript, f, ensure_ascii=False, indent=2)
        print(f"💾 Transcript saved to {filename}")

    # --- Save audio ---
    if AUDIO_BUFFER:
        audio_data = np.concatenate(AUDIO_BUFFER, axis=0)
        audio_file = f"audio_live_{base}.wav"
        write_wav(audio_file, 16000, audio_data)   # 16000 = sample rate
        print(f"🎧 Audio saved to {audio_file}")

client = OpenAI()  # uses your OPENAI_API_KEY env variable
# Allow requests from local browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for local dev only
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/ask")
async def ask_ai(request: Request):
    data = await request.json()
    question = data.get("question", "")

    if not question.strip():
        return {"answer": "(No question text received)"}

    # return {"answer": "Hello from FastAPI! This is a placeholder response."}

    # Call OpenAI model (you can change to gpt-4o, etc.)
    completion = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {"role": "system", "content": "You are acting as you are on a JAVA interview. Answer as you would in real life. Be concise."},
            {"role": "user", "content": question}
        ]
    )

    answer = completion.choices[0].message.content
    return {"answer": answer}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)