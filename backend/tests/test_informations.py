from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import StudentStatus
from app.models.notification import Notification
from tests.test_assessments import ORIGIN, Family, login, make_student
from tests.test_assessments import family as family_fixture

family = family_fixture
BASE = "/professional/informations"
CONTENT = {
    "title": "Aviso para a carteira",
    "content": "Conteudo reservado para o acompanhamento.",
    "category": "NOTICE",
}


@pytest.fixture
def draft(client: TestClient, family: Family) -> dict[str, object]:
    login(client, family.a.user)
    result = client.post(BASE, headers=ORIGIN, json=CONTENT)
    assert result.status_code == 201
    data: dict[str, object] = result.json()
    return data


def test_publication(
    client: TestClient, family: Family, draft: dict[str, object], db: Session
) -> None:
    assert draft["status"] == "DRAFT" and draft["student_id"] is None
    assert list(db.scalars(select(Notification))) == []
    login(client, family.student_a.user)
    assert client.get("/student/informations").json()["total"] == 0
    assert client.get(f"/student/informations/{draft['id']}").status_code == 404
    login(client, family.a.user)
    published = client.post(
        f"{BASE}/{draft['id']}/publish", headers=ORIGIN, json={"expected_revision": 1}
    )
    assert published.status_code == 200, published.text
    assert published.json()["published_at"] and published.json()["status"] == "PUBLISHED"
    assert (
        client.post(
            f"{BASE}/{draft['id']}/publish", headers=ORIGIN, json={"expected_revision": 2}
        ).status_code
        == 409
    )
    notifications = list(db.scalars(select(Notification)))
    assert len(notifications) == 1 and notifications[0].user_id == family.student_a.user_id
    assert CONTENT["content"] not in notifications[0].message
    login(client, family.student_a.user)
    result = client.get(f"/student/informations/{draft['id']}")
    assert result.status_code == 200 and result.headers["cache-control"] == "no-store"
    assert not {
        "professional_id",
        "student_id",
        "created_by_user_id",
        "edit_revision",
    }.intersection(result.json())
    login(client, family.a.user)
    assert (
        client.patch(
            f"{BASE}/{draft['id']}", headers=ORIGIN, json=CONTENT | {"expected_revision": 2}
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"{BASE}/{draft['id']}/archive", headers=ORIGIN, json={"expected_revision": 2}
        ).status_code
        == 200
    )
    login(client, family.student_a.user)
    assert client.get(f"/student/informations/{draft['id']}").status_code == 404


def test_unicode_content_round_trip(client: TestClient, family: Family) -> None:
    content = "Nutrição, evolução, hidratação e reavaliação estão disponíveis."
    login(client, family.a.user)
    created = client.post(BASE, headers=ORIGIN, json=CONTENT | {"content": content})
    assert created.status_code == 201
    result = client.get(f"{BASE}/{created.json()['id']}")
    assert result.status_code == 200
    assert result.json()["content"] == content


@pytest.mark.parametrize(
    "method,suffix", [("GET", ""), ("PATCH", ""), ("POST", "/publish"), ("POST", "/archive")]
)
def test_bola(
    client: TestClient, family: Family, draft: dict[str, object], method: str, suffix: str
) -> None:
    login(client, family.b.user)
    payload = (CONTENT if method == "PATCH" else {}) | {"expected_revision": 1}
    for identifier in [draft["id"], str(uuid4())]:
        assert (
            client.request(
                method,
                f"{BASE}/{identifier}{suffix}",
                headers=ORIGIN,
                json=payload if method != "GET" else None,
            ).status_code
            == 404
        )
    assert client.get(BASE).json()["total"] == 0
    assert (
        client.post(
            BASE, headers=ORIGIN, json=CONTENT | {"student_id": str(family.student_a.id)}
        ).status_code
        == 404
    )
    assert client.get(BASE, params={"student_id": str(family.student_a.id)}).status_code == 404


def test_individual(client: TestClient, family: Family, db: Session) -> None:
    sibling = make_student(family.a, "sibling@example.com", family.master.password_hash)
    db.add(sibling)
    db.commit()
    login(client, family.a.user)
    created = client.post(
        BASE, headers=ORIGIN, json=CONTENT | {"student_id": str(family.student_a.id)}
    ).json()
    assert (
        client.post(
            f"{BASE}/{created['id']}/publish", headers=ORIGIN, json={"expected_revision": 1}
        ).status_code
        == 200
    )
    for actor in [sibling.user, family.student_b.user]:
        login(client, actor)
        assert client.get("/student/informations").json()["total"] == 0
        assert client.get(f"/student/informations/{created['id']}").status_code == 404
    assert len(list(db.scalars(select(Notification)))) == 1
    login(client, family.student_a.user)
    assert client.get("/student/informations").json()["total"] == 1


@pytest.mark.parametrize("status", list(StudentStatus))
def test_broadcast_eligibility(
    client: TestClient, family: Family, draft: dict[str, object], db: Session, status: StudentStatus
) -> None:
    family.student_a.status = status
    family.student_a.user.is_active = status != StudentStatus.INACTIVE
    db.commit()
    assert (
        client.post(
            f"{BASE}/{draft['id']}/publish", headers=ORIGIN, json={"expected_revision": 1}
        ).status_code
        == 200
    )
    assert len(list(db.scalars(select(Notification)))) == (
        1 if status == StudentStatus.ACTIVE else 0
    )


@pytest.mark.parametrize(
    "change",
    [
        {"title": "  "},
        {"content": "  "},
        {"category": "FREE"},
        {"professional_id": str(uuid4())},
        {"status": "PUBLISHED"},
        {"created_by_user_id": str(uuid4())},
    ],
)
def test_invalid(client: TestClient, family: Family, change: dict[str, object]) -> None:
    login(client, family.a.user)
    assert client.post(BASE, headers=ORIGIN, json=CONTENT | change).status_code == 422


def test_edit_filters_master_origin(
    client: TestClient, family: Family, draft: dict[str, object]
) -> None:
    path = f"{BASE}/{draft['id']}"
    assert (
        client.patch(
            path,
            headers=ORIGIN,
            json=CONTENT | {"title": "Titulo corrigido", "expected_revision": 1},
        ).status_code
        == 200
    )
    assert (
        client.post(path + "/publish", headers=ORIGIN, json={"expected_revision": 1}).status_code
        == 409
    )
    assert client.get(BASE + "?status=DRAFT&category=NOTICE&general_only=true").json()["total"] == 1
    assert client.get(BASE + "?status=PUBLISHED").json()["total"] == 0
    for headers in [{}, {"Origin": "https://bad.example"}]:
        assert (
            client.post(
                path + "/publish", headers=headers, json={"expected_revision": 2}
            ).status_code
            == 403
        )
    login(client, family.master)
    assert client.get("/master/informations").json()["total"] == 1
    assert client.get(f"/master/informations/{draft['id']}").status_code == 200
    assert client.post(BASE, headers=ORIGIN, json=CONTENT).status_code == 403
    assert client.post(
        f"/master/informations/{draft['id']}/publish", headers=ORIGIN, json={"expected_revision": 2}
    ).status_code in (404, 405)
    login(client, family.student_a.user)
    assert client.post(BASE, headers=ORIGIN, json=CONTENT).status_code == 403
    client.cookies.clear()
    assert client.get(BASE).status_code == 401
    assert client.get("/student/informations").status_code == 401
