from fastapi import APIRouter

router = APIRouter(prefix="/api")

@router.get("/")
def root():
    return {"message": "FastAPI is running"}
