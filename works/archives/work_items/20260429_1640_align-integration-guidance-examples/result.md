# Result

- Work item: works/current/20260429_1640_align-integration-guidance-examples
- Created at: 20260429_1640
- Phase ID: P1
- Phase: Feedback Field and Role Contract
- Slice ID: P1.S4
- Slice: align integration guidance and examples
- Review status: completed
- Reviewer: self
- Next action: Start P1.REVIEW phase review.

## Outcome

Updated integration-facing docs and packaged operator examples to cover `user_id`, trigger fields, target fields, process context, and metadata. Examples now show when to send caller-owned user identity, trigger type/message/metadata, exact reviewed target, safe `used_context`, source metadata, and attributes. Guidance explicitly says not to send raw hidden chain-of-thought.

## Deviations from plan

None.

## Validation run

- `uv run python -m json.tool src/vocky/admin_assets/docs.json >/dev/null`
- `uv run pytest tests/test_admin_ui.py`
- `git diff --check`

## Files changed

- `README.md`
- `docs/action-feedback-integration.md`
- `src/vocky/admin_assets/docs.json`
- `tests/test_admin_ui.py`
- `works/backlog.md`
- `works/current/20260429_1640_align-integration-guidance-examples/plan.md`
- `works/current/20260429_1640_align-integration-guidance-examples/result.md`

## Docs updated

- `README.md`
- `docs/action-feedback-integration.md`
- `src/vocky/admin_assets/docs.json`

## Roadmap updates

- P1.S4 is ready to archive. P1.REVIEW should validate the whole phase.

## Retrospective

- The examples now make the identity/trigger/target split visible without introducing new REST-only aliases or public review APIs.
