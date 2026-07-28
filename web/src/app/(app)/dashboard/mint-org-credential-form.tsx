"use client";

import { useActionState, useEffect, useId, useRef, useState } from "react";

import { ShowOnceKey } from "@/components/show-once-key";
import { Button, FieldError, Input, Label } from "@/components/ui";
import { DASHBOARD } from "@/content";
import {
  mintOrgCredentialAction,
  type MintOrgCredentialState,
} from "./actions";

/**
 * The form's initial state lives HERE, not in `actions.ts`: that file is
 * `"use server"`, where every export is registered as a callable server
 * action, so exporting a plain object from it makes Next throw "A 'use
 * server' file can only export async functions" at request time. A
 * type-only import is safe. See `../projects/[projectId]/actions.ts:16-23`.
 */
const INITIAL_STATE: MintOrgCredentialState = { error: null };

/**
 * P10.S4 — the org-key mint island on `/dashboard`, the sibling of
 * `MintCredentialForm` (project-scoped, `../projects/[projectId]/`) but with
 * no `projectId`: an org-level key is not bound to any single project. Same
 * show-once handling — via the SHARED `<ShowOnceKey>` — for the same reason:
 * vocky returns the plaintext `vk_` key exactly once.
 */
export function MintOrgCredentialForm() {
  const [state, formAction, pending] = useActionState(
    mintOrgCredentialAction,
    INITIAL_STATE,
  );

  const copy = DASHBOARD.orgKeys.mint;
  const baseId = useId();
  const nameId = `${baseId}-name`;
  const hintId = `${baseId}-hint`;
  const errorId = `${baseId}-error`;
  const formRef = useRef<HTMLFormElement>(null);

  // Dismissal is keyed by the `ok` stamp of the panel that was dismissed, not a
  // boolean: a plain `dismissed` flag would stay true and swallow the NEXT
  // minted key — the one case where a silent miss is unrecoverable.
  const [dismissedAt, setDismissedAt] = useState<number | null>(null);

  // Clear the field after a successful mint. Keyed off `ok` (bumped per success)
  // rather than `error === null`, which is also the INITIAL state.
  useEffect(() => {
    if (state.ok) formRef.current?.reset();
  }, [state.ok]);

  const invalid = state.error !== null;
  const showKey =
    state.key !== undefined &&
    state.ok !== undefined &&
    state.ok !== dismissedAt;

  return (
    <div className="space-y-4">
      {showKey && state.key !== undefined && state.ok !== undefined ? (
        <ShowOnceKey
          value={state.key}
          copy={DASHBOARD.orgKeys.keyPanel}
          onDismiss={() => setDismissedAt(state.ok ?? null)}
        />
      ) : null}

      <form ref={formRef} action={formAction} className="space-y-2">
        <Label htmlFor={nameId}>{copy.nameLabel}</Label>
        <p id={hintId} className="text-caption text-steel">
          {copy.nameHint}
        </p>
        <div className="flex flex-wrap items-start gap-3">
          {/* No `required`: vocky defaults an omitted name to `null`, so an
              unnamed key is a legitimate, first-class case. */}
          <Input
            id={nameId}
            name="name"
            type="text"
            placeholder={copy.namePlaceholder}
            maxLength={200}
            disabled={pending}
            aria-invalid={invalid}
            aria-describedby={invalid ? `${hintId} ${errorId}` : hintId}
            className="min-w-0 flex-1"
          />
          <Button type="submit" variant="primary" disabled={pending}>
            {pending ? copy.submitPendingLabel : copy.submitLabel}
          </Button>
        </div>
        <FieldError id={errorId}>{state.error ?? undefined}</FieldError>
      </form>
    </div>
  );
}
