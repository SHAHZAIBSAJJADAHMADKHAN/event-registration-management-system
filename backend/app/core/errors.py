"""Small, reusable API error primitives."""

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


class APIError(Exception):
    """A safe error that routes and services may intentionally return."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


async def api_error_handler(_: Request, error: APIError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"error": {"code": error.code, "message": error.message}},
    )


async def unexpected_error_handler(_: Request, __: Exception) -> JSONResponse:
    """Avoid exposing internal exception details to API clients."""
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "message": "An unexpected error occurred."}},
    )
