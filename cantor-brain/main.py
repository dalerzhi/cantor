import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router as api_router
from core.redis_client import init_redis, close_redis, subscribe_to_device_events

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_redis()
    task = asyncio.create_task(subscribe_to_device_events())
    yield
    # Shutdown
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    await close_redis()

app = FastAPI(title="Cantor Brain", version="1.0.0", lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
