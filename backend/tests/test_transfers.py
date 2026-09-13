from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import Engine, event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Professional, Student, StudentStatus, User, UserRole
from app.models.assessment import Assessment
from app.models.audit_log import AuditAction, AuditLog
from app.models.reevaluation import ReevaluationRequest, ReevaluationStatus
from app.schemas.audit_log import StudentTransfer
from app.services.transfers import transfer
from tests.test_assessments import ORIGIN, Family, login, make_student
from tests.test_assessments import content as assessment_fixture
from tests.test_assessments import family as family_fixture
from tests.test_diets import content as diet_fixture
from tests.test_workouts import content as workout_fixture

family = family_fixture
assessment_content = assessment_fixture
diet_content = diet_fixture
workout_content = workout_fixture


def payload(
    old: str | None, new: str, reason: str = "Reorganização administrativa"
) -> dict[str, str | None]:
    return {
        "expected_professional_id": old,
        "new_professional_id": new,
        "reason": reason,
    }


def move(client: TestClient, family: Family, student: Student | None = None) -> Response:
    student = student or family.student_a
    login(client, family.master)
    return client.post(
        f"/master/students/{student.id}/transfer",
        headers=ORIGIN,
        json=payload(
            str(student.professional_id) if student.professional_id else None, str(family.b.id)
        ),
    )


def test_transfer_and_audit(client: TestClient, family: Family, db: Session) -> None:
    student = family.student_a
    old_id = student.professional_id
    result = move(client, family)
    assert result.status_code == 200, result.text
    db.refresh(student)
    assert student.professional_id == family.b.id
    assert student.status == StudentStatus.ACTIVE
    audit = db.scalar(select(AuditLog))
    assert audit is not None
    assert audit.action == AuditAction.STUDENT_TRANSFERRED
    assert audit.actor_user_id == family.master.id
    assert audit.old_professional_id == old_id
    assert audit.new_professional_id == family.b.id
    assert audit.reason == "Reorganização administrativa"
    assert result.json()["audit_log_id"] == str(audit.id)
    listed = client.get("/master/audit-logs")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["old_professional_name"] == "a"
    assert client.get(f"/master/audit-logs/{audit.id}").status_code == 200
    assert client.get("/master/audit-logs?action=STUDENT_TRANSFERRED").json()["total"] == 1
    assert client.get(f"/master/audit-logs?resource_id={uuid4()}").json()["total"] == 0
    assert client.get("/master/audit-logs?page_size=0").status_code == 422


def test_assign_unassigned(client: TestClient, family: Family, db: Session) -> None:
    family.student_a.professional_id = None
    db.commit()
    response = move(client, family)
    assert response.status_code == 200, response.text
    audit = db.scalar(select(AuditLog))
    assert audit is not None
    assert audit.action == AuditAction.STUDENT_ASSIGNED
    assert audit.old_professional_id is None
    assert family.student_a.status == StudentStatus.ACTIVE


@pytest.mark.parametrize("status", [StudentStatus.PENDING_APPROVAL, StudentStatus.INACTIVE])
def test_status_preserved(
    client: TestClient, family: Family, db: Session, status: StudentStatus
) -> None:
    family.student_a.status = status
    db.commit()
    assert move(client, family).status_code == 200
    db.refresh(family.student_a)
    assert family.student_a.status == status


def test_rejected_blocked(client: TestClient, family: Family, db: Session) -> None:
    family.student_a.status = StudentStatus.REJECTED
    db.commit()
    assert move(client, family).status_code == 409
    assert db.scalar(select(AuditLog)) is None


def test_invalid_destination_and_stale(client: TestClient, family: Family, db: Session) -> None:
    login(client, family.master)
    path = f"/master/students/{family.student_a.id}/transfer"
    original = str(family.a.id)
    assert (
        client.post(path, headers=ORIGIN, json=payload(original, str(uuid4()))).status_code == 404
    )
    assert client.post(path, headers=ORIGIN, json=payload(original, original)).status_code == 409
    family.b.user.is_active = False
    db.commit()
    assert (
        client.post(path, headers=ORIGIN, json=payload(original, str(family.b.id))).status_code
        == 409
    )
    family.b.user.is_active = True
    db.commit()
    assert (
        client.post(path, headers=ORIGIN, json=payload(str(uuid4()), str(family.b.id))).status_code
        == 409
    )
    assert (
        client.post(path, headers=ORIGIN, json=payload(original, str(family.b.id))).status_code
        == 200
    )
    assert (
        client.post(path, headers=ORIGIN, json=payload(original, str(family.a.id))).status_code
        == 409
    )
    assert db.scalar(select(AuditLog).order_by(AuditLog.created_at.desc())) is not None


def test_contract_auth_origin(client: TestClient, family: Family) -> None:
    path = f"/master/students/{family.student_a.id}/transfer"
    body = payload(str(family.a.id), str(family.b.id))
    assert client.post(path, headers=ORIGIN, json=body).status_code == 401
    login(client, family.a.user)
    assert client.post(path, headers=ORIGIN, json=body).status_code == 403
    assert client.get("/master/audit-logs").status_code == 403
    login(client, family.student_a.user)
    assert client.post(path, headers=ORIGIN, json=body).status_code == 403
    login(client, family.master)
    assert client.post(path, json=body).status_code == 403
    assert (
        client.post(
            path,
            headers=ORIGIN,
            json={"new_professional_id": str(family.b.id), "reason": "Valid reason"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            path, headers=ORIGIN, json=payload(str(family.a.id), str(family.b.id), " x ")
        ).status_code
        == 422
    )


def test_in_review_blocks(client: TestClient, family: Family, db: Session) -> None:
    request = ReevaluationRequest(
        student_id=family.student_a.id,
        professional_id=family.a.id,
        category="WORKOUT",
        reason="Motivo de teste seguro.",
        status=ReevaluationStatus.IN_REVIEW,
    )
    db.add(request)
    db.commit()
    assert move(client, family).status_code == 409
    assert family.student_a.professional_id == family.a.id


def test_atomic_rollback(family: Family, db: Session) -> None:
    def reject(*_args: object) -> None:
        raise IntegrityError("insert", {}, Exception("forced"))

    event.listen(AuditLog, "before_insert", reject)
    try:
        with pytest.raises(HTTPException) as failure:
            transfer(
                db,
                family.master,
                family.student_a.id,
                StudentTransfer(
                    expected_professional_id=family.a.id,
                    new_professional_id=family.b.id,
                    reason="Reorganização administrativa",
                ),
            )
        assert failure.value.status_code == 409
    finally:
        event.remove(AuditLog, "before_insert", reject)
        db.rollback()
    db.refresh(family.student_a)
    assert family.student_a.professional_id == family.a.id
    assert db.scalar(select(AuditLog)) is None


def test_access_changes_without_new_login(client: TestClient, family: Family) -> None:
    path = f"/professional/students/{family.student_a.id}"
    login(client, family.a.user)
    a_cookie = client.cookies.get("nutramove_session")
    assert client.get(path).status_code == 200
    login(client, family.b.user)
    b_cookie = client.cookies.get("nutramove_session")
    assert client.get(path).status_code == 404
    assert move(client, family).status_code == 200
    assert a_cookie and b_cookie
    client.cookies.set("nutramove_session", a_cookie)
    assert client.get(path).status_code == 404
    client.cookies.set("nutramove_session", b_cookie)
    assert client.get(path).status_code == 200


def test_history_access(
    client: TestClient,
    family: Family,
    db: Session,
    assessment_content: dict[str, object],
    diet_content: dict[str, object],
    workout_content: dict[str, object],
) -> None:
    student_id = family.student_a.id
    login(client, family.a.user)
    assessment = client.post(
        f"/professional/students/{student_id}/assessments", headers=ORIGIN, json=assessment_content
    )
    assert assessment.status_code == 201, assessment.text
    diet = client.post(
        f"/professional/students/{student_id}/diets", headers=ORIGIN, json=diet_content
    )
    assert diet.status_code == 201, diet.text
    workout = client.post(
        f"/professional/students/{student_id}/workouts", headers=ORIGIN, json=workout_content
    )
    assert workout.status_code == 201, workout.text
    assert move(client, family).status_code == 200
    login(client, family.b.user)
    assert client.get(f"/professional/students/{student_id}/evolution").status_code == 200
    assert client.get(f"/professional/assessments/{assessment.json()['id']}").status_code == 200
    assert (
        client.patch(
            f"/professional/assessments/{assessment.json()['id']}",
            headers=ORIGIN,
            json={
                **{
                    key: value
                    for key, value in assessment_content.items()
                    if key != "assessment_date"
                },
                "expected_revision": 1,
            },
        ).status_code
        == 404
    )
    assert client.get(f"/professional/students/{student_id}/diets").status_code == 200
    assert client.get(f"/professional/students/{student_id}/workouts").status_code == 200
    assert client.get(f"/professional/diets/{diet.json()['diet_id']}").status_code == 200
    assert client.get(f"/professional/workouts/{workout.json()['workout_id']}").status_code == 200
    assert (
        client.post(
            f"/professional/diets/{diet.json()['diet_id']}/versions",
            headers=ORIGIN,
            json=diet_content,
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/professional/workouts/{workout.json()['workout_id']}/versions",
            headers=ORIGIN,
            json=workout_content,
        ).status_code
        == 404
    )
    fresh_assessment = client.post(
        f"/professional/students/{student_id}/assessments",
        headers=ORIGIN,
        json=assessment_content,
    )
    assert fresh_assessment.status_code == 201
    current_assessment = db.get(Assessment, fresh_assessment.json()["id"])
    assert current_assessment and current_assessment.professional_id == family.b.id
    login(client, family.a.user)
    assert client.get(f"/professional/students/{student_id}/evolution").status_code == 404
    assert client.get(f"/professional/students/{student_id}/diets").status_code == 404
    assert client.get(f"/professional/students/{student_id}/workouts").status_code == 404
    historical_assessment = db.scalar(
        select(Assessment).where(Assessment.id == assessment.json()["id"])
    )
    assert historical_assessment is not None
    assert historical_assessment.professional_id == family.a.id


def test_information_and_notification_history(
    client: TestClient, family: Family, db: Session
) -> None:
    login(client, family.a.user)
    general = client.post(
        "/professional/informations",
        headers=ORIGIN,
        json={
            "title": "Aviso geral",
            "content": "Conteúdo geral de teste seguro.",
            "category": "NOTICE",
        },
    )
    assert general.status_code == 201
    individual = client.post(
        "/professional/informations",
        headers=ORIGIN,
        json={
            "title": "Aviso individual",
            "content": "Conteúdo individual de teste seguro.",
            "category": "NOTICE",
            "student_id": str(family.student_a.id),
        },
    )
    assert individual.status_code == 201
    for item in (general, individual):
        assert (
            client.post(
                f"/professional/informations/{item.json()['id']}/publish",
                headers=ORIGIN,
                json={"expected_revision": 1},
            ).status_code
            == 200
        )
    login(client, family.student_a.user)
    assert client.get("/student/informations").json()["total"] == 2
    notifications_before = client.get("/notifications").json()["total"]
    assert move(client, family).status_code == 200
    login(client, family.student_a.user)
    assert client.get("/student/informations").json()["total"] == 0
    assert client.get("/notifications").json()["total"] == notifications_before
    assert client.get(f"/student/informations/{general.json()['id']}").status_code == 404
    login(client, family.master)
    assert client.get(f"/master/informations/{general.json()['id']}").status_code == 200
    assert client.get(f"/master/informations/{individual.json()['id']}").status_code == 200


def test_current_plans_and_new_authorship(
    client: TestClient,
    family: Family,
    db: Session,
    diet_content: dict[str, object],
    workout_content: dict[str, object],
) -> None:
    from app.models.diet import Diet, DietVersion
    from app.models.workout import Workout, WorkoutVersion

    student_id = family.student_a.id
    login(client, family.a.user)
    diet = client.post(
        f"/professional/students/{student_id}/diets", headers=ORIGIN, json=diet_content
    )
    workout = client.post(
        f"/professional/students/{student_id}/workouts", headers=ORIGIN, json=workout_content
    )
    assert diet.status_code == workout.status_code == 201
    diet_version = diet.json()
    workout_version = workout.json()
    assert (
        client.post(
            f"/professional/diet-versions/{diet_version['id']}/approve",
            headers=ORIGIN,
            json={"expected_revision": 1},
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/professional/workout-versions/{workout_version['id']}/approve",
            headers=ORIGIN,
            json={"expected_revision": 1},
        ).status_code
        == 200
    )
    login(client, family.student_a.user)
    assert client.get("/student/diet").json()["diet"] is not None
    assert client.get("/student/workout").json()["workout"] is not None
    assert move(client, family).status_code == 200
    login(client, family.student_a.user)
    assert client.get("/student/diet").json()["diet"]["version_number"] == 1
    assert client.get("/student/workout").json()["workout"]["version_number"] == 1
    login(client, family.b.user)
    assert (
        client.post(
            f"/professional/diet-versions/{diet_version['id']}/duplicate", headers=ORIGIN
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/professional/workout-versions/{workout_version['id']}/duplicate", headers=ORIGIN
        ).status_code
        == 404
    )
    new_diet = client.post(
        f"/professional/students/{student_id}/diets", headers=ORIGIN, json=diet_content
    )
    new_workout = client.post(
        f"/professional/students/{student_id}/workouts", headers=ORIGIN, json=workout_content
    )
    assert new_diet.status_code == new_workout.status_code == 201
    old_diet = db.get(Diet, diet_version["diet_id"])
    old_workout = db.get(Workout, workout_version["workout_id"])
    next_diet = db.get(Diet, new_diet.json()["diet_id"])
    next_workout = db.get(Workout, new_workout.json()["workout_id"])
    approved_diet = db.get(DietVersion, diet_version["id"])
    approved_workout = db.get(WorkoutVersion, workout_version["id"])
    assert old_diet and old_diet.professional_id == family.a.id
    assert old_workout and old_workout.professional_id == family.a.id
    assert next_diet and next_diet.professional_id == family.b.id
    assert next_workout and next_workout.professional_id == family.b.id
    assert approved_diet and approved_diet.status.value == "APPROVED"
    assert approved_workout and approved_workout.status.value == "APPROVED"


def test_pending_reevaluation_and_hydration(
    client: TestClient, family: Family, db: Session
) -> None:
    from app.models.hydration import WaterRecord

    record = WaterRecord(
        student_id=family.student_a.id, amount_ml=500, consumed_at=datetime.now(UTC)
    )
    request = ReevaluationRequest(
        student_id=family.student_a.id,
        professional_id=family.a.id,
        category="WORKOUT",
        reason="Motivo de teste seguro.",
        status=ReevaluationStatus.PENDING,
    )
    db.add_all([record, request])
    db.commit()
    assert move(client, family).status_code == 200
    login(client, family.a.user)
    assert client.get(f"/professional/students/{family.student_a.id}/hydration").status_code == 404
    assert client.get(f"/professional/reevaluation-requests/{request.id}").status_code == 404
    login(client, family.b.user)
    assert client.get(f"/professional/students/{family.student_a.id}/hydration").status_code == 200
    assert client.get(f"/professional/reevaluation-requests/{request.id}").status_code == 200
    assert (
        client.post(
            f"/professional/reevaluation-requests/{request.id}/start-review", headers=ORIGIN
        ).status_code
        == 200
    )
    db.refresh(request)
    assert request.professional_id == family.a.id


def test_dashboard_counts(client: TestClient, family: Family, db: Session) -> None:
    login(client, family.a.user)
    before_a = client.get("/professional/dashboard").json()["students"]["total"]
    login(client, family.b.user)
    before_b = client.get("/professional/dashboard").json()["students"]["total"]
    assert move(client, family).status_code == 200
    login(client, family.a.user)
    assert client.get("/professional/dashboard").json()["students"]["total"] == before_a - 1
    login(client, family.b.user)
    assert client.get("/professional/dashboard").json()["students"]["total"] == before_b + 1
    family.student_b.professional_id = None
    db.commit()
    login(client, family.master)
    before_unassigned = client.get("/master/dashboard").json()["students_unassigned"]
    response = client.post(
        f"/master/students/{family.student_b.id}/transfer",
        headers=ORIGIN,
        json=payload(None, str(family.a.id)),
    )
    assert response.status_code == 200
    assert client.get("/master/dashboard").json()["students_unassigned"] == before_unassigned - 1


def test_audit_is_private_and_read_only(client: TestClient, family: Family) -> None:
    audit_id = move(client, family).json()["audit_log_id"]
    for actor in (family.a.user, family.student_a.user):
        login(client, actor)
        assert client.get("/master/audit-logs").status_code == 403
        assert client.get(f"/master/audit-logs/{audit_id}").status_code == 403
    client.cookies.clear()
    assert client.get("/master/audit-logs").status_code == 401
    login(client, family.master)
    assert (
        client.patch(f"/master/audit-logs/{audit_id}", headers=ORIGIN, json={}).status_code == 405
    )
    assert client.delete(f"/master/audit-logs/{audit_id}", headers=ORIGIN).status_code == 405


def test_simultaneous_transfers(auth_engine: Engine) -> None:
    suffix = uuid4().hex
    with Session(auth_engine) as seed:
        master = User(
            name="Concurrent master",
            email=f"master-{suffix}@example.com",
            role=UserRole.MASTER,
            password_hash="unused",
        )
        professionals = [
            Professional(
                user=User(
                    name=f"Concurrent {index}",
                    email=f"p-{index}-{suffix}@example.com",
                    role=UserRole.PROFESSIONAL,
                    password_hash="unused",
                )
            )
            for index in range(3)
        ]
        seed.add_all([master, *professionals])
        seed.flush()
        student = make_student(professionals[0], f"student-{suffix}@example.com", "unused")
        seed.add(student)
        seed.commit()
        master_id = master.id
        student_id = student.id
        old_id = professionals[0].id
        destination_ids = [professionals[1].id, professionals[2].id]
    barrier = Barrier(2)

    def submit(destination_id: UUID) -> int:
        with Session(auth_engine) as session:
            actor = session.get(User, master_id)
            assert actor is not None
            barrier.wait(timeout=10)
            try:
                transfer(
                    session,
                    actor,
                    student_id,
                    StudentTransfer(
                        expected_professional_id=old_id,
                        new_professional_id=destination_id,
                        reason="Reorganização administrativa",
                    ),
                )
                return 200
            except HTTPException as error:
                session.rollback()
                return error.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(submit, destination_ids[0])
        second = executor.submit(submit, destination_ids[1])
        assert sorted([first.result(timeout=20), second.result(timeout=20)]) == [200, 409]
    with Session(auth_engine) as check:
        moved = check.get(Student, student_id)
        assert moved is not None
        assert moved.professional_id in destination_ids
        assert (
            check.scalar(
                select(func.count()).select_from(AuditLog).where(AuditLog.resource_id == student_id)
            )
            == 1
        )
