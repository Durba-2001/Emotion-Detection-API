from fastapi import FastAPI
from src.api.routers import emotion, auth  # Import routers from src/api/routers

app = FastAPI(title="Emotion Detection API", version="1.0")
# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(emotion.router, prefix="/api/v1/emotions", tags=["Emotions"])


