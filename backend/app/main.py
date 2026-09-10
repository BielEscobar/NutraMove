from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.dashboards import router as dashboards_router
from app.api.diets import master_router as master_diets_router
from app.api.diets import professional_router as professional_diets_router
from app.api.diets import student_router as student_diets_router
from app.api.health import router as health_router
from app.api.professionals import router as professionals_router
from app.api.students import master_router as master_students_router
from app.api.students import professional_router as professional_students_router
from app.api.students import router as students_router
from app.core.config import Settings, get_settings
from app.core.errors import SafeErrorMiddleware, register_error_handlers


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    def configured_settings() -> Settings:
        return settings

    app = FastAPI(title=settings.app_name, debug=False)
    app.dependency_overrides[get_settings] = configured_settings
    app.add_middleware(SafeErrorMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Content-Type"],
    )
    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(professionals_router)
    app.include_router(students_router)
    app.include_router(master_students_router)
    app.include_router(professional_students_router)
    app.include_router(dashboards_router)
    app.include_router(professional_diets_router)
    app.include_router(master_diets_router)
    app.include_router(student_diets_router)
    return app
