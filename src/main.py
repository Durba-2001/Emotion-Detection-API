from fastapi import FastAPI
from src.api.routers import emotion, auth  # Import routers from src/api/routers
from dotenv import load_dotenv,find_dotenv
import os
from slowapi import Limiter,_rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
load_dotenv(find_dotenv())
RATE_LIMIT_REQUESTS = int(os.environ.get("RATE_LIMIT_REQUESTS"))
RATE_LIMIT_WINDOW= int(os.environ.get("RATE_LIMIT_WINDOW"))
RATE_LIMIT = f"{RATE_LIMIT_REQUESTS}/{RATE_LIMIT_WINDOW} second"
# Initialize limiter (global)
limiter = Limiter(key_func=get_remote_address,default_limits=[RATE_LIMIT])

app = FastAPI(title="Emotion Detection API", version="1.0")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(emotion.router, prefix="/api/v1/emotions", tags=["Emotions"])


