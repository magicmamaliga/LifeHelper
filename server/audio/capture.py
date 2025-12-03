import time
import threading
import queue
import numpy as np
import pyaudiowpatch as pyaudio 

from .transcribe import transcribe_segment 
from .. import config as config 
from ..audio import thread_starter as thread_starter


_audio_q = queue.Queue()
AUDIO_BUFFER = []


# --- Audio Capture and Processing ---
def _put_data_to_queue(indata):
    """Converts raw bytes to mono float32 numpy array and puts it into the queue."""
    
    # 1. Convert raw bytes (paInt16) to numpy int16 array
    np_data_int16 = np.frombuffer(indata, dtype=np.int16)
    
    # 2. Convert to float32 (-1.0 to 1.0)
    np_data_float32 = np_data_int16.astype(np.float32) / 32768.0 
    
    # 3. Handle Stereo -> Mono (Mean across channels)
    if thread_starter._CHANNELS > 1:
        # Reshape to (M, thread_starter._CHANNELS) and take the mean across channels (axis=1)
        np_data_float32 = np_data_float32.reshape(-1, thread_starter._CHANNELS).mean(axis=1, keepdims=True)
    elif thread_starter._CHANNELS == 1:
         np_data_float32 = np_data_float32.reshape(-1, 1)
        
    _audio_q.put(np_data_float32)
    AUDIO_BUFFER.append(np_data_float32)


def _capture_loop():
    print("Capture loop thread started...........................")
    """Blocking capture loop using PyAudio's stream.read()."""
    
    chunkSize = 1024  

    if not thread_starter._LOOPBACK_DEVICE_INDEX or not thread_starter._pyaudio_instance:
        print("Error: Loopback device not initialized. Stopping capture loop.")
        return

    print(f"Starting capture stream at {config.SAMPLE_RATE}Hz...")

    try:
        stream = thread_starter._pyaudio_instance.open(format= pyaudio.paInt16,
                                        channels=thread_starter._CHANNELS,
                                        rate=config.SAMPLE_RATE,
                                        input=True,
                                        frames_per_buffer=chunkSize,
                                        input_device_index=thread_starter._LOOPBACK_DEVICE_INDEX)

        while not thread_starter._stop:
            try:
                # This is a blocking read call
                data = stream.read(chunkSize, exception_on_overflow=False) 
                _put_data_to_queue(data)
                
            except IOError as e:
                # Handle stream I/O errors
                if e.errno == -9981: 
                    print(f"Stream error in capture loop: {e}")
                else:
                    raise e
                break
            except Exception as e:
                print(f"Unexpected error in capture loop: {e}")
                break

    except Exception as e:
        print(f"Failed to open PyAudio stream: {e}")
    finally:
        if 'stream' in locals() and stream.is_active():
            stream.stop_stream()
            stream.close()
        print("Capture loop finished. ")


def _transcribe_worker():
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
            data = _audio_q.get(timeout=1)
            
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
            

