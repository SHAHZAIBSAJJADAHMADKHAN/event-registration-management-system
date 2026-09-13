"""Non-feature system endpoints."""

from fastapi import APIRouter, status

router = APIRouter(tags=["system"])


@router.get("/", status_code=status.HTTP_200_OK)
async def root() -> dict[str, str]:
    return {
        "service": "event-management-api",
        "message": "Event Management API foundation is running.",
    }


@router.get("/health", status_code=status.HTTP_200_OK)
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": "event-management-api"}
