import time
import threading
import queue
import pyaudiowpatch as pyaudio 

from .. import config as config 
from .capture import _capture_loop, _transcribe_worker

_stop = False
_pyaudio_instance = pyaudio.PyAudio() 
_CHANNELS = 2
_LOOPBACK_DEVICE_INDEX = None

def start_audio_streamer():
    """
    Initializes PyAudioWPatch, registers the SIGINT handler, and starts threads.
    """
    global _pyaudio_instance, _stop
    
    _stop = False
    try:
        _pyaudio_instance = pyaudio.PyAudio()
    except Exception as e:
        print(f"\nFATAL ERROR: PyAudio initialization failed. Details: {e}")
        return False

    # 2. Find and configure the loopback device
    if not find_loopback_device():
        print("Cannot proceed without a valid loopback device. Terminating audio.")
        _pyaudio_instance.terminate() 
        _pyaudio_instance = None 
        return False
    
    threading.Thread(target=_capture_loop, daemon=True).start()
    threading.Thread(target=_transcribe_worker, daemon=True).start()


def stop_threads():
    global _stop
    _stop = True

# --- PyAudioWPatch Device Finding ---
def find_loopback_device():
    global _LOOPBACK_DEVICE_INDEX, _CHANNELS, _pyaudio_instance

    try:
        default_device_index = _pyaudio_instance.get_default_output_device_info()['index']
    except Exception as e:
        print(f"Error: Could not determine default output device. ({e})")
        return False

    try:
        loopback_info = _pyaudio_instance.get_wasapi_loopback_analogue_by_index(default_device_index)
        
        _LOOPBACK_DEVICE_INDEX = loopback_info['index']
        config.SAMPLE_RATE = int(loopback_info.get('defaultSampleRate', config.SAMPLE_RATE)) 
        _CHANNELS = loopback_info.get('maxInputChannels', _CHANNELS)
        
        print(f"✅ Found Loopback Device (Index: {_LOOPBACK_DEVICE_INDEX}): {loopback_info['name']}")
        print(f"   Native Rate: {config.SAMPLE_RATE} Hz, Channels: {_CHANNELS}")
        return True
        
    except Exception as e:
        print(f"Error details: {e}")
        return False