"use client";

import { useActionState, useId, useState } from "react";

import { Button } from "@/components/ui";
import { PROJECT } from "@/content";
import { revokeCredentialAction, type RevokeCredentialState } from "./actions";

/** Initial state lives here, not in the `"use server"` file — see `actions.ts`. */
const INITIAL_STATE: RevokeCredentialState = { error: null };

export interface RevokeCredentialButtonProps {
  projectId: string;
  credentialId: string;
  /** For the action's accessible name — `name ?? token_prefix`, never the key. */
  credentialLabel: string;
}

/**
 * P4.S4 — the per-row revoke island.
 *
 * Both ids ride as hidden inputs rather than `action.bind`, keeping the plain
 * `(prevState, formData)` action shape (the action re-validates them, and vocky
 * scopes the whole thing to the caller's tenant regardless).
 *
 * Revoke is irreversible and unprompted clicks sit one row apart, so it takes a
 * two-step confirm — rendered inline rather than as a `window.confirm`, which is
 * unstyleable and blocks the whole tab.
 *
 * `Button variant="destructiveOutline" size="sm"`: revoke is destructive, so the
 * vocky system (round 01, §4.4) gives it the danger-outlined treatment — a bordered
 * variant that reads as dangerous without shouting, kept small to sit in a table
 * row. (P4's note that the palette had no destructive variant is now obsolete:
 * vocky ships both `destructive` and `destructiveOutline`.)
 */
export function RevokeCredentialButton({
  projectId,
  credentialId,
  credentialLabel,
}: RevokeCredentialButtonProps) {
  const [state, formAction, pending] = useActionState(
    revokeCredentialAction,
    INITIAL_STATE,
  );

  const copy = PROJECT.revoke;
  const errorId = `${useId()}-error`;
  const [confirming, setConfirming] = useState(false);

  return (
    <form action={formAction} className="inline-flex flex-col items-end gap-1">
      <input type="hidden" name="projectId" value={projectId} />
      <input type="hidden" name="credentialId" value={credentialId} />

      {confirming ? (
        <div className="inline-flex items-center gap-2">
          <span className="text-caption text-steel">{copy.confirmPrompt}</span>
          <Button
            type="submit"
            variant="destructiveOutline"
            size="sm"
            disabled={pending}
            aria-describedby={state.error ? errorId : undefined}
          >
            {pending ? copy.pendingLabel : copy.confirmLabel}
          </Button>
          <Button
            type="button"
            variant="link"
            onClick={() => setConfirming(false)}
            disabled={pending}
          >
            {copy.cancelLabel}
          </Button>
        </div>
      ) : (
        <Button
          type="button"
          variant="destructiveOutline"
          size="sm"
          onClick={() => setConfirming(true)}
          aria-label={`${copy.ariaLabelPrefix} ${credentialLabel}`}
        >
          {copy.label}
        </Button>
      )}

      {state.error ? (
        <p id={errorId} role="alert" className="text-caption text-destructive">
          {state.error}
        </p>
      ) : null}
    </form>
  );
}
