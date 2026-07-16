"use client";

import { AUTH_ERRORS, SIGNUP_PAGE } from "@/content";

import { CredentialsForm } from "../credentials-form";

/**
 * Signup form (P4.S2) — configures the shared credentials island for
 * `POST /api/auth/signup`. On success vocky has provisioned the user, their
 * tenant, and the owner membership, and the BFF has already sealed the returned
 * token into the cookie — so a new account lands on the dashboard authenticated,
 * with no second login step.
 *
 * 409 is the duplicate-email case (the one place signup and login diverge); 400 is
 * vocky's own validation, most often the 8-character password minimum.
 */
function errorFor(status: number | null): string {
  switch (status) {
    case 409:
      return AUTH_ERRORS.emailTaken;
    case 400:
    case 422:
      return AUTH_ERRORS.invalidInput;
    case 429:
      return AUTH_ERRORS.rateLimited;
    default:
      return AUTH_ERRORS.generic;
  }
}

export function SignupForm() {
  return (
    <CredentialsForm
      endpoint="/api/auth/signup"
      copy={SIGNUP_PAGE}
      passwordAutoComplete="new-password"
      errorFor={errorFor}
    />
  );
}
