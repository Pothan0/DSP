import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
import os

# Import the API
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard.api import create_app

# Initialize system on startup
from main import init_system
import asyncio

app = create_app()

@app.on_event("startup")
async def startup():
    try:
        await init_system()
        print("TrustChain system initialized")
    except Exception as e:
        print(f"Warning: Could not initialize system: {e}")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.get("/")
async def root():
    return FileResponse(os.path.join(BASE_DIR, "templates", "index.html"))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)