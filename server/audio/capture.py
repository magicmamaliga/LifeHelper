import time
import threading
import queue
import numpy as np
import sounddevice as sd

from ..config import SAMPLE_RATE, DEVICE_INDEX
from .transcribe import transcribe_segment

_audio_q = queue.Queue()
AUDIO_BUFFER = []
_stop = False


def stop_threads():
    global _stop
    _stop = True



def _audio_callback(indata, frames, time_info, status):
    _audio_q.put(indata.copy())
    AUDIO_BUFFER.append(indata.copy())


def _capture_loop():
    global _stop
    with sd.InputStream(
        channels=1,
        samplerate=SAMPLE_RATE,
        device=DEVICE_INDEX,
        callback=_audio_callback,
        dtype="float32"
    ):
        while not _stop:
            time.sleep(0.1)


def _transcribe_worker():
    global _stop
    buffer = np.zeros((0, 1), dtype=np.float32)

    # silence detection
    silence_threshold = 0.005
    silence_window = int(SAMPLE_RATE * 0.2)
    silence_required = 0.8
    silence_limit = int(silence_required / 0.2)
    silence_counter = 0
    speech_detected = False

    max_samples = SAMPLE_RATE * 7
    min_sentence_length = 1.8

    while not _stop:
        try:
            data = _audio_q.get(timeout=1)
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

                total_duration = len(buffer) / SAMPLE_RATE

                # finalize
                if speech_detected and silence_counter >= silence_limit and total_duration >= min_sentence_length:
                    segment = buffer.copy().flatten()
                    buffer = np.zeros((0,1), dtype=np.float32)
                    silence_counter = 0
                    speech_detected = False
                    transcribe_segment(segment)
                    continue

                if len(buffer) >= max_samples:
                    segment = buffer[:max_samples].flatten()
                    buffer = buffer[max_samples:]
                    silence_counter = 0
                    speech_detected = False
                    transcribe_segment(segment)
                    continue

        except queue.Empty:
            time.sleep(0.05)


def start_audio_streamer():
    threading.Thread(target=_capture_loop, daemon=True).start()
    threading.Thread(target=_transcribe_worker, daemon=True).start()
