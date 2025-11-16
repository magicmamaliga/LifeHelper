from server.main import app

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting LifeHelper backend...")
    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )
