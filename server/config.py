import os
import sounddevice as sd
from openai import OpenAI
import whisper

import sys


SAMPLE_RATE = 16000
CHUNK_SECONDS = 3

WHISPER_CPP_PATH = r"C:\Users\Mate\Desktop\whisper.cpp\build\bin\whisper-cli.exe"
WHISPER_MODEL = r"C:\Users\Mate\Desktop\whisper.cpp\models\ggml-base.en.bin"

DEVICE_INDEX = next(
    i for i, d in enumerate(sd.query_devices())
    if "CABLE Output" in d["name"]
)

client = OpenAI()
whisper_model = whisper.load_model("base")

TRANSCRIPTS_DIR = "./transcripts"
STATIC_DIR = "./dist"

os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
