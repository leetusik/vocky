"use client";

import { useState } from "react";

import { Button } from "@/components/ui";

/**
 * Copy shape for the show-once panel. Matches `PROJECT.keyPanel` and
 * `DASHBOARD.orgKeys.keyPanel` — both mint surfaces (project-bound and
 * org-level) render the identical show-once behavior with their own copy.
 */
export interface ShowOnceKeyCopy {
  heading: string;
  warning: string;
  keyLabel: string;
  copyLabel: string;
  copiedLabel: string;
  copyFailedLabel: string;
  dismissLabel: string;
}

export interface ShowOnceKeyProps {
  value: string;
  copy: ShowOnceKeyCopy;
  onDismiss: () => void;
}

/**
 * P10.S4 — lifted out of the project mint form (P4.S4, module-private there)
 * so the dashboard's org-key mint form can render the identical show-once
 * behavior rather than a copy. vocky returns the plaintext `vk_…` key EXACTLY
 * ONCE — project-bound or org-level, the shape is identical either way — and
 * persists only its sha256 hash, so this is the only render of the value that
 * will ever happen: selectable mono text plus a clipboard button, with an
 * explicit warning that dismissing the panel destroys the key.
 */
export function ShowOnceKey({ value, copy, onDismiss }: ShowOnceKeyProps) {
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
      className="rounded-lg border border-mint bg-surface-green p-4"
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
