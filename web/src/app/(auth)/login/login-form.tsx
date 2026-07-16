"use client";

import { AUTH_ERRORS, LOGIN_PAGE } from "@/content";

import { CredentialsForm } from "../credentials-form";

/**
 * Login form (P4.S2) — configures the shared credentials island for
 * `POST /api/auth/login`.
 *
 * Note the 401 copy: vocky answers an identical generic 401 for an unknown email
 * and for a wrong password (no account enumeration), the BFF forwards only that
 * bare status, and this maps it to ONE message — the property is preserved all the
 * way to the UI.
 */
function errorFor(status: number | null): string {
  switch (status) {
    case 401:
      return AUTH_ERRORS.invalidCredentials;
    case 400:
    case 422:
      return AUTH_ERRORS.invalidInput;
    case 429:
      return AUTH_ERRORS.rateLimited;
    default:
      return AUTH_ERRORS.generic;
  }
}

export function LoginForm() {
  return (
    <CredentialsForm
      endpoint="/api/auth/login"
      copy={LOGIN_PAGE}
      passwordAutoComplete="current-password"
      errorFor={errorFor}
    />
  );
}
