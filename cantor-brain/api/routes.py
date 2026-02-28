from fastapi import APIRouter

router = APIRouter()

@router.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint to verify system status."""
    return {"status": "ok", "message": "Cantor Brain is healthy"}
