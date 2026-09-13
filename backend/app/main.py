"""FastAPI application factory for the Event Management API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.admin_events import router as admin_events_router
from app.api.routes.admin_operations import router as admin_operations_router
from app.api.routes.discovery import router as discovery_router
from app.api.routes.registrations import router as registrations_router
from app.api.routes.system import router as system_router
from app.core.config import get_settings
from app.core.errors import APIError, api_error_handler, unexpected_error_handler


def create_application() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Event Management API",
        version="0.1.0",
        description="Backend foundation with Supabase JWT authentication enforcement.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.frontend_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)
    # Vercel Services forwards the original /api/* path to FastAPI. Register
    # the existing routers once beneath that public prefix rather than relying
    # on deployment-time path rewriting.
    app.include_router(system_router, prefix="/api")
    app.include_router(auth_router, prefix="/api")
    app.include_router(admin_events_router, prefix="/api")
    app.include_router(admin_operations_router, prefix="/api")
    app.include_router(discovery_router, prefix="/api")
    app.include_router(registrations_router, prefix="/api")
    return app


app = create_application()
