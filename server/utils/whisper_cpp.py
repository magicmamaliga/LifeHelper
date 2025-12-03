import os
import subprocess


def transcribe_with_whisper_cpp(binary, model, audio_data, tmp):
    tmp_wav = tmp + ".wav"
    txt_path = tmp + ".txt"

    with open(tmp_wav, "wb") as f:
        f.write(audio_data)

    cmd = [
        binary, "-m", model,
        "-f", tmp_wav, "-otxt", "-of", tmp,
        "-t", "8"
    ]

    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    # Handle cases
    if result.returncode == 3221225786:
        cleanup_temp_files(tmp_wav, txt_path)
        return ""

    if result.returncode != 0:
        cleanup_temp_files(tmp_wav, txt_path)
        return ""

    text = ""
    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            text = f.read().strip()
    except FileNotFoundError:
        pass

    cleanup_temp_files(tmp_wav, txt_path)
    return text

def cleanup_temp_files(*paths):
    for path in paths:
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass