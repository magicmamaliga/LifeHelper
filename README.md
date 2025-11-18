Run Dev:
 uvicorn server.main:app --reload --port 8000
 npm run dev

Run Build:
npm:
 npm run build
 npm run electron
 npm run dist

Python:
pyinstaller   --onedir  --add-binary "whisper/whisper-cli.exe;whisper/whisper-cli.exe"  --add-data "whisper/models/ggml-base.en.bin;whisper/models/ggml-base.en.bin" --add-data "dist;dist" lifehelper.py


pyinstaller --onefile --add-data "dist;dist" lifehelper.py   


Run Whisper-cli.exe
& "C:\Users\Mate\Desktop\whisper-cli.exe" -m "C:\Users\Mate\Desktop\whisper.cpp\models\ggml-base.en.bin" -f "C:\Users\Mate\Desktop\LifeHelper\transcripts\session_2025-11-18T13-47-53.wav" 