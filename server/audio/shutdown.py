import os
import json
import numpy as np
from datetime import datetime
from scipy.io.wavfile import write as write_wav

from .capture import AUDIO_BUFFER
from .state import get_live_transcript
from ..config import SAMPLE_RATE, TRANSCRIPTS_DIR


def save_transcript_and_audio_on_shutdown():
    transcript = get_live_transcript()
    if not transcript and not AUDIO_BUFFER:
        return

    timestamp = datetime.now().isoformat(timespec='seconds').replace(":", "-")
    base = os.path.join(TRANSCRIPTS_DIR, f"session_{timestamp}")

    # save transcript
    if transcript:
        with open(base + ".json", "w", encoding="utf-8") as f:
            json.dump(transcript, f, ensure_ascii=False, indent=2)
        print(f"💾 Transcript saved to {base}.json")

    if AUDIO_BUFFER:
        audio = np.concatenate(AUDIO_BUFFER, axis=0)
        write_wav(base + ".wav", SAMPLE_RATE, audio)
        print(f"🎧 Audio saved to {base}.wav")
