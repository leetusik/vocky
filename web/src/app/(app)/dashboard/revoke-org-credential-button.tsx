"use client";

import { useActionState, useId, useState } from "react";

import { Button } from "@/components/ui";
import { DASHBOARD } from "@/content";
import {
  revokeOrgCredentialAction,
  type RevokeOrgCredentialState,
} from "./actions";

/** Initial state lives here, not in the `"use server"` file — see `actions.ts`. */
const INITIAL_STATE: RevokeOrgCredentialState = { error: null };

export interface RevokeOrgCredentialButtonProps {
  credentialId: string;
  /** For the action's accessible name — `name ?? token_prefix`, never the key. */
  credentialLabel: string;
}

/**
 * P10.S4 — the org-key per-row revoke island, the sibling of
 * `RevokeCredentialButton` (project-scoped, `../projects/[projectId]/`) but
 * with no `projectId`: an org-level key is revoked by id alone (vocky scopes
 * `DELETE /app/credentials/{id}` to the caller's tenant AND requires the row
 * be org-level, regardless of what this client sends).
 *
 * Same two-step inline confirm as the project-scoped sibling — revoke is
 * irreversible and unprompted clicks sit one row apart.
 */
export function RevokeOrgCredentialButton({
  credentialId,
  credentialLabel,
}: RevokeOrgCredentialButtonProps) {
  const [state, formAction, pending] = useActionState(
    revokeOrgCredentialAction,
    INITIAL_STATE,
  );

  const copy = DASHBOARD.orgKeys.revoke;
  const errorId = `${useId()}-error`;
  const [confirming, setConfirming] = useState(false);

  return (
    <form action={formAction} className="inline-flex flex-col items-end gap-1">
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
