import os
import sounddevice as sd
from openai import OpenAI
import whisper

import sys


SAMPLE_RATE = 16000
CHUNK_SECONDS = 3
WHISPER_CPP_PATH = r"whisper/whisper-cli.exe"
WHISPER_MODEL = r"whisper/models/ggml-base.en.bin"

 

client = OpenAI()
whisper_model = whisper.load_model("base")

TRANSCRIPTS_DIR = "./transcripts"
STATIC_DIR = "./dist"

os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
