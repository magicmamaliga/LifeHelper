import subprocess, threading, queue, numpy as np, time, io, soundfile as sf

class WhisperCppStreamer:
    """
    Streamer for whisper.cpp that sends complete WAV chunks to stdin (-f -)
    """

    def __init__(self, exe_path, model_path, threads=8):
        self.exe_path = exe_path
        self.model_path = model_path
        self.threads = str(threads)
        self.process = None
        self.output_queue = queue.Queue()
        self.stop_flag = False

    def start(self):
        cmd = [
            self.exe_path,
            "-m", self.model_path,
            "-f", "-",        # read WAV data from stdin
            "-otxt",          # plain text output
            "-t", self.threads,
            "-nt",            # no timestamps
            "-np",            # no progress bars
        ]
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0
        )
        threading.Thread(target=self._read_output, daemon=True).start()
        print("🚀 whisper.cpp streaming process started (WAV over stdin mode).")

    def _read_output(self):
        """Read stdout lines from whisper.cpp"""
        while not self.stop_flag:
            line = self.process.stdout.readline()
            if not line:
                time.sleep(0.05)
                continue
            text = line.decode("utf-8", errors="ignore").strip()
            if text:
                self.output_queue.put(text)

    def transcribe_chunk(self, audio_chunk, sample_rate=16000):
        """Send one full WAV block to whisper.cpp and return any output."""
        if self.process is None:
            raise RuntimeError("Streamer not started")

        # Create an in-memory WAV (header + samples)
        wav_buf = io.BytesIO()
        sf.write(wav_buf, audio_chunk, sample_rate, format="WAV", subtype="PCM_16")
        wav_data = wav_buf.getvalue()

        # Write the entire WAV to stdin
        try:
            self.process.stdin.write(wav_data)
            self.process.stdin.flush()
        except BrokenPipeError:
            return ""

        # Collect any output
        texts = []
        while not self.output_queue.empty():
            texts.append(self.output_queue.get_nowait())

        return " ".join(texts)

    def stop(self):
        self.stop_flag = True
        if self.process:
            try:
                self.process.stdin.close()
            except Exception:
                pass
            self.process.terminate()
            self.process.wait(timeout=5)
        print("🛑 whisper.cpp streamer stopped.")
