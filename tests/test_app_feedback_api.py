"""Cross-project feedback read + multilingual search tests (`/app/feedback`)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text
from starlette.applications import Starlette

from vocky.accounts.auth import AuthError, auth_error_handler
from vocky.app_api import routes as app_api_routes
from vocky.app_feedback_api import routes as app_feedback_routes
from vocky.auth_api import routes as auth_routes
from vocky.db import get_engine


def make_app() -> Starlette:
    """Test app: auth + control-plane + cross-project feedback routes, 401 handler."""

    return Starlette(
        routes=[*auth_routes, *app_api_routes, *app_feedback_routes],
        exception_handlers={AuthError: auth_error_handler},
    )


def _client() -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=make_app())
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


async def _signup(client: httpx.AsyncClient, email: str) -> dict[str, str]:
    """Sign up a user and return auth headers for the issued session token."""

    response = await client.post(
        "/auth/signup", json={"email": email, "password": "hunter2pass"}
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['token']}"}


async def _make_project(client: httpx.AsyncClient, headers: dict[str, str], name: str) -> str:
    response = await client.post("/app/projects", json={"name": name}, headers=headers)
    assert response.status_code == 201
    return response.json()["project"]["id"]


async def _seed_feedback(
    *,
    feedback_id: str,
    project_id: str,
    ingested_at: datetime,
    message: str,
) -> None:
    async with get_engine().begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO feedback_events "
                "(id, message, source_product, ingested_at, project_id) "
                "VALUES (:id, :message, 'changple5', :ingested_at, :project_id)"
            ),
            {
                "id": feedback_id,
                "message": message,
                "ingested_at": ingested_at,
                "project_id": project_id,
            },
        )


@pytest.mark.anyio
async def test_lists_and_searches_across_projects(configured_database: str) -> None:
    async with _client() as client:
        headers = await _signup(client, "alice@example.com")
        project_a = await _make_project(client, headers, "Project A")
        project_b = await _make_project(client, headers, "Project B")

        korean = "00000000-0000-0000-0000-0000000000a1"
        korean_particle = "00000000-0000-0000-0000-0000000000a2"
        english = "00000000-0000-0000-0000-0000000000a3"
        # Korean row in project A; particle-attached Korean row in project B.
        await _seed_feedback(
            feedback_id=korean,
            project_id=project_a,
            ingested_at=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
            message="결제 오류가 있어요",
        )
        await _seed_feedback(
            feedback_id=korean_particle,
            project_id=project_b,
            ingested_at=datetime(2026, 6, 1, 11, 0, tzinfo=UTC),
            message="결제를 못 했습니다",
        )
        await _seed_feedback(
            feedback_id=english,
            project_id=project_a,
            ingested_at=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
            message="checkout button is broken",
        )

        listed = await client.get("/app/feedback", headers=headers)
        korean_hits = await client.get("/app/feedback", params={"q": "결제"}, headers=headers)
        english_hits = await client.get(
            "/app/feedback", params={"q": "checkout"}, headers=headers
        )
        no_hits = await client.get(
            "/app/feedback", params={"q": "환불정책없음"}, headers=headers
        )
        first = await client.get("/app/feedback", params={"limit": "1"}, headers=headers)
        second = await client.get(
            "/app/feedback",
            params={"limit": "1", "cursor": first.json()["next_cursor"]},
            headers=headers,
        )

    # Cross-project aggregation, newest-first, each record tagged with project_id.
    assert listed.status_code == 200
    records = listed.json()["records"]
    assert [r["id"] for r in records] == [english, korean_particle, korean]
    assert {r["project_id"] for r in records} == {project_a, project_b}

    # Korean substring matches BOTH the bare and the 조사-attached (결제를) row.
    assert {r["id"] for r in korean_hits.json()["records"]} == {korean, korean_particle}
    # English substring match; an unrelated term matches nothing.
    assert [r["id"] for r in english_hits.json()["records"]] == [english]
    assert no_hits.json()["records"] == []

    # Keyset paging composes across projects.
    assert [r["id"] for r in first.json()["records"]] == [english]
    assert [r["id"] for r in second.json()["records"]] == [korean_particle]


@pytest.mark.anyio
async def test_project_id_narrowing_and_cross_tenant_isolation(
    configured_database: str,
) -> None:
    async with _client() as client:
        headers = await _signup(client, "owner@example.com")
        project_a = await _make_project(client, headers, "Project A")
        project_b = await _make_project(client, headers, "Project B")
        mine_a = "00000000-0000-0000-0000-0000000000b1"
        mine_b = "00000000-0000-0000-0000-0000000000b2"
        await _seed_feedback(
            feedback_id=mine_a,
            project_id=project_a,
            ingested_at=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
            message="row in A",
        )
        await _seed_feedback(
            feedback_id=mine_b,
            project_id=project_b,
            ingested_at=datetime(2026, 6, 1, 11, 0, tzinfo=UTC),
            message="row in B",
        )

        # A second tenant with its own project + feedback.
        other_headers = await _signup(client, "intruder@example.com")
        project_x = await _make_project(client, other_headers, "Project X")
        theirs = "00000000-0000-0000-0000-0000000000b3"
        await _seed_feedback(
            feedback_id=theirs,
            project_id=project_x,
            ingested_at=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
            message="secret in X",
        )

        narrowed = await client.get(
            "/app/feedback", params={"project_id": project_a}, headers=headers
        )
        not_owned = await client.get(
            "/app/feedback", params={"project_id": project_x}, headers=headers
        )
        unknown = await client.get(
            "/app/feedback", params={"project_id": str(uuid4())}, headers=headers
        )
        malformed = await client.get(
            "/app/feedback", params={"project_id": "not-a-uuid"}, headers=headers
        )
        owner_list = await client.get("/app/feedback", headers=headers)
        cross_get = await client.get(f"/app/feedback/{theirs}", headers=headers)

    # ?project_id narrows to a single owned project.
    assert [r["id"] for r in narrowed.json()["records"]] == [mine_a]
    # Narrowing to a project the caller does not own is 404 (never 403), as is an
    # unknown id; a malformed id is 400.
    assert not_owned.status_code == 404
    assert unknown.status_code == 404
    assert malformed.status_code == 400

    # The second tenant's feedback never appears and get-one on it is 404.
    owner_ids = {r["id"] for r in owner_list.json()["records"]}
    assert owner_ids == {mine_a, mine_b}
    assert theirs not in owner_ids
    assert cross_get.status_code == 404


@pytest.mark.anyio
async def test_requires_session_token(configured_database: str) -> None:
    async with _client() as client:
        no_token = await client.get("/app/feedback")
        bad_token = await client.get(
            "/app/feedback", headers={"Authorization": "Bearer nope"}
        )

    assert no_token.status_code == 401
    assert no_token.json() == {"detail": "Unauthorized"}
    assert no_token.headers["www-authenticate"] == "Bearer"
    assert bad_token.status_code == 401
