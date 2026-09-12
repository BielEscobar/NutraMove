from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Professional, StudentStatus, User, UserRole
from app.models.reevaluation import ReevaluationCategory, ReevaluationRequest, ReevaluationStatus
from app.schemas.reevaluation import ReevaluationCreate
from app.services import reevaluations
from tests.test_assessments import ORIGIN, Family, login, make_student
from tests.test_assessments import family as assessment_family

PAYLOAD = {"category": "WORKOUT", "reason": "Gostaria de revisar meu acompanhamento."}
BASE = "/student/reevaluation-requests"
PRO = "/professional/reevaluation-requests"


@pytest.fixture
def request_id(client: TestClient, family: Family) -> str:
    login(client, family.student_a.user)
    result = client.post(BASE, headers=ORIGIN, json=PAYLOAD)
    assert result.status_code == 201, result.text
    return str(result.json()["id"])


def test_creation(client: TestClient, family: Family, db: Session, request_id: str) -> None:
    result = client.get(f"{BASE}/{request_id}")
    data = result.json()
    record = db.get(ReevaluationRequest, UUID(request_id))
    assert record and record.professional_id == family.a.id
    assert data["status"] == "PENDING" and data["reason"] == PAYLOAD["reason"]
    assert data["professional_response"] is None and data["reviewed_at"] is None
    assert result.headers["cache-control"] == "no-store"
    assert not {
        "student_id",
        "professional_id",
        "user_id",
        "reviewed_by_user_id",
        "completed_by_user_id",
        "cancelled_by_user_id",
    }.intersection(data)
    assert client.get(BASE).json()["total"] == 1
    duplicate = client.post(BASE, headers=ORIGIN, json=PAYLOAD | {"category": "DIET"})
    assert duplicate.status_code == 409
    assert "em andamento" in duplicate.json()["error"]["message"]


@pytest.mark.parametrize(
    "change",
    [
        {"reason": "   "},
        {"reason": "short"},
        {"reason": "x" * 2001},
        {"category": "FREE"},
        {"student_id": str(uuid4())},
        {"professional_id": str(uuid4())},
        {"user_id": str(uuid4())},
        {"role": "MASTER"},
        {"status": "COMPLETED"},
        {"professional_response": "Injected response"},
    ],
)
def test_create_validation(client: TestClient, family: Family, change: dict[str, object]) -> None:
    login(client, family.student_a.user)
    assert client.post(BASE, headers=ORIGIN, json=PAYLOAD | change).status_code == 422


@pytest.mark.parametrize(
    "condition", ["pending", "rejected", "unassigned", "professional_inactive"]
)
def test_creation_requirements(
    client: TestClient, family: Family, db: Session, condition: str
) -> None:
    if condition == "pending":
        family.student_a.status = StudentStatus.PENDING_APPROVAL
    elif condition == "rejected":
        family.student_a.status = StudentStatus.REJECTED
    elif condition == "unassigned":
        family.student_a.professional_id = None
        db.expire(family.student_a, ["professional"])
    else:
        family.a.user.is_active = False
    db.commit()
    login(client, family.student_a.user)
    assert client.post(BASE, headers=ORIGIN, json=PAYLOAD).status_code == 409
    assert client.get(BASE).status_code == 200


def test_workflow(client: TestClient, family: Family, db: Session, request_id: str) -> None:
    login(client, family.a.user)
    path = f"{PRO}/{request_id}"
    assert client.get("/professional/dashboard").json()["reevaluations_pending"] == 1
    assert (
        client.post(
            path + "/complete", headers=ORIGIN, json={"professional_response": "Resposta final."}
        ).status_code
        == 409
    )
    review = client.post(path + "/start-review", headers=ORIGIN)
    assert review.status_code == 200 and review.json()["status"] == "IN_REVIEW"
    assert review.json()["reviewed_at"] is not None
    dashboard = client.get("/professional/dashboard").json()
    assert dashboard["reevaluations_pending"] == 0 and dashboard["reevaluations_in_review"] == 1
    assert client.post(path + "/start-review", headers=ORIGIN).status_code == 409
    assert (
        client.post(
            path + "/complete", headers=ORIGIN, json={"professional_response": "   "}
        ).status_code
        == 422
    )
    done = client.post(
        path + "/complete",
        headers=ORIGIN,
        json={"professional_response": "  Revisei seu acompanhamento.  "},
    )
    assert done.status_code == 200 and done.json()["status"] == "COMPLETED"
    assert done.json()["completed_at"] is not None
    assert done.json()["professional_response"] == "Revisei seu acompanhamento."
    record = db.get(ReevaluationRequest, UUID(request_id))
    assert record and record.reviewed_by_user_id == record.completed_by_user_id == family.a.user_id
    assert client.get("/professional/dashboard").json()["reevaluations_in_review"] == 0
    for action in ["start-review", "cancel", "complete"]:
        assert (
            client.post(
                path + "/" + action,
                headers=ORIGIN,
                json={"professional_response": "Cannot overwrite."},
            ).status_code
            == 409
        )
    login(client, family.student_a.user)
    assert (
        client.get(f"{BASE}/{request_id}").json()["professional_response"]
        == "Revisei seu acompanhamento."
    )
    assert client.post(BASE, headers=ORIGIN, json=PAYLOAD).status_code == 201


@pytest.mark.parametrize(
    "method,suffix",
    [("GET", ""), ("POST", "/start-review"), ("POST", "/complete"), ("POST", "/cancel")],
)
def test_professional_bola(
    client: TestClient, family: Family, request_id: str, method: str, suffix: str
) -> None:
    login(client, family.b.user)
    for identifier in [request_id, str(uuid4())]:
        response = client.request(
            method,
            f"{PRO}/{identifier}{suffix}",
            headers=ORIGIN,
            json={"professional_response": "Response from wrong portfolio."}
            if suffix == "/complete"
            else None,
        )
        assert response.status_code == 404
    assert client.get(PRO).json()["total"] == 0
    assert client.get(PRO, params={"student_id": str(family.student_a.id)}).status_code == 404
    metrics = client.get("/professional/dashboard").json()
    assert metrics["reevaluations_pending"] == metrics["reevaluations_in_review"] == 0


def test_student_bola_and_permissions(client: TestClient, family: Family, request_id: str) -> None:
    login(client, family.student_b.user)
    assert client.get(BASE).json()["total"] == 0
    assert client.get(f"{BASE}/{request_id}").status_code == 404
    assert client.post(f"{BASE}/{request_id}/cancel", headers=ORIGIN).status_code == 404
    login(client, family.student_a.user)
    assert (
        client.post(
            f"{PRO}/{request_id}/complete",
            headers=ORIGIN,
            json={"professional_response": "Unauthorized."},
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"{BASE}/{request_id}", headers=ORIGIN, json={"reason": "Unauthorized modification."}
        ).status_code
        == 405
    )
    assert client.get(BASE, params={"student_id": str(family.student_b.id)}).status_code == 422


def test_cancellation(client: TestClient, family: Family, db: Session, request_id: str) -> None:
    cancelled = client.post(f"{BASE}/{request_id}/cancel", headers=ORIGIN)
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "CANCELLED"
    record = db.get(ReevaluationRequest, UUID(request_id))
    assert record and record.cancelled_by_user_id == family.student_a.user_id
    assert record.cancelled_at is not None
    assert client.post(f"{BASE}/{request_id}/cancel", headers=ORIGIN).status_code == 409
    new = client.post(BASE, headers=ORIGIN, json=PAYLOAD).json()["id"]
    login(client, family.a.user)
    assert client.post(f"{PRO}/{new}/start-review", headers=ORIGIN).status_code == 200
    login(client, family.student_a.user)
    assert client.post(f"{BASE}/{new}/cancel", headers=ORIGIN).status_code == 409
    assert client.post(BASE, headers=ORIGIN, json=PAYLOAD).status_code == 409
    login(client, family.a.user)
    assert client.post(f"{PRO}/{new}/cancel", headers=ORIGIN).status_code == 200
    assert client.post(f"{PRO}/{new}/start-review", headers=ORIGIN).status_code == 409


def test_filters_and_master(client: TestClient, family: Family, request_id: str) -> None:
    client.post(f"{BASE}/{request_id}/cancel", headers=ORIGIN)
    client.post(BASE, headers=ORIGIN, json=PAYLOAD | {"category": "DIET"})
    login(client, family.student_b.user)
    client.post(BASE, headers=ORIGIN, json=PAYLOAD)
    login(client, family.a.user)
    assert client.get(PRO).json()["total"] == 2
    assert client.get(PRO + "?category=DIET").json()["total"] == 1
    assert client.get(PRO + "?status=CANCELLED").json()["total"] == 1
    assert len(client.get(PRO + "?page_size=1&page=2").json()["items"]) == 1
    assert client.get(PRO + "?page_size=101").status_code == 422
    login(client, family.master)
    master = "/master/reevaluation-requests"
    assert client.get(master).json()["total"] == 3
    assert (
        client.get(master + "/" + request_id).json()["student_name"] == family.student_a.user.name
    )
    assert client.post(f"{PRO}/{request_id}/cancel", headers=ORIGIN).status_code == 403
    for action in ["start-review", "complete", "cancel"]:
        assert client.post(f"{master}/{request_id}/{action}", headers=ORIGIN).status_code in (
            404,
            405,
        )


def test_origins_and_anonymous(client: TestClient, family: Family, request_id: str) -> None:
    for headers in [{}, {"Origin": "https://untrusted.example"}]:
        assert client.post(BASE, headers=headers, json=PAYLOAD).status_code == 403
        assert client.post(f"{BASE}/{request_id}/cancel", headers=headers).status_code == 403
    login(client, family.a.user)
    for action in ["start-review", "complete", "cancel"]:
        assert (
            client.post(
                f"{PRO}/{request_id}/{action}",
                headers={"Origin": "https://bad.example"},
                json={"professional_response": "Must not be stored."},
            ).status_code
            == 403
        )
    client.cookies.clear()
    for base in [BASE, PRO, "/master/reevaluation-requests"]:
        assert client.get(base).status_code == 401
    assert client.post(BASE, headers=ORIGIN, json=PAYLOAD).status_code == 401


def test_current_portfolio_authorization(
    client: TestClient, family: Family, db: Session, request_id: str
) -> None:
    # Simulates a future transfer at DB level, without adding a transfer feature.
    family.student_a.professional_id = family.b.id
    db.commit()
    login(client, family.a.user)
    assert client.get(f"{PRO}/{request_id}").status_code == 404
    login(client, family.b.user)
    assert client.get(f"{PRO}/{request_id}").status_code == 200
    record = db.get(ReevaluationRequest, UUID(request_id))
    assert record and record.professional_id == family.a.id


def test_database_unique(db: Session, family: Family, request_id: str) -> None:
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(
            ReevaluationRequest(
                student_id=family.student_a.id,
                professional_id=family.a.id,
                category=ReevaluationCategory.DIET,
                reason="Duplicate direct insert.",
                status=ReevaluationStatus.IN_REVIEW,
            )
        )
        db.flush()


def test_concurrent_creation(auth_engine: Engine) -> None:
    # Independent connections, committed fixtures, only in the disposable test schema.
    with Session(auth_engine) as seed:
        suffix = uuid4().hex
        professional = Professional(
            user=User(
                name="Concurrent professional",
                email=f"p-{suffix}@example.com",
                role=UserRole.PROFESSIONAL,
                password_hash="unused",
            )
        )
        seed.add(professional)
        seed.flush()
        student = make_student(professional, f"s-{suffix}@example.com", "unused")
        seed.add(student)
        seed.commit()
        actor_id, student_id = student.user_id, student.id
    barrier = Barrier(2)

    def submit() -> int:
        with Session(auth_engine) as session:
            actor = session.get(User, actor_id)
            assert actor
            barrier.wait(timeout=10)
            try:
                reevaluations.create(
                    session,
                    actor,
                    ReevaluationCreate(
                        category=ReevaluationCategory.WORKOUT, reason="Concurrent valid request."
                    ),
                )
                return 201
            except HTTPException as error:
                session.rollback()
                return error.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(submit)
        second = executor.submit(submit)
        assert sorted([first.result(timeout=20), second.result(timeout=20)]) == [201, 409]
    with Session(auth_engine) as check:
        assert (
            check.scalar(
                select(func.count())
                .select_from(ReevaluationRequest)
                .where(ReevaluationRequest.student_id == student_id)
            )
            == 1
        )


family = assessment_family
