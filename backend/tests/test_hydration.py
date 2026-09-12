from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.time import day_bounds
from app.models.hydration import WaterRecord
from app.repositories import hydration
from tests.test_assessments import ORIGIN, Family, login
from tests.test_assessments import family as assessment_family


def test_water_flow(client: TestClient, family: Family, db: Session) -> None:
    family.student_a.water_goal = 2.5
    db.commit()
    login(client, family.student_a.user)
    for amount in (250, 500):
        response = client.post("/student/water-records", headers=ORIGIN, json={"amount_ml": amount})
        assert response.status_code == 201
        assert set(response.json()) == {"id", "amount_ml", "consumed_at", "created_at"}
        assert response.headers["cache-control"] == "no-store"
    result = client.get("/student/hydration").json()
    assert result["consumed_ml"] == 750
    assert result["goal_ml"] == 2500
    assert result["percentage"] == 30
    assert result["remaining_ml"] == 1750
    assert len(result["records"]) == 2
    assert result["timezone"] == "America/Sao_Paulo"
    assert client.get("/student/hydration?page_size=1").json()["total_records"] == 2
    assert len(client.get("/student/hydration?page=2&page_size=1").json()["records"]) == 1
    brief = client.get("/student/hydration/summary").json()
    assert "records" not in brief and brief["consumed_ml"] == 750
    assert "remaining_ml" not in WaterRecord.__table__.columns
    client.post("/student/water-records", headers=ORIGIN, json={"amount_ml": 2500})
    over = client.get("/student/hydration/summary").json()
    assert over["remaining_ml"] == 0 and over["percentage"] == 130


@pytest.mark.parametrize("amount", [0, -1, 10001, True, False, 1.5, "250", None])
def test_invalid_amount(client: TestClient, family: Family, amount: object) -> None:
    login(client, family.student_a.user)
    assert (
        client.post(
            "/student/water-records", headers=ORIGIN, json={"amount_ml": amount}
        ).status_code
        == 422
    )


@pytest.mark.parametrize(
    "field", ["student_id", "professional_id", "user_id", "role", "water_goal"]
)
def test_water_injection(client: TestClient, family: Family, field: str) -> None:
    login(client, family.student_a.user)
    assert (
        client.post(
            "/student/water-records", headers=ORIGIN, json={"amount_ml": 250, field: str(uuid4())}
        ).status_code
        == 422
    )


@pytest.mark.parametrize("goal", [None, 0.0])
def test_no_goal(client: TestClient, family: Family, db: Session, goal: float | None) -> None:
    family.student_a.water_goal = goal
    db.commit()
    login(client, family.student_a.user)
    result = client.get("/student/hydration").json()
    assert result["goal_ml"] is result["remaining_ml"] is result["percentage"] is None
    assert result["consumed_ml"] == 0 and result["records"] == []


def test_timestamp(client: TestClient, family: Family) -> None:
    login(client, family.student_a.user)
    yesterday = datetime.now(UTC) - timedelta(days=1)
    result = client.post(
        "/student/water-records",
        headers=ORIGIN,
        json={"amount_ml": 300, "consumed_at": yesterday.isoformat()},
    )
    assert result.status_code == 201
    assert datetime.fromisoformat(result.json()["consumed_at"]) == yesterday
    for value in [(datetime.now(UTC) + timedelta(minutes=6)).isoformat(), "2026-01-01T10:00:00"]:
        assert (
            client.post(
                "/student/water-records",
                headers=ORIGIN,
                json={"amount_ml": 300, "consumed_at": value},
            ).status_code
            == 422
        )


@pytest.mark.parametrize("days", [1, 7, 30])
def test_timezone_history(
    client: TestClient, family: Family, db: Session, monkeypatch: pytest.MonkeyPatch, days: int
) -> None:
    from app.services import hydration as service

    today = date(2026, 9, 11)
    monkeypatch.setattr(hydration, "business_today", lambda _: today)
    monkeypatch.setattr(service, "business_today", lambda _: today)
    start, end = day_bounds(today, "America/Sao_Paulo")
    assert start == datetime(2026, 9, 11, 3, tzinfo=UTC)
    for instant, amount in [
        (start - timedelta(seconds=1), 100),
        (start, 250),
        (end - timedelta(seconds=1), 500),
        (end, 1000),
    ]:
        db.add(WaterRecord(student_id=family.student_a.id, consumed_at=instant, amount_ml=amount))
    db.add(WaterRecord(student_id=family.student_b.id, consumed_at=start, amount_ml=9000))
    db.commit()
    login(client, family.student_a.user)
    result = client.get("/student/hydration").json()
    assert result["date"] == str(today) and result["consumed_ml"] == 750
    history = client.get(f"/student/hydration/history?days={days}").json()
    assert len(history["items"]) == days
    assert history["items"][-1] == {"date": str(today), "consumed_ml": 750}
    if days > 1:
        assert history["items"][-2]["consumed_ml"] == 100
    assert client.get("/student/hydration/history?days=2").status_code == 422


def test_water_scope_and_goal(client: TestClient, family: Family, db: Session) -> None:
    login(client, family.student_a.user)
    client.post("/student/water-records", headers=ORIGIN, json={"amount_ml": 500})
    login(client, family.student_b.user)
    assert (
        client.get("/student/hydration", params={"student_id": str(family.student_a.id)}).json()[
            "consumed_ml"
        ]
        == 0
    )
    assert client.patch("/student/profile", headers=ORIGIN, json={"water_goal": 3}).status_code in (
        404,
        405,
    )
    login(client, family.a.user)
    own = f"/professional/students/{family.student_a.id}"
    assert client.get(own + "/hydration").json()["consumed_ml"] == 500
    assert client.patch(own, headers=ORIGIN, json={"water_goal": 2.5}).status_code == 200
    assert client.get(own + "/hydration").json()["goal_ml"] == 2500
    for suffix in ["/hydration", "/hydration/history"]:
        assert (
            client.get(f"/professional/students/{family.student_b.id}" + suffix).status_code == 404
        )
        assert client.get(f"/professional/students/{uuid4()}" + suffix).status_code == 404
    login(client, family.master)
    assert client.get(f"/master/students/{family.student_a.id}/hydration").status_code == 200
    assert (
        client.get(f"/master/students/{family.student_b.id}/hydration/history").status_code == 200
    )
    assert family.student_a.water_goal == 2.5


def test_water_roles_origin(client: TestClient, family: Family) -> None:
    assert client.get("/student/hydration").status_code == 401
    assert (
        client.post("/student/water-records", headers=ORIGIN, json={"amount_ml": 250}).status_code
        == 401
    )
    for actor in [family.master, family.a.user]:
        login(client, actor)
        assert client.get("/student/hydration").status_code == 403
        assert (
            client.post(
                "/student/water-records", headers=ORIGIN, json={"amount_ml": 250}
            ).status_code
            == 403
        )
    login(client, family.student_a.user)
    for headers in [{}, {"Origin": "https://bad.example"}]:
        assert (
            client.post(
                "/student/water-records", headers=headers, json={"amount_ml": 250}
            ).status_code
            == 403
        )


def test_summary_sql(client: TestClient, family: Family, db: Session) -> None:
    login(client, family.student_a.user)
    queries: list[str] = []

    def capture(
        conn: object,
        cursor: object,
        statement: str,
        parameters: object,
        context: object,
        many: bool,
    ) -> None:
        queries.append(statement)

    connection = db.connection()
    event.listen(connection, "before_cursor_execute", capture)
    try:
        assert client.get("/student/hydration/summary").status_code == 200
        assert client.get("/student/hydration/history").status_code == 200
    finally:
        event.remove(connection, "before_cursor_execute", capture)
    assert any("sum(" in sql.lower() for sql in queries)
    assert any("GROUP BY" in sql and "timezone(" in sql for sql in queries)
    assert not any("water_records.amount_ml AS" in sql for sql in queries)


def test_timezone_setting() -> None:
    with pytest.raises(ValidationError):
        Settings(business_timezone="not/a/timezone")
    # DST days are not always 24 hours; use local calendar boundaries.
    start, end = day_bounds(date(2026, 3, 8), "America/New_York")
    assert end - start == timedelta(hours=23)


family = assessment_family
