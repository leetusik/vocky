# Plan

- Work item: works/current/20260427_2325_build_rest_capture_try_ui
- Created at: 20260427_2325
- Phase ID: P4
- Phase: Working REST capture Try docs
- Slice ID: P4.S2
- Slice: build REST capture try UI

## Goal

Implement the Admin Docs `rest_capture_try` block renderer and same-origin browser request flow for trying `POST /api/feedback`.

## Scope

- Add client-side state for the REST capture API token and try request output.
- Render a `rest_capture_try` docs block with API token password input, editable JSON payload textarea, send action, and request/status/response/error output.
- Use `sessionStorage` for the API token under `vocky.apiToken`.
- POST to `/api/feedback` with JSON headers and optional `Authorization: Bearer <token>`.
- Add focused CSS for the try form and output areas.

## Context

- Existing docs rendering is static JSON-driven block rendering in `src/vocky/admin_assets/app.js`.
- The try block is internal to packaged Admin UI docs and must not add backend routes.
- `P4.S3` will add the actual docs.json block and tests; this slice makes the renderer support it.

## Milestones

1. Add REST try state helpers and request execution code.
2. Extend docs block rendering for `rest_capture_try`.
3. Add CSS for the form, payload editor, and output panels.
4. Run JS syntax validation.

## Validation

- `node --check src/vocky/admin_assets/app.js`

## Risks / open questions

- Avoid persisting the API token beyond `sessionStorage`.
- Keep error reporting useful for JSON parse failures, HTTP errors, and network failures without inventing server behavior.

## Docs to update

- None in this slice; `P4.S3` updates `docs.json`.
