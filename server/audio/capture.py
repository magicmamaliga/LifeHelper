import time
import threading
import queue
import numpy as np
import signal # NEW: For catching Ctrl+C (SIGINT)
# NEW IMPORTS FOR WASAPI LOOPBACK
import pyaudiowpatch as pyaudio 
# Note: The sounddevice import is removed

# Assuming 'transcribe_segment' is in a sibling module
from .transcribe import transcribe_segment 

## --- Configuration Update ---
SAMPLE_RATE = 16000 # Target rate for transcription
CHUNK_SIZE = 1024   # Buffer size for reading stream data

# PyAudio Configuration (will be updated dynamically)
_FORMAT = pyaudio.paInt16
_CHANNELS = 2 
# ------------------------------

_audio_q = queue.Queue()
AUDIO_BUFFER = []
_stop = False
_LOOPBACK_DEVICE_INDEX = None
_LOOPBACK_RATE = None 

# PyAudio instance is stored here while the context manager is active
_pyaudio_instance = None 

# --- Signal Handling ---

def stop_threads():
    """Sets the global stop flag to terminate all loops."""
    global _stop
    _stop = True

def sigint_handler(signum, frame):
    """Custom handler to set the global stop flag when SIGINT is received."""
    print("\nCaught Ctrl+C (SIGINT). Initiating shutdown...")
    stop_threads()

# --- PyAudioWPatch Device Finding ---

def find_loopback_device(p):
    """
    Finds the WASAPI loopback analogue for the default output device.
    Sets global loopback parameters on success.
    """
    print("--- Attempting to find WASAPI Loopback Device ---")
    global _LOOPBACK_DEVICE_INDEX, _LOOPBACK_RATE, _CHANNELS, _pyaudio_instance
    _pyaudio_instance = p 

    try:
        default_device_index = p.get_default_output_device_info()['index']
    except Exception as e:
        print(f"Error: Could not determine default output device. ({e})")
        return False

    try:
        loopback_info = p.get_wasapi_loopback_analogue_by_index(default_device_index)
        
        _LOOPBACK_DEVICE_INDEX = loopback_info['index']
        _LOOPBACK_RATE = int(loopback_info.get('defaultSampleRate', SAMPLE_RATE)) 
        _CHANNELS = loopback_info.get('maxInputChannels', _CHANNELS)
        
        print(f"✅ Found Loopback Device (Index: {_LOOPBACK_DEVICE_INDEX}): {loopback_info['name']}")
        print(f"   Native Rate: {_LOOPBACK_RATE} Hz, Channels: {_CHANNELS}")
        return True
        
    except Exception as e:
        print("❌ Failed to find the WASAPI Loopback Analogue. Check PyAudioWPatch installation.")
        print(f"Error details: {e}")
        return False

# --- Audio Capture and Processing ---

def _put_data_to_queue(indata):
    """Converts raw bytes to mono float32 numpy array and puts it into the queue."""
    global _CHANNELS
    
    # 1. Convert raw bytes (paInt16) to numpy int16 array
    np_data_int16 = np.frombuffer(indata, dtype=np.int16)
    
    # 2. Convert to float32 (-1.0 to 1.0)
    np_data_float32 = np_data_int16.astype(np.float32) / 32768.0 
    
    # 3. Handle Stereo -> Mono (Mean across channels)
    if _CHANNELS > 1:
        # Reshape to (M, _CHANNELS) and take the mean across channels (axis=1)
        np_data_float32 = np_data_float32.reshape(-1, _CHANNELS).mean(axis=1, keepdims=True)
    elif _CHANNELS == 1:
         np_data_float32 = np_data_float32.reshape(-1, 1)
        
    _audio_q.put(np_data_float32)


def _capture_loop():
    """Blocking capture loop using PyAudio's stream.read()."""
    global _stop, _pyaudio_instance

    if not _LOOPBACK_DEVICE_INDEX or not _pyaudio_instance:
        print("Error: Loopback device not initialized. Stopping capture loop.")
        return

    print(f"Starting capture stream at {_LOOPBACK_RATE}Hz...")

    try:
        stream = _pyaudio_instance.open(format=_FORMAT,
                                        channels=_CHANNELS,
                                        rate=_LOOPBACK_RATE,
                                        input=True,
                                        frames_per_buffer=CHUNK_SIZE,
                                        input_device_index=_LOOPBACK_DEVICE_INDEX)

        while not _stop:
            try:
                # This is a blocking read call
                data = stream.read(CHUNK_SIZE, exception_on_overflow=False) 
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
        print("Capture loop finished.")


def _transcribe_worker():
    global _stop
    buffer = np.zeros((0, 1), dtype=np.float32)
    
    # --- Resampling Setup ---
    # This must be calculated after the loopback rate is found
    if _LOOPBACK_RATE and _LOOPBACK_RATE != SAMPLE_RATE:
        resample_ratio = _LOOPBACK_RATE / SAMPLE_RATE
    else:
        resample_ratio = 1.0
    # ------------------------

    # silence detection
    silence_threshold = 0.005
    silence_window = int(SAMPLE_RATE * 0.2)
    silence_required = 0.8
    silence_limit = int(silence_required / 0.2)
    silence_counter = 0
    speech_detected = False

    max_samples = SAMPLE_RATE * 7
    min_sentence_length = 1.8
    
    print(f"Transcription worker running. Target sample rate: {SAMPLE_RATE} Hz")


    while not _stop:
        try:
            # Data pulled from queue is a (N, 1) float32 array at _LOOPBACK_RATE
            data = _audio_q.get(timeout=1)
            
            # ** CRITICAL: RESAMPLE THE DATA **
            if resample_ratio != 1.0:
                 # WARNING: This simple integer downsampling is for illustration only. 
                 # Use proper resampling (e.g., scipy.signal.resample_poly) for quality.
                 downsample_factor = int(resample_ratio) 
                 if downsample_factor > 1:
                    data = data[::downsample_factor]
            
            # The rest of the logic assumes 'data' is now at SAMPLE_RATE
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
            if not _stop:
                print(f"Error in transcribe worker: {e}")
            break
            

def start_audio_streamer():
    """
    Initializes PyAudioWPatch, registers the SIGINT handler, and starts threads.
    """
    # 1. Register the custom handler for SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, sigint_handler)
    
    try:
        # 2. Initialize PyAudioWPatch context manager
        with pyaudio.PyAudio() as p:
            
            # 3. Find and configure the loopback device
            if not find_loopback_device(p):
                print("Cannot proceed without a valid loopback device.")
                return

            # 4. Start the worker threads
            # Daemon threads will automatically be killed when the main thread exits
            threading.Thread(target=_capture_loop, daemon=True).start()
            time.sleep(0.5) 
            threading.Thread(target=_transcribe_worker, daemon=True).start()
            
            # 5. Main Thread Loop (stays alive and responsive to signals)
            print("Audio streamer threads started. Press Ctrl+C to stop.")
            # The main thread waits here. The SIGINT handler will set _stop=True.
            while not _stop:
                time.sleep(0.1) 
                
    except Exception as e:
        # Only catches initialization errors outside the PyAudio context
        print(f"\nFATAL ERROR: Streamer initialization failed.")
        print(f"Details: {e}")
        
    finally:
        # Ensures all threads are marked for termination and cleanup occurs
        stop_threads() 
        # Wait briefly for threads to finish their cleanup
        time.sleep(0.5) 
        print("Streamer successfully shut down.")

if __name__ == "__main__":
    start_audio_streamer()