"""Org-level ingest credentials end-to-end (``/app/credentials``) — P10.S3.

Drives the whole ``create_app()`` stack over ASGI: mint an org key through the
real route, use it across every project in its org, and prove the org surface
can neither revoke nor probe a credential outside its exact scope. The
enforcement-level (service-constructed) cases live in
``tests/test_org_credential_scope.py``; these pin the surface that turns them on.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import fakeredis.aioredis
import httpx
import pytest
from sqlalchemy import text
from starlette.applications import Starlette

import vocky.api as api_module
from vocky.app import create_app
from vocky.capture_queue import CaptureQueue
from vocky.db import get_engine

_CAPTURE = {"message": "org capture", "source": {"product": "vocky-cli"}}


def _client(app: Starlette) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    )


async def _signup(client: httpx.AsyncClient, email: str) -> str:
    response = await client.post(
        "/auth/signup", json={"email": email, "password": "password-1234"}
    )
    assert response.status_code == 201, response.text
    return response.json()["token"]


async def _projects(client: httpx.AsyncClient, token: str) -> dict[str, str]:
    response = await client.get(
        "/app/projects", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200, response.text
    return {entry["name"]: entry["id"] for entry in response.json()["projects"]}


async def _mint_org_key(client: httpx.AsyncClient, token: str) -> tuple[str, str]:
    """Mint an org key through the real route; return ``(key, credential_id)``."""

    response = await client.post(
        "/app/credentials", headers={"Authorization": f"Bearer {token}"}, json={}
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return body["key"], body["credential"]["id"]


async def _seed_feedback(feedback_id: str, project_id: str, hour: int) -> None:
    async with get_engine().begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO feedback_events "
                "(id, message, source_product, ingested_at, project_id) VALUES "
                "(:id, 'row', 'changple5', :ingested_at, :project_id)"
            ),
            {
                "id": feedback_id,
                "ingested_at": datetime(2026, 6, 1, hour, tzinfo=UTC),
                "project_id": project_id,
            },
        )


@pytest.mark.anyio
async def test_org_key_spans_every_project_in_its_org(
    configured_database: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mint → capture into two projects → read both back through the one key."""

    redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    queue = CaptureQueue(redis_client)
    monkeypatch.setattr(api_module, "get_capture_queue", lambda: queue)

    async with _client(create_app()) as client:
        token = await _signup(client, "org-owner@example.com")
        auth = {"Authorization": f"Bearer {token}"}

        minted = await client.post(
            "/app/credentials", headers=auth, json={"name": "org ci"}
        )
        assert minted.status_code == 201, minted.text
        key = minted.json()["key"]
        credential = minted.json()["credential"]
        assert key.startswith("vk_")
        assert credential["project_id"] is None  # org-level, not bound
        assert credential["token_prefix"] == key[:12]
        assert credential["name"] == "org ci"
        assert "token_hash" not in credential

        listed = await client.get("/app/credentials", headers=auth)
        assert listed.status_code == 200
        assert [record["id"] for record in listed.json()["credentials"]] == [
            credential["id"]
        ]

        ingest = {"Authorization": f"Bearer {key}"}
        for project in ("alpha", "beta"):
            captured = await client.post(
                "/api/feedback", headers=ingest, json={**_CAPTURE, "project": project}
            )
            assert captured.status_code == 202, captured.text

        projects = await _projects(client, token)
        assert set(projects) == {"default", "alpha", "beta"}

        first = await queue.pop_job(timeout_seconds=1)
        second = await queue.pop_job(timeout_seconds=1)
        assert first is not None and second is not None
        assert [str(first.payload.project_id), str(second.payload.project_id)] == [
            projects["alpha"],
            projects["beta"],
        ]

        alpha_row = "00000000-0000-0000-0000-0000000000c1"
        beta_row = "00000000-0000-0000-0000-0000000000c2"
        await _seed_feedback(alpha_row, projects["alpha"], 10)
        await _seed_feedback(beta_row, projects["beta"], 11)

        read = await client.get("/api/project/feedback", headers=ingest)
        assert read.status_code == 200
        records = read.json()["records"]
        assert {record["id"] for record in records} == {alpha_row, beta_row}
        assert {record["project_id"] for record in records} == {
            projects["alpha"],
            projects["beta"],
        }

        # The org key appears in its own usage view: a per-project listing
        # structurally cannot return an org-level row (P10.S3 unions them in).
        usage = await client.get("/api/project/usage", headers=ingest)
        assert usage.status_code == 200
        assert key[:12] in {
            entry["token_prefix"] for entry in usage.json()["credentials"]
        }

    await redis_client.aclose()


@pytest.mark.anyio
async def test_org_delete_is_404_never_403_even_for_a_bound_key(
    configured_database: str,
) -> None:
    """The org route reaches org-level rows of the caller's tenant, and nothing else."""

    async with _client(create_app()) as client:
        token = await _signup(client, "org-probe@example.com")
        auth = {"Authorization": f"Bearer {token}"}
        project_id = (await _projects(client, token))["default"]

        bound = await client.post(
            f"/app/projects/{project_id}/credentials", headers=auth, json={}
        )
        bound_id = bound.json()["credential"]["id"]

        other_token = await _signup(client, "org-probe-other@example.com")
        _other_key, other_id = await _mint_org_key(client, other_token)

        # A *project-bound* id of the caller's own tenant 404s exactly like
        # another tenant's org id and like an id that does not exist at all.
        probes = [
            await client.delete(f"/app/credentials/{bound_id}", headers=auth),
            await client.delete(f"/app/credentials/{other_id}", headers=auth),
            await client.delete(f"/app/credentials/{uuid4()}", headers=auth),
        ]
        assert [response.status_code for response in probes] == [404, 404, 404]
        assert {response.json()["detail"] for response in probes} == {
            "credential not found"
        }

        malformed = await client.delete("/app/credentials/not-a-uuid", headers=auth)
        assert malformed.status_code == 400

        # No probe revoked anything.
        mine = await client.get(
            f"/app/projects/{project_id}/credentials", headers=auth
        )
        assert mine.json()["credentials"][0]["revoked_at"] is None
        theirs = await client.get(
            "/app/credentials", headers={"Authorization": f"Bearer {other_token}"}
        )
        assert theirs.json()["credentials"][0]["revoked_at"] is None


@pytest.mark.anyio
async def test_revoking_an_org_key_rejects_ingest(configured_database: str) -> None:
    async with _client(create_app()) as client:
        token = await _signup(client, "org-revoke@example.com")
        auth = {"Authorization": f"Bearer {token}"}
        key, credential_id = await _mint_org_key(client, token)
        ingest = {"Authorization": f"Bearer {key}"}

        assert (await client.get("/api/project/usage", headers=ingest)).status_code == 200

        deleted = await client.delete(f"/app/credentials/{credential_id}", headers=auth)
        assert deleted.status_code == 204

        rejected = await client.get("/api/project/usage", headers=ingest)
        assert rejected.status_code == 401
        assert rejected.json() == {"detail": "Unauthorized"}

        # Revoked rows stay listed (with a revocation stamp), as per project.
        listed = (await client.get("/app/credentials", headers=auth)).json()
        assert listed["credentials"][0]["revoked_at"] is not None


@pytest.mark.anyio
async def test_org_key_never_reaches_another_tenants_feedback(
    configured_database: str,
) -> None:
    """404 — never 403 — on every per-record verb, for a cross-tenant id."""

    async with _client(create_app()) as client:
        mine = await _signup(client, "org-isolation-a@example.com")
        theirs = await _signup(client, "org-isolation-b@example.com")
        outside_project = (await _projects(client, theirs))["default"]

        outside = "00000000-0000-0000-0000-0000000000c3"
        await _seed_feedback(outside, outside_project, 12)

        key, _credential_id = await _mint_org_key(client, mine)
        ingest = {"Authorization": f"Bearer {key}"}
        url = f"/api/project/feedback/{outside}"

        responses = [
            await client.get(url, headers=ingest),
            await client.patch(url, headers=ingest, json={"comment": "probe"}),
            await client.delete(url, headers=ingest),
            await client.post(f"{url}/comments", headers=ingest, json={"body": "probe"}),
            await client.get(f"{url}/comments", headers=ingest),
            await client.get(f"{url}/attachments/{uuid4()}", headers=ingest),
        ]

        assert [response.status_code for response in responses] == [404] * 6
        assert {response.json()["detail"] for response in responses} == {
            "feedback not found"
        }
        # The list surface never leaks it either.
        listed = await client.get("/api/project/feedback", headers=ingest)
        assert listed.json()["records"] == []


@pytest.mark.anyio
async def test_project_bound_mint_is_unchanged(configured_database: str) -> None:
    """The additive claim, pinned: a per-project mint is bound and stays invisible here."""

    async with _client(create_app()) as client:
        token = await _signup(client, "org-additive@example.com")
        auth = {"Authorization": f"Bearer {token}"}
        project_id = (await _projects(client, token))["default"]

        created = await client.post(
            f"/app/projects/{project_id}/credentials", headers=auth, json={"name": "ci"}
        )
        assert created.status_code == 201
        credential = created.json()["credential"]
        assert credential["project_id"] == project_id
        assert set(credential) == {
            "id",
            "project_id",
            "name",
            "token_prefix",
            "created_at",
            "last_used_at",
            "revoked_at",
        }

        # The two listings are disjoint: a bound key is not an org key.
        assert (await client.get("/app/credentials", headers=auth)).json() == {
            "credentials": []
        }
