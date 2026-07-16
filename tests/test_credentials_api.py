"""End-to-end tests for per-project credentials + mandatory /api/* ingest auth.

Drives the whole ``create_app()`` stack over ASGI: the user-authed ``/app/*``
credential control-plane and the ``ProjectCredentialAuthMiddleware`` that guards
``/api/*``. Confirms the plaintext key is returned once, authenticates ingest,
is rejected once revoked, and that the endpoints never leak across tenants.
"""

from __future__ import annotations

import fakeredis.aioredis
import httpx
import pytest
from starlette.applications import Starlette

import vocky.api as api_module
from vocky.app import create_app
from vocky.capture_queue import CaptureQueue

_CAPTURE_BODY = {"message": "smoke", "source": {"product": "vocky-cli"}}


def _client(app: Starlette) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


async def _signup(client: httpx.AsyncClient, email: str) -> str:
    response = await client.post(
        "/auth/signup", json={"email": email, "password": "password-1234"}
    )
    assert response.status_code == 201, response.text
    return response.json()["token"]


async def _create_project(client: httpx.AsyncClient, token: str, name: str) -> str:
    response = await client.post(
        "/app/projects",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name},
    )
    assert response.status_code == 201, response.text
    return response.json()["project"]["id"]


@pytest.mark.anyio
async def test_credential_lifecycle_gates_api_ingest(
    configured_database: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(api_module, "get_capture_queue", lambda: CaptureQueue(redis_client))

    async with _client(create_app()) as client:
        token = await _signup(client, "owner@example.com")
        auth = {"Authorization": f"Bearer {token}"}
        project_id = await _create_project(client, token, "app one")

        # Mint: plaintext key returned once; the hash is never surfaced.
        created = await client.post(
            f"/app/projects/{project_id}/credentials", headers=auth, json={"name": "ci"}
        )
        assert created.status_code == 201
        body = created.json()
        key = body["key"]
        credential = body["credential"]
        assert key.startswith("vk_")
        assert credential["token_prefix"] == key[:12]
        assert credential["name"] == "ci"
        assert credential["revoked_at"] is None
        assert "token_hash" not in credential
        credential_id = credential["id"]

        # List: metadata only, no key and no hash.
        listed = await client.get(f"/app/projects/{project_id}/credentials", headers=auth)
        assert listed.status_code == 200
        creds = listed.json()["credentials"]
        assert [record["id"] for record in creds] == [credential_id]
        assert "token_hash" not in creds[0]
        assert "key" not in creds[0]

        # The key authenticates /api/feedback ingest.
        capture = await client.post(
            "/api/feedback", headers={"Authorization": f"Bearer {key}"}, json=_CAPTURE_BODY
        )
        assert capture.status_code == 202

        # Revoke; the same key is then rejected with the generic 401.
        deleted = await client.delete(
            f"/app/projects/{project_id}/credentials/{credential_id}", headers=auth
        )
        assert deleted.status_code == 204

        revoked = await client.post(
            "/api/feedback", headers={"Authorization": f"Bearer {key}"}, json=_CAPTURE_BODY
        )
        assert revoked.status_code == 401
        assert revoked.json() == {"detail": "Unauthorized"}

    await redis_client.aclose()


@pytest.mark.anyio
async def test_credential_endpoints_do_not_leak_across_tenants(
    configured_database: str,
) -> None:
    async with _client(create_app()) as client:
        owner_token = await _signup(client, "owner2@example.com")
        owner_auth = {"Authorization": f"Bearer {owner_token}"}
        project_id = await _create_project(client, owner_token, "owned")

        mint = await client.post(
            f"/app/projects/{project_id}/credentials", headers=owner_auth, json={}
        )
        credential_id = mint.json()["credential"]["id"]

        intruder_token = await _signup(client, "intruder@example.com")
        intruder_auth = {"Authorization": f"Bearer {intruder_token}"}

        # Every per-project credential op on another tenant's project answers 404.
        created = await client.post(
            f"/app/projects/{project_id}/credentials", headers=intruder_auth, json={}
        )
        listed = await client.get(
            f"/app/projects/{project_id}/credentials", headers=intruder_auth
        )
        deleted = await client.delete(
            f"/app/projects/{project_id}/credentials/{credential_id}",
            headers=intruder_auth,
        )

        assert created.status_code == 404
        assert listed.status_code == 404
        assert deleted.status_code == 404
