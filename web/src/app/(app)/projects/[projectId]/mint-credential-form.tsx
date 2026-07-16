"use client";

import { useActionState, useEffect, useId, useRef, useState } from "react";

import { Button, FieldError, Input, Label } from "@/components/ui";
import { PROJECT } from "@/content";
import { mintCredentialAction, type MintCredentialState } from "./actions";

/**
 * The form's initial state lives HERE, not in `actions.ts`: that file is
 * `"use server"`, where every export is registered as a callable server action,
 * so exporting a plain object from it makes Next throw "A 'use server' file can
 * only export async functions" at request time. A type-only import is safe.
 */
const INITIAL_STATE: MintCredentialState = { error: null };

export interface MintCredentialFormProps {
  projectId: string;
}

/**
 * P4.S4 — the mint-credential island, and the app's only handler of a plaintext
 * secret.
 *
 * The minted `vk_` key arrives in the action state and is rendered by
 * `<ShowOnceKey>` below. That is deliberate and is the ONE exception to the rule
 * that no vocky data crosses a client boundary: vocky returns the key exactly
 * once (it stores only the sha256 hash), so the user either copies it now or
 * loses it forever.
 *
 * Keeping it in the ACTION STATE rather than the server-rendered tree is what
 * makes it survive `revalidatePath`'s re-render — and what makes it vanish on the
 * next submit or navigation, with no persistence anywhere.
 */
export function MintCredentialForm({ projectId }: MintCredentialFormProps) {
  const [state, formAction, pending] = useActionState(
    mintCredentialAction,
    INITIAL_STATE,
  );

  const copy = PROJECT.mint;
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
    state.key !== undefined && state.ok !== undefined && state.ok !== dismissedAt;

  return (
    <div className="space-y-4">
      {showKey && state.key !== undefined && state.ok !== undefined ? (
        <ShowOnceKey
          value={state.key}
          onDismiss={() => setDismissedAt(state.ok ?? null)}
        />
      ) : null}

      <form ref={formRef} action={formAction} className="space-y-2">
        <input type="hidden" name="projectId" value={projectId} />

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

/**
 * The show-once panel: the only render of the plaintext key that will ever
 * happen. Selectable mono text plus a clipboard button — and an explicit warning,
 * because dismissing this panel destroys the key.
 */
function ShowOnceKey({
  value,
  onDismiss,
}: {
  value: string;
  onDismiss: () => void;
}) {
  const copy = PROJECT.keyPanel;
  const [copied, setCopied] = useState(false);
  const [copyFailed, setCopyFailed] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setCopyFailed(false);
    } catch {
      // Clipboard access can be denied (insecure origin, permissions). The key is
      // selectable text either way, so we just say so — and never log the value.
      setCopyFailed(true);
    }
  }

  return (
    <div
      role="alert"
      className="rounded-lg border border-hairline-strong bg-surface p-4"
    >
      <h4 className="text-body-md font-semibold text-ink">{copy.heading}</h4>
      <p className="mt-1 text-body-sm text-steel">{copy.warning}</p>

      <div className="mt-3 flex flex-wrap items-center gap-3">
        <code
          aria-label={copy.keyLabel}
          className="min-w-0 flex-1 overflow-x-auto rounded-md border border-hairline bg-canvas px-3 py-2.5 font-mono text-body-sm break-all text-ink select-all"
        >
          {value}
        </code>
        <Button type="button" variant="primary" size="sm" onClick={handleCopy}>
          {copied ? copy.copiedLabel : copy.copyLabel}
        </Button>
        <Button type="button" variant="secondary" size="sm" onClick={onDismiss}>
          {copy.dismissLabel}
        </Button>
      </div>

      {copyFailed ? (
        <p className="mt-2 text-body-sm text-destructive">
          {copy.copyFailedLabel}
        </p>
      ) : null}
    </div>
  );
}
