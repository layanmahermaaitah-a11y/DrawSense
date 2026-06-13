import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import models
from app.database import engine
from app.routers import auth, drawings
from app.ai_logic import load_drawsense_model

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI): 

    print("Starting DrawSense API & Initializing Resources...")
    models.Base.metadata.create_all(bind=engine)

    os.makedirs("assets/drawings", exist_ok=True)
    os.makedirs("models", exist_ok=True)
    os.makedirs("assets/avatars", exist_ok=True)

    try:
        load_drawsense_model()
        print("✅ AI Model Loaded Successfully")
    except Exception as e:
        print(f"Error loading AI Model: {e}")
    yield  
    print("Stopping DrawSense API...")


app = FastAPI(
    title="DrawSense API",
    description="Backend for AI-powered children's drawing analysis",
    version="1.0.0",
    lifespan=lifespan
)

# الإعدادات لـ CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




app.include_router(auth.router, prefix="/auth")
app.include_router(drawings.router, tags=["Drawings Analysis"])

app.mount("/assets", StaticFiles(directory="assets"), name="assets")
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")


@app.get("/", tags=["General"])
def home():
    return {
        "message": "DrawSense API is online",
        "status": "active",
        "documentation": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)