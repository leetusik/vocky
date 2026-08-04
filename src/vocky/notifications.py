"""Feedback capture email alerts over SMTP.

Sends one plain-text email to the owning org's owner whenever the worker
persists a captured feedback event. Stdlib ``smtplib`` only (Decision 1 in
``works/phases/active/P13/phase.md``) — the blocking send is isolated in
:func:`_send_message` and run through ``asyncio.to_thread`` so the worker's
single asyncio loop is never blocked.

Unconfigured SMTP (``Settings.smtp_configured`` False) cleanly disables
alerts: :meth:`FeedbackAlertNotifier.notify_feedback_persisted` returns
silently without attempting a recipient lookup or a send.

Exception policy: everything through step 3 (nothing to notify, unconfigured,
no owner email) returns rather than raises. The send path (recipient
resolution via the accounts service, and the SMTP send itself) is allowed to
raise out of this module — the caller (the worker's post-persist hook, P13.S3)
owns swallow-and-log containment so an alert failure can never re-enter the
capture job's requeue/dead-letter path.
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage
from typing import Protocol

from vocky.accounts import get_accounts_service
from vocky.config import Settings, get_settings
from vocky.feedback.types import FeedbackEventRecord

logger = logging.getLogger(__name__)


class OwnerEmailResolver(Protocol):
    """The one accounts-service method this module depends on (DI seam)."""

    async def get_owner_email_for_project(
        self, project_id: object
    ) -> str | None: ...


def _render_message(
    settings: Settings, record: FeedbackEventRecord, to_email: str
) -> EmailMessage:
    """Render the plain-text alert email for one persisted feedback event."""

    subject = f"Vocky feedback: {record.source_product}"
    if record.feedback_value is not None:
        subject = f"{subject} ({record.feedback_value})"

    lines = [
        f"Message: {record.message}",
        f"Feedback value: {record.feedback_value}",
        f"Comment: {record.comment}",
        f"Channel: {record.channel}",
        f"Source product: {record.source_product}",
        f"Event at: {record.event_at}",
        f"Ingested at: {record.ingested_at}",
        f"Event id: {record.id}",
        f"Project id: {record.project_id}",
    ]

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from_value
    message["To"] = to_email
    message.set_content("\n".join(lines))
    return message


def _send_message(settings: Settings, message: EmailMessage) -> None:
    """Blocking SMTP send. Isolated so it is trivially swappable/testable.

    ``SMTP_SSL`` when ``smtp_port == 465``, else ``SMTP`` + ``starttls()``.
    AUTH only when ``smtp_user`` is non-blank.
    """

    smtp_cls = smtplib.SMTP_SSL if settings.smtp_port == 465 else smtplib.SMTP
    with smtp_cls(settings.smtp_host, settings.smtp_port, timeout=10) as client:
        if smtp_cls is smtplib.SMTP:
            client.starttls()
        if settings.smtp_user.strip():
            client.login(settings.smtp_user, settings.smtp_password)
        client.send_message(message)


class FeedbackAlertNotifier:
    """Sends one plain-text owner alert email per persisted feedback event."""

    def __init__(
        self, *, settings: Settings, accounts_service: OwnerEmailResolver
    ) -> None:
        self._settings = settings
        self._accounts_service = accounts_service

    async def notify_feedback_persisted(
        self, record: FeedbackEventRecord | None
    ) -> None:
        """Notify the owning org's owner about one persisted feedback event.

        Returns silently (no lookup, no send) when there is nothing to notify
        about or alerts are disabled. See the module docstring for the
        exception policy of the remaining steps.
        """

        if record is None or record.project_id is None:
            logger.debug("Skipping feedback alert: no record or no project id")
            return

        if not self._settings.smtp_configured:
            return

        to_email = await self._accounts_service.get_owner_email_for_project(
            record.project_id
        )
        if to_email is None:
            logger.warning(
                "No owner email for project %s; skipping feedback alert",
                record.project_id,
            )
            return

        message = _render_message(self._settings, record, to_email)
        await asyncio.to_thread(_send_message, self._settings, message)


def get_feedback_alert_notifier() -> FeedbackAlertNotifier:
    """Return a feedback alert notifier built from house factories."""

    return FeedbackAlertNotifier(
        settings=get_settings(), accounts_service=get_accounts_service()
    )
