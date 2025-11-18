Run Dev:
 uvicorn server.main:app --reload --port 8000
 npm run dev

Run Build:
npm:
 npm run build
 npm run electron
 npm run dist

Python:
pyinstaller --onedir --add-data "dist;dist" lifehelper.py   
pyinstaller --onefile --add-data "dist;dist" lifehelper.py   