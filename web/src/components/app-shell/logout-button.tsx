"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { APP_SHELL } from "@/content";

/**
 * Logout control (P4.S2) — adapted from hi2vi_web's `(console)/logout-button.tsx`.
 * POSTs the same-origin BFF logout route (which revokes the token at vocky and
 * clears the sealed cookie), then replaces to /login and refreshes so the
 * now-unauthenticated server tree re-runs.
 *
 * Best-effort by design: we navigate even if the POST throws, because the `(app)`
 * server guard — not this button — is the real gate. The same-origin fetch
 * satisfies the route's CSRF check with no custom header.
 */
export function LogoutButton() {
  const router = useRouter();
  const [pending, setPending] = useState(false);

  async function handleLogout() {
    if (pending) return;
    setPending(true);
    try {
      await fetch("/api/auth/logout", { method: "POST" });
    } catch {
      // ignore — navigate anyway; the server guard re-checks on the next load
    } finally {
      router.replace("/login");
      router.refresh();
    }
  }

  return (
    <button
      type="button"
      onClick={handleLogout}
      disabled={pending}
      className="rounded-md border border-hairline-soft px-[11px] py-1.5 text-caption font-bold text-steel transition hover:border-hairline-strong hover:text-charcoal disabled:cursor-not-allowed disabled:opacity-70"
    >
      {pending ? APP_SHELL.logoutPendingLabel : APP_SHELL.logoutLabel}
    </button>
  );
}
