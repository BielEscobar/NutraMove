from calendar import monthrange
from datetime import date, timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Student, User, UserRole
from app.models.assessment import Assessment, Measurement
from app.repositories.students import get_student as find_student
from app.repositories.students import scoped_query
from app.schemas.assessment import (
    AssessmentBrief,
    AssessmentList,
    EvolutionCurrent,
    EvolutionResponse,
    HistoryPoint,
    MeasurementSeries,
    Period,
    bmi,
)


def student(
    db: Session, actor: User, student_id: UUID | None = None, *, lock: bool = False
) -> Student:
    result = find_student(db, actor, student_id, lock=lock)
    if result is None:
        raise HTTPException(404, "Aluno não encontrado.")
    return result


def scope(db: Session, actor: User) -> Select[tuple[Assessment]]:
    query = select(Assessment).where(
        Assessment.student_id.in_(scoped_query(db, actor).with_only_columns(Student.id))
    )
    return query


def detail(db: Session, actor: User, assessment_id: UUID, *, lock: bool = False) -> Assessment:
    query = (
        scope(db, actor)
        .where(Assessment.id == assessment_id)
        .options(selectinload(Assessment.measurements))
    )
    result = db.scalar(query)
    if result is None:
        raise HTTPException(404, "Avaliação não encontrada.")
    if lock:
        owner = student(db, actor, result.student_id, lock=True)
        if actor.role == UserRole.PROFESSIONAL and result.professional_id != owner.professional_id:
            raise HTTPException(404, "Avaliação não encontrada.")
        result = db.scalar(
            query.with_for_update(of=Assessment).execution_options(populate_existing=True)
        )
        if result is None:
            raise HTTPException(404, "Avaliação não encontrada.")
    return result


def latest_weight(db: Session, student_id: UUID) -> Assessment | None:
    return db.scalar(
        select(Assessment)
        .where(Assessment.student_id == student_id, Assessment.weight_kg.is_not(None))
        .order_by(
            Assessment.assessment_date.desc(), Assessment.created_at.desc(), Assessment.id.desc()
        )
        .limit(1)
    )


def list_assessments(
    db: Session, actor: User, student_id: UUID | None, page: int, page_size: int
) -> AssessmentList:
    owner = student(db, actor, student_id)
    query = scope(db, actor).where(Assessment.student_id == owner.id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(
        query.order_by(
            Assessment.assessment_date.desc(), Assessment.created_at.desc(), Assessment.id.desc()
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return AssessmentList(
        items=[AssessmentBrief.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def period_start(period: Period, today: date) -> date | None:
    if period == "all":
        return None
    if period.endswith("d"):
        return today - timedelta(days=int(period[:-1]) - 1)
    months = 6 if period == "6m" else 12
    index = today.year * 12 + today.month - 1 - months
    year, month_index = divmod(index, 12)
    month = month_index + 1
    return date(year, month, min(today.day, monthrange(year, month)[1]))


def evolution(
    db: Session, actor: User, student_id: UUID | None, period: Period
) -> EvolutionResponse:
    owner = student(db, actor, student_id)
    base = scope(db, actor).where(Assessment.student_id == owner.id)
    latest = db.scalar(
        base.order_by(
            Assessment.assessment_date.desc(), Assessment.created_at.desc(), Assessment.id.desc()
        ).limit(1)
    )
    current = None
    if latest:
        weight = latest_weight(db, owner.id)
        current = EvolutionCurrent(
            latest_assessment_date=latest.assessment_date,
            weight_kg=weight.weight_kg if weight else None,
            weight_date=weight.assessment_date if weight else None,
            bmi=bmi(weight.weight_kg, weight.height_cm) if weight else None,
        )
    start = period_start(period, date.today())
    query = base if start is None else base.where(Assessment.assessment_date >= start)
    # Select only chart columns; no notes, authors or profile data in the history payload.
    rows = db.execute(
        query.with_only_columns(
            Assessment.id, Assessment.assessment_date, Assessment.weight_kg, Assessment.height_cm
        ).order_by(Assessment.assessment_date, Assessment.created_at, Assessment.id)
    ).all()
    weights = [
        HistoryPoint(assessment_id=r.id, date=r.assessment_date, value=r.weight_kg)
        for r in rows
        if r.weight_kg is not None
    ]
    bmis = []
    for row in rows:
        value = bmi(row.weight_kg, row.height_cm)
        if value is not None:
            bmis.append(HistoryPoint(assessment_id=row.id, date=row.assessment_date, value=value))
    measurements = db.execute(
        select(
            Measurement.measurement_type,
            Measurement.side,
            Measurement.value_cm,
            Assessment.id,
            Assessment.assessment_date,
        )
        .join(Assessment)
        .where(Assessment.id.in_(query.with_only_columns(Assessment.id)))
        .order_by(
            Measurement.measurement_type,
            Measurement.side,
            Assessment.assessment_date,
            Assessment.created_at,
            Assessment.id,
        )
    ).all()
    series: dict[tuple[str, str | None], MeasurementSeries] = {}
    for measurement_row in measurements:
        key = (measurement_row.measurement_type, measurement_row.side)
        if key not in series:
            series[key] = MeasurementSeries(
                measurement_type=measurement_row.measurement_type,
                side=measurement_row.side,
                points=[],
            )
        series[key].points.append(
            HistoryPoint(
                assessment_id=measurement_row.id,
                date=measurement_row.assessment_date,
                value=measurement_row.value_cm,
            )
        )
    return EvolutionResponse(
        current=current,
        weight_history=weights,
        bmi_history=bmis,
        measurements=list(series.values()),
        period=period,
    )
