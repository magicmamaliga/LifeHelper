import time
import threading
import queue
import numpy as np
import pyaudiowpatch as pyaudio 

from .transcribe import transcribe_segment 
from .. import config as config 
from ..audio import thread_starter as thread_starter



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
        
    thread_starter.audio_q.put(np_data_float32)
    AUDIO_BUFFER.append(np_data_float32)


def capture_loop():
    chunkSize = 1024  
    if not thread_starter._LOOPBACK_DEVICE_INDEX or not thread_starter._pyaudio_instance:
        print("Error: Loopback device not initialized. Stopping capture loop.")
        return
    print(f"Starting capture stream at {config.SAMPLE_RATE}Hz")

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



