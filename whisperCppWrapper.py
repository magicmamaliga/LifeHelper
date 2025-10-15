import subprocess
import tempfile
import os

WHISPER_CPP_PATH = r"C:\Users\Mate\Desktop\whisper.cpp\build\bin\whisper-cli.exe"
WHISPER_MODEL = r"C:\Users\Mate\Desktop\whisper.cpp\models\ggml-base.en.bin"

def transcribe_with_whisper_cpp(audio_data, sample_rate=16000):
    """Transcribe raw audio bytes with whisper.cpp binary."""
    # print(audio_data )
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
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    with open(txt_path, "r", encoding="utf-8") as f:
        text = f.read().strip()

    os.remove(tmp_path)
    os.remove(txt_path)
    return text
