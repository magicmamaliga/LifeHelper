from openai import OpenAI


SAMPLE_RATE = 16000
WHISPER_CPP_PATH = r"whisper/whisper-cli.exe"
WHISPER_MODEL = r"whisper/models/ggml-base.en.bin"
TRANSCRIPTS_DIR = r"./transcripts"
STATIC_DIR = r"./dist"
 

client = OpenAI()
