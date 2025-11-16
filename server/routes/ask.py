from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from ..config import client

router = APIRouter(prefix="/api")

conversation_history = []


@router.post("/ask")
async def ask_ai(request: Request):
    data = await request.json()
    question = data.get("question", "").strip()

    if not question:
        return {"answer": "(No question text received)"}

    conversation_history.append({"role": "user", "content": question})

    def stream():
        partial = ""
        for chunk in client.chat.completions.create(
            model="gpt-4o-mini",
            messages=conversation_history,
            stream=True
        ):
            delta = chunk.choices[0].delta
            if delta and delta.content:
                partial += delta.content
                yield delta.content

        conversation_history.append({"role": "assistant", "content": partial})

    return StreamingResponse(stream(), media_type="text/plain")
