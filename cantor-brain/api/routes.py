from fastapi import APIRouter

router = APIRouter()

# Import and include sub-routers
from api.devices import router as devices_router
from api.cantors import router as cantors_router

router.include_router(devices_router)
router.include_router(cantors_router)


@router.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint to verify system status."""
    return {"status": "ok", "message": "Cantor Brain is healthy"}