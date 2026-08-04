"""Tests for the feedback alert notifier (pure-Python, no DB)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

import vocky.notifications as notifications_module
from vocky.config import Settings
from vocky.feedback.types import FeedbackEventRecord
from vocky.notifications import FeedbackAlertNotifier


def _settings(**overrides: object) -> Settings:
    kwargs: dict[str, object] = {"DATABASE_URL": "postgresql://unused"}
    kwargs.update(overrides)
    return Settings(**kwargs)


def _record(**overrides: object) -> FeedbackEventRecord:
    fields: dict[str, object] = {
        "id": uuid4(),
        "project_id": uuid4(),
        "message": "It broke",
        "source_product": "acme-app",
        "feedback_value": -1,
        "comment": "did not work",
        "channel": "widget",
        "source_integration": None,
        "conversation_id": None,
        "session_id": None,
        "user_id": None,
        "trigger_type": None,
        "trigger_message": None,
        "trigger_metadata": {},
        "target_type": None,
        "target_id": None,
        "target_role": None,
        "target_text": None,
        "event_at": datetime.now(UTC),
        "ingested_at": datetime.now(UTC),
        "tags": (),
        "messages": (),
        "used_context": (),
        "source_metadata": {},
        "attributes": {},
    }
    fields.update(overrides)
    return FeedbackEventRecord(**fields)


class RecordingAccountsService:
    """Fake accounts service: DI seam for `get_owner_email_for_project`."""

    def __init__(self, *, owner_email: str | None) -> None:
        self.owner_email = owner_email
        self.calls: list[object] = []

    async def get_owner_email_for_project(self, project_id: object) -> str | None:
        self.calls.append(project_id)
        return self.owner_email


async def test_unconfigured_settings_skips_lookup_and_send(monkeypatch) -> None:
    send_calls: list[object] = []
    monkeypatch.setattr(
        notifications_module, "_send_message", lambda *a, **k: send_calls.append(a)
    )
    accounts = RecordingAccountsService(owner_email="owner@example.com")
    notifier = FeedbackAlertNotifier(settings=_settings(), accounts_service=accounts)

    await notifier.notify_feedback_persisted(_record())

    assert accounts.calls == []
    assert send_calls == []


@pytest.mark.parametrize("record", [None, "project_id_none"])
async def test_no_record_or_no_project_id_skips_lookup_and_send(
    monkeypatch, record: object
) -> None:
    send_calls: list[object] = []
    monkeypatch.setattr(
        notifications_module, "_send_message", lambda *a, **k: send_calls.append(a)
    )
    accounts = RecordingAccountsService(owner_email="owner@example.com")
    settings = _settings(VOCKY_SMTP_HOST="smtp.example.com", VOCKY_SMTP_FROM="a@b.com")
    notifier = FeedbackAlertNotifier(settings=settings, accounts_service=accounts)

    given_record = None if record is None else _record(project_id=None)
    await notifier.notify_feedback_persisted(given_record)

    assert accounts.calls == []
    assert send_calls == []


async def test_configured_and_owner_resolves_sends_once(monkeypatch) -> None:
    send_calls: list[tuple[object, object]] = []
    monkeypatch.setattr(
        notifications_module,
        "_send_message",
        lambda settings, message: send_calls.append((settings, message)),
    )
    accounts = RecordingAccountsService(owner_email="owner@example.com")
    settings = _settings(
        VOCKY_SMTP_HOST="smtp.example.com",
        VOCKY_SMTP_FROM="alerts@example.com",
    )
    notifier = FeedbackAlertNotifier(settings=settings, accounts_service=accounts)
    record = _record(message="It broke badly", feedback_value=-1)

    await notifier.notify_feedback_persisted(record)

    assert len(send_calls) == 1
    sent_settings, message = send_calls[0]
    assert sent_settings is settings
    assert message["To"] == "owner@example.com"
    assert message["From"] == "alerts@example.com"
    assert "acme-app" in message["Subject"]
    body = message.get_content()
    assert "It broke badly" in body
    assert "-1" in body


async def test_owner_lookup_returns_none_skips_send(monkeypatch) -> None:
    send_calls: list[object] = []
    monkeypatch.setattr(
        notifications_module, "_send_message", lambda *a, **k: send_calls.append(a)
    )
    accounts = RecordingAccountsService(owner_email=None)
    settings = _settings(VOCKY_SMTP_HOST="smtp.example.com", VOCKY_SMTP_FROM="a@b.com")
    notifier = FeedbackAlertNotifier(settings=settings, accounts_service=accounts)

    await notifier.notify_feedback_persisted(_record())

    assert len(accounts.calls) == 1
    assert send_calls == []
