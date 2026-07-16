"use client";

import { useId, useState } from "react";
import { useRouter } from "next/navigation";

import { Button, FieldError, Input, Label } from "@/components/ui";
import type { AuthPageCopy } from "@/content";

/**
 * The shared email+password client island behind BOTH auth forms (P4.S2) — login
 * and signup differ only in their endpoint, copy, autocomplete hint, and
 * status→message mapping, so the submit/error/navigation logic lives here once
 * rather than being duplicated across two near-identical forms. `LoginForm` /
 * `SignupForm` are the thin, page-local wrappers that configure it.
 *
 * The flow: POST JSON to the same-origin BFF route (which satisfies its
 * `assertSameOrigin` check with no CSRF header needed) → on `res.ok` the server
 * has already sealed the vocky token into the httpOnly cookie, so we `replace()`
 * to the dashboard and `refresh()` to re-run the now-authenticated server tree.
 *
 * The response body is never read: the BFF answers a bare status by design, so
 * `errorFor(status)` is the whole error vocabulary. The password never touches a
 * URL and is cleared on failure so a wrong value isn't left staged.
 */
export interface CredentialsFormProps {
  /** BFF endpoint, e.g. `/api/auth/login`. */
  endpoint: string;
  copy: AuthPageCopy;
  /** `current-password` (login) or `new-password` (signup). */
  passwordAutoComplete: "current-password" | "new-password";
  /** Map a non-ok BFF status (or `null` for a network throw) to display copy. */
  errorFor: (status: number | null) => string;
}

export function CredentialsForm({
  endpoint,
  copy,
  passwordAutoComplete,
  errorFor,
}: CredentialsFormProps) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const baseId = useId();
  const emailId = `${baseId}-email`;
  const passwordId = `${baseId}-password`;
  const errorId = `${baseId}-error`;

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;
    setPending(true);
    setError(null);
    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (res.ok) {
        // Cookie is set — leave `pending` true through the navigation.
        router.replace("/dashboard");
        router.refresh();
        return;
      }
      setError(errorFor(res.status));
      setPassword("");
      setPending(false);
    } catch {
      setError(errorFor(null));
      setPending(false);
    }
  }

  const invalid = error !== null;

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor={emailId}>{copy.emailLabel}</Label>
        <Input
          id={emailId}
          type="email"
          name="email"
          value={email}
          placeholder={copy.emailPlaceholder}
          autoComplete="email"
          required
          disabled={pending}
          aria-invalid={invalid}
          aria-describedby={invalid ? errorId : undefined}
          onChange={(e) => {
            setEmail(e.target.value);
            if (error) setError(null);
          }}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor={passwordId}>{copy.passwordLabel}</Label>
        <Input
          id={passwordId}
          type="password"
          name="password"
          value={password}
          placeholder={copy.passwordPlaceholder}
          autoComplete={passwordAutoComplete}
          required
          disabled={pending}
          aria-invalid={invalid}
          aria-describedby={invalid ? errorId : undefined}
          onChange={(e) => {
            setPassword(e.target.value);
            if (error) setError(null);
          }}
        />
        {copy.passwordHint ? (
          <p className="text-caption text-steel">{copy.passwordHint}</p>
        ) : null}
      </div>

      <FieldError id={errorId}>{error ?? undefined}</FieldError>

      <Button
        type="submit"
        variant="primary"
        disabled={pending}
        className="w-full"
      >
        {pending ? copy.submitPendingLabel : copy.submitLabel}
      </Button>
    </form>
  );
}
