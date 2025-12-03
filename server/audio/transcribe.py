import io
import numpy as np
import tempfile
import soundfile as sf
import time
import queue

from datetime import datetime
from .. import config as config
from ..config import  WHISPER_CPP_PATH, WHISPER_MODEL
from ..utils.whisper_cpp import transcribe_with_whisper_cpp
from ..utils.state import add_to_transcript
from ..routes.static import resource_path
from . import thread_starter

def transcribe_worker():
    buffer = np.zeros((0, 1), dtype=np.float32)
    
    resample_ratio = 1.0

    # silence detection
    silence_threshold = 0.005
    silence_window = int(config.SAMPLE_RATE * 0.2)
    silence_required = 0.8
    silence_limit = int(silence_required / 0.2)
    silence_counter = 0
    speech_detected = False

    max_samples = config.SAMPLE_RATE * 7
    min_sentence_length = 1.8
    
    print(f"Transcription worker running. Target sample rate: {config.SAMPLE_RATE} Hz")

    while not thread_starter._stop:
        try:
            # Data pulled from queue is a (N, 1) float32 array at config.SAMPLE_RATE
            data = thread_starter.audio_q.get(timeout=1)
            
            # ** CRITICAL: RESAMPLE THE DATA **
            if resample_ratio != 1.0:
                 # WARNING: This simple integer downsampling is for illustration only. 
                 # Use proper resampling (e.g., scipy.signal.resample_poly) for quality.
                 downsample_factor = int(resample_ratio) 
                 if downsample_factor > 1:
                    data = data[::downsample_factor]
            
            # The rest of the logic assumes 'data' is now at config.SAMPLE_RATE
            buffer = np.concatenate((buffer, data))

            if len(buffer) >= silence_window:
                recent = buffer[-silence_window:]
                rms = (recent**2).mean()**0.5

                if rms > silence_threshold:
                    silence_counter = 0
                    speech_detected = True
                else:
                    if speech_detected:
                        silence_counter += 1

                total_duration = len(buffer) / config.SAMPLE_RATE

                # finalize segment
                if speech_detected and silence_counter >= silence_limit and total_duration >= min_sentence_length:
                    segment = buffer.copy().flatten()
                    buffer = np.zeros((0,1), dtype=np.float32)
                    silence_counter = 0
                    speech_detected = False
                    transcribe_segment(segment) 
                    continue

                # finalize segment due to maximum length
                if len(buffer) >= max_samples:
                    segment = buffer[:max_samples].flatten()
                    buffer = buffer[max_samples:]
                    silence_counter = 0
                    speech_detected = False
                    transcribe_segment(segment)
                    continue

        except queue.Empty:
            time.sleep(0.05)
        except Exception as e:
            if not thread_starter._stop:
                print(f"Error in transcribe worker: {e}")
            break
            


def transcribe_segment(segment: np.ndarray):
    wav_buf = io.BytesIO()
    sf.write(wav_buf, segment, config.SAMPLE_RATE, format="WAV")
    data = wav_buf.getvalue()

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmpname = tmp.name
    text = transcribe_with_whisper_cpp(
        resource_path(WHISPER_CPP_PATH), resource_path(WHISPER_MODEL), data, tmpname
    )

    if not valid_text(text):
        return

    ts = datetime.now().isoformat(timespec="seconds")
    add_to_transcript({"timestamp": ts, "text": text})
    print(f"[{ts}] {text}")


def valid_text(text: str) -> bool:
    if not text:
        return False
    t = text.strip().lower()
    if t in ("[blank_audio]", "[blank]", "(silence)", "[ silence ]"):
        return False
    if t in ("you", "uh", "ah", "a", "hmm"):
        return False
    return True
