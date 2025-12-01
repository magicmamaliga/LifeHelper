import pyaudiowpatch as pyaudio
import wave
import numpy as np
import time

# --- Configuration ---
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
RECORD_SECONDS = 5
OUTPUT_FILENAME = "bluetooth_capture.wav"
# ---------------------

def find_loopback_device(p):
    """
    Lists all devices and attempts to find a suitable WASAPI loopback device.
    """
    print("--- Listing Audio Devices (PyAudioWPatch) ---")
    
    # 1. Get default output device info
    try:
        default_device_index = p.get_default_output_device_info()['index']
    except Exception as e:
        print(f"Error: Could not determine default output device. Please ensure an audio output device is connected and active. ({e})")
        return None, None

    # 2. Find the loopback analogue for the default output
    try:
        # PyAudioWPatch adds this specific method to find the loopback device
        loopback_info = p.get_wasapi_loopback_analogue_by_index(default_device_index)
        
        device_name = loopback_info['name']
        device_index = loopback_info['index']
        
        print(f"\n✅ Found Loopback Device (Index: {device_index}): {device_name}")
        print("This device is the monitoring source for your current default speaker/headphone output.")
        print("We will attempt to record from this device.")
        
        return device_index, device_name
        
    except Exception as e:
        print("\n❌ Failed to find the WASAPI Loopback Analogue for the default output device.")
        print("This might happen if PyAudioWPatch is not correctly installed or if the device does not fully support WASAPI loopback.")
        print(f"Error details: {e}")
        return None, None


def record_audio(device_index, device_name):
    """
    Records audio from the specified loopback device.
    """
    p = pyaudio.PyAudio()
    
    try:
        print(f"\n--- Starting 5-second recording from: {device_name} ---")
        
        # Open a stream using the detected loopback device index
        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK,
                        input_device_index=device_index)

        frames = []
        
        # Use a simple time-based loop for recording
        for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            # You MUST read the data in the loop
            data = stream.read(CHUNK, exception_on_overflow=False) 
            frames.append(data)
            
        print("--- Recording finished. ---")

        # Stop and close the stream
        stream.stop_stream()
        stream.close()

        # Save the captured audio data to a WAV file
        wf = wave.open(OUTPUT_FILENAME, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        
        print(f"\nSuccess! Audio saved to {OUTPUT_FILENAME}")
        print("Please play this file back and listen for the system audio (music, video, etc.) that was playing during the 5 seconds.")

    except Exception as e:
        print(f"\nAn error occurred during recording: {e}")
        print("Please ensure your audio is playing, and the default output device is correct.")
    finally:
        # Always terminate PyAudio
        p.terminate()

def main():
    """
    Main function to initialize PyAudioWPatch and run the test.
    """
    try:
        # Use the context manager provided by PyAudioWPatch
        # This ensures the PyAudio instance is properly initialized and cleaned up
        with pyaudio.PyAudio() as p:
            # 1. Find the loopback device
            loopback_index, loopback_name = find_loopback_device(p)
            
            if loopback_index is not None:
                # 2. Check if something is playing right now
                print("\n*** ACTION REQUIRED ***")
                print("Start playing some music or a video on your computer NOW.")
                print(f"The recording will start in 3 seconds and last for {RECORD_SECONDS} seconds.")
                time.sleep(3)
                
                # 3. Perform the recording
                record_audio(loopback_index, loopback_name)
            else:
                print("\nCannot proceed with recording test without a valid loopback device.")
                print("Ensure you are running this script on a Windows machine and that PyAudioWPatch is correctly installed.")

    except Exception as e:
        print(f"\nFATAL ERROR: PyAudioWPatch initialization failed. Are all dependencies installed?")
        print(f"Details: {e}")

if __name__ == "__main__":
    main()