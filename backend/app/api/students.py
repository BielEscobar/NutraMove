from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import CurrentUser, DbSession, require_roles, require_trusted_origin
from app.api.professionals import no_cache
from app.models import UserRole
from app.repositories import students
from app.schemas.student import (
    MasterStudentFilters,
    StudentCreate,
    StudentFilters,
    StudentList,
    StudentRegistrationResponse,
    StudentResponse,
    StudentUpdate,
)
from app.services import students as service

router = APIRouter(tags=["students"], dependencies=[Depends(no_cache)])
master_router = APIRouter(
    prefix="/master/students",
    tags=["master students"],
    dependencies=[Depends(require_roles(UserRole.MASTER)), Depends(no_cache)],
)
professional_router = APIRouter(
    prefix="/professional/students",
    tags=["professional students"],
    dependencies=[Depends(require_roles(UserRole.PROFESSIONAL)), Depends(no_cache)],
)


@router.post(
    "/students/register",
    status_code=201,
    response_model=StudentRegistrationResponse,
    dependencies=[Depends(require_trusted_origin)],
)
def register(data: StudentCreate, db: DbSession) -> StudentRegistrationResponse:
    student = service.create(db, data)
    return StudentRegistrationResponse(status=student.status)


@router.get(
    "/students/me",
    response_model=StudentResponse,
    dependencies=[Depends(require_roles(UserRole.STUDENT))],
)
def me(db: DbSession, actor: CurrentUser) -> StudentResponse:
    return service.response(service.get(db, actor))


@master_router.get("", response_model=StudentList)
def master_list(
    db: DbSession, actor: CurrentUser, filters: Annotated[MasterStudentFilters, Query()]
) -> StudentList:
    items, total = students.list_students(db, actor, filters)
    return StudentList(
        items=[service.brief(item) for item in items],
        total=total,
        page=filters.page,
        page_size=filters.page_size,
    )


@master_router.get("/{student_id}", response_model=StudentResponse)
def master_detail(student_id: UUID, db: DbSession, actor: CurrentUser) -> StudentResponse:
    return service.response(service.get(db, actor, student_id))


@master_router.patch("/{student_id}", response_model=StudentResponse)
def master_update(
    student_id: UUID, data: StudentUpdate, db: DbSession, actor: CurrentUser
) -> StudentResponse:
    return service.response(service.update(db, actor, student_id, data))


@master_router.post("/{student_id}/approve", response_model=StudentResponse)
def master_approve(student_id: UUID, db: DbSession, actor: CurrentUser) -> StudentResponse:
    return service.response(service.transition(db, actor, student_id, "approve"))


@master_router.post("/{student_id}/reject", response_model=StudentResponse)
def master_reject(student_id: UUID, db: DbSession, actor: CurrentUser) -> StudentResponse:
    return service.response(service.transition(db, actor, student_id, "reject"))


@master_router.post("/{student_id}/activate", response_model=StudentResponse)
def master_activate(student_id: UUID, db: DbSession, actor: CurrentUser) -> StudentResponse:
    return service.response(service.transition(db, actor, student_id, "activate"))


@master_router.post("/{student_id}/deactivate", response_model=StudentResponse)
def master_deactivate(student_id: UUID, db: DbSession, actor: CurrentUser) -> StudentResponse:
    return service.response(service.transition(db, actor, student_id, "deactivate"))


@professional_router.get("", response_model=StudentList)
def professional_list(
    db: DbSession, actor: CurrentUser, filters: Annotated[StudentFilters, Query()]
) -> StudentList:
    items, total = students.list_students(db, actor, filters)
    return StudentList(
        items=[service.brief(item) for item in items],
        total=total,
        page=filters.page,
        page_size=filters.page_size,
    )


@professional_router.get("/{student_id}", response_model=StudentResponse)
def professional_detail(student_id: UUID, db: DbSession, actor: CurrentUser) -> StudentResponse:
    return service.response(service.get(db, actor, student_id))


@professional_router.patch("/{student_id}", response_model=StudentResponse)
def professional_update(
    student_id: UUID, data: StudentUpdate, db: DbSession, actor: CurrentUser
) -> StudentResponse:
    return service.response(service.update(db, actor, student_id, data))


@professional_router.post("/{student_id}/approve", response_model=StudentResponse)
def professional_approve(student_id: UUID, db: DbSession, actor: CurrentUser) -> StudentResponse:
    return service.response(service.transition(db, actor, student_id, "approve"))


@professional_router.post("/{student_id}/reject", response_model=StudentResponse)
def professional_reject(student_id: UUID, db: DbSession, actor: CurrentUser) -> StudentResponse:
    return service.response(service.transition(db, actor, student_id, "reject"))


@professional_router.post("/{student_id}/activate", response_model=StudentResponse)
def professional_activate(student_id: UUID, db: DbSession, actor: CurrentUser) -> StudentResponse:
    return service.response(service.transition(db, actor, student_id, "activate"))


@professional_router.post("/{student_id}/deactivate", response_model=StudentResponse)
def professional_deactivate(student_id: UUID, db: DbSession, actor: CurrentUser) -> StudentResponse:
    return service.response(service.transition(db, actor, student_id, "deactivate"))
