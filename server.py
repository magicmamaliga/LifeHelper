# server.py
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import whisper
import tempfile
import os

# Load model once at startup (choose "base", "small", "medium", "large")
whisper_model = whisper.load_model("small")  # good balance for CPU-only

client = OpenAI()  # uses your OPENAI_API_KEY env variable
app = FastAPI()

# Allow requests from local browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for local dev only
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    # Save temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    # Transcribe
    result = whisper_model.transcribe(tmp_path, fp16=False)
    os.remove(tmp_path)

    # Build response (keep only text + segments)
    response = {
        "text": result["text"].strip(),
        "segments": [
            {"start": seg["start"], "end": seg["end"], "text": seg["text"].strip()}
            for seg in result["segments"]
        ],
    }
    return response


@app.post("/ask")
async def ask_ai(request: Request):
    data = await request.json()
    question = data.get("question", "")

    if not question.strip():
        return {"answer": "(No question text received)"}

    return {"answer": "Hello from FastAPI! This is a placeholder response."}

    # Call OpenAI model (you can change to gpt-4o, etc.)
    # completion = client.chat.completions.create(
    #     model="gpt-4o-mini",
    #     messages=[
    #         {"role": "system", "content": "You are an assistant answering transcript-related questions."},
    #         {"role": "user", "content": question}
    #     ]
    # )

    # answer = completion.choices[0].message.content
    # return {"answer": answer}
