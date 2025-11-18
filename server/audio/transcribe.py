import io
import numpy as np
import tempfile
from datetime import datetime
import soundfile as sf

from ..config import SAMPLE_RATE, WHISPER_CPP_PATH, WHISPER_MODEL
from ..utils.whisper_cpp import transcribe_with_whisper_cpp
from .state import add_to_transcript
from ..routes.static import resource_path

def valid_text(text: str) -> bool:
    if not text:
        return False
    t = text.strip().lower()
    if t in ("[blank_audio]", "[blank]", "(silence)", "[ silence ]"):
        return False
    if t in ("you", "uh", "ah", "a", "hmm"):
        return False
    return True


def transcribe_segment(segment: np.ndarray):
    wav_buf = io.BytesIO()
    sf.write(wav_buf, segment, SAMPLE_RATE, format="WAV")
    data = wav_buf.getvalue()

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmpname = tmp.name
    print("Transcribing segment...")
    print(  resource_path(WHISPER_CPP_PATH), WHISPER_MODEL, tmpname  )
    text = transcribe_with_whisper_cpp(
        resource_path(WHISPER_CPP_PATH), resource_path(WHISPER_MODEL), data, tmpname
    )

    if not valid_text(text):
        return

    ts = datetime.now().isoformat(timespec="seconds")
    add_to_transcript({"timestamp": ts, "text": text})
    print(f"[{ts}] {text}")
