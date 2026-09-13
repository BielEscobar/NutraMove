from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.information import Information, InformationStatus
from app.models.notification import Notification
from app.models.notification import NotificationType as Kind
from app.services.notifications import add
from tests.test_assessments import ORIGIN, Family, login
from tests.test_assessments import family as family_fixture
from tests.test_diets import content as diet_fixture
from tests.test_students import payload as registration_fixture
from tests.test_workouts import content as workout_fixture

family = family_fixture
diet_content = diet_fixture
workout_content = workout_fixture
registration = registration_fixture


def test_private_inbox(client: TestClient, family: Family, db: Session) -> None:
    for _ in range(3):
        add(db, family.student_a.user_id, Kind.WORKOUT_UPDATED, uuid4())
    add(db, family.student_b.user_id, Kind.WORKOUT_UPDATED, uuid4())
    db.commit()
    login(client, family.student_a.user)
    records = client.get("/notifications?page_size=2").json()
    assert records["total"] == 3 and len(records["items"]) == 2
    assert "user_id" not in str(records)
    identifier = records["items"][0]["id"]
    assert client.get("/notifications/unread-count").json() == {"count": 3}
    first = client.post(f"/notifications/{identifier}/read", headers=ORIGIN)
    assert first.status_code == 200 and first.json()["read_at"]
    assert (
        client.post(f"/notifications/{identifier}/read", headers=ORIGIN).json()["read_at"]
        == first.json()["read_at"]
    )
    assert client.get("/notifications?unread_only=true").json()["total"] == 2
    assert client.post("/notifications/read-all", headers=ORIGIN).status_code == 204
    assert client.get("/notifications/unread-count").json() == {"count": 0}
    for actor in [family.student_b.user, family.a.user, family.master]:
        login(client, actor)
        assert client.get(f"/notifications/{identifier}").status_code == 404
        assert client.post(f"/notifications/{identifier}/read", headers=ORIGIN).status_code == 404
    login(client, family.student_b.user)
    assert client.get("/notifications/unread-count").json() == {"count": 1}
    assert client.get("/notifications?user_id=" + str(family.student_a.user_id)).status_code == 422


@pytest.mark.parametrize(
    "path", ["/notifications", "/notifications/unread-count", "/notifications/" + str(uuid4())]
)
def test_anonymous(client: TestClient, path: str) -> None:
    assert client.get(path).status_code == 401


def test_read_origin(client: TestClient, family: Family, db: Session) -> None:
    add(db, family.master.id, Kind.WORKOUT_UPDATED, uuid4())
    db.commit()
    login(client, family.master)
    identifier = client.get("/notifications").json()["items"][0]["id"]
    for headers in [{}, {"Origin": "https://bad.example"}]:
        assert client.post("/notifications/read-all", headers=headers).status_code == 403
        assert client.post(f"/notifications/{identifier}/read", headers=headers).status_code == 403
    assert client.get("/notifications/unread-count").json()["count"] == 1


@pytest.mark.parametrize("module", ["diets", "workouts"])
def test_plan_events(
    client: TestClient,
    family: Family,
    db: Session,
    module: str,
    diet_content: dict[str, object],
    workout_content: dict[str, object],
) -> None:
    login(client, family.a.user)
    content = diet_content if module == "diets" else workout_content
    result = client.post(
        f"/professional/students/{family.student_a.id}/{module}", headers=ORIGIN, json=content
    )
    assert result.status_code == 201
    identifier = result.json()["id"]
    assert list(db.scalars(select(Notification))) == []
    path = (
        f"/professional/{'diet' if module == 'diets' else 'workout'}-versions/{identifier}/approve"
    )
    response = client.post(path, headers=ORIGIN, json={"expected_revision": 1})
    assert response.status_code == 200, response.text
    assert client.post(path, headers=ORIGIN, json={"expected_revision": 1}).status_code == 409
    records = list(db.scalars(select(Notification)))
    assert len(records) == 1 and records[0].user_id == family.student_a.user_id
    assert records[0].resource_id == UUID(identifier)
    assert records[0].type == (Kind.DIET_UPDATED if module == "diets" else Kind.WORKOUT_UPDATED)
    assert str(content["notes"]) not in records[0].message


@pytest.mark.parametrize("finish", ["complete", "cancel"])
def test_reevaluation_events(client: TestClient, family: Family, db: Session, finish: str) -> None:
    login(client, family.student_a.user)
    response = client.post(
        "/student/reevaluation-requests",
        headers=ORIGIN,
        json={"category": "WORKOUT", "reason": "Motivo privado da solicitacao."},
    )
    identifier = response.json()["id"]
    created_notification = db.scalar(select(Notification))
    assert created_notification is not None
    assert created_notification.type == Kind.REEVALUATION_CREATED
    login(client, family.a.user)
    path = f"/professional/reevaluation-requests/{identifier}"
    assert client.post(path + "/start-review", headers=ORIGIN).status_code == 200
    assert (
        client.post(
            path + "/" + finish,
            headers=ORIGIN,
            json={"professional_response": "Resposta privada do profissional."},
        ).status_code
        == 200
    )
    records = list(db.scalars(select(Notification)))
    assert len(records) == 3
    assert {r.type for r in records} == {
        Kind.REEVALUATION_CREATED,
        Kind.REEVALUATION_IN_REVIEW,
        Kind.REEVALUATION_COMPLETED if finish == "complete" else Kind.REEVALUATION_CANCELLED,
    }
    assert all("privad" not in r.message for r in records)


@pytest.mark.parametrize("linked", [True, False])
def test_registration_event(
    client: TestClient, family: Family, db: Session, registration: dict[str, object], linked: bool
) -> None:
    if linked:
        registration["professional_id"] = str(family.a.id)
    assert client.post("/students/register", headers=ORIGIN, json=registration).status_code == 201
    records = list(db.scalars(select(Notification)))
    assert len(records) == int(linked)
    if linked:
        assert (
            records[0].user_id == family.a.user_id
            and records[0].type == Kind.STUDENT_PENDING_APPROVAL
        )


def test_information_rollback(client: TestClient, family: Family, db: Session) -> None:
    login(client, family.a.user)
    created = client.post(
        "/professional/informations",
        headers=ORIGIN,
        json={
            "title": "Teste transacional",
            "content": "Conteudo para publicar atomicamente.",
            "category": "INFO",
        },
    ).json()
    connection = db.connection()

    def fail(
        conn: object,
        cursor: object,
        statement: str,
        parameters: object,
        context: object,
        many: bool,
    ) -> None:
        if statement.startswith("INSERT INTO notifications"):
            raise IntegrityError("test", {}, Exception("test-only"))

    event.listen(connection, "before_cursor_execute", fail)
    try:
        assert (
            client.post(
                f"/professional/informations/{created['id']}/publish",
                headers=ORIGIN,
                json={"expected_revision": 1},
            ).status_code
            == 409
        )
    finally:
        event.remove(connection, "before_cursor_execute", fail)
    record = db.get(Information, UUID(created["id"]))
    assert record and record.status == InformationStatus.DRAFT and record.published_at is None
    assert list(db.scalars(select(Notification))) == []
