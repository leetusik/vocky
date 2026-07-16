// Auth-surface copy (P4.S2) — the public login + signup pages. Copy-as-data per
// the S1 convention: pages never hardcode strings inline.
//
// The error copy is keyed by the BFF's STATUS CODE, never by vocky's `detail`
// text (which the BFF deliberately does not forward). Note `invalidCredentials`
// is intentionally one message for both an unknown email and a wrong password —
// vocky answers an identical generic 401 for both so accounts cannot be
// enumerated, and this copy preserves that property in the UI.

export interface AuthPageCopy {
  /** Document <title> (the SITE template appends " · vocky"). */
  title: string;
  lead: string;
  sub: string;
  emailLabel: string;
  emailPlaceholder: string;
  passwordLabel: string;
  passwordPlaceholder: string;
  /** Hint shown under the password field (signup states vocky's 8-char minimum). */
  passwordHint?: string;
  submitLabel: string;
  submitPendingLabel: string;
  /** Cross-link to the other auth page, e.g. "No account yet? Create one". */
  altPrompt: string;
  altLinkLabel: string;
  altHref: string;
}

/** Status-keyed error copy shared by both forms. */
export const AUTH_ERRORS = {
  /** 401 — unknown email OR wrong password, deliberately indistinguishable. */
  invalidCredentials: "Incorrect email or password.",
  /** 409 — signup against an email that already exists. */
  emailTaken: "An account with this email already exists. Sign in instead.",
  /** 400 / 422 — vocky-side or shape validation. */
  invalidInput:
    "Enter a valid email address and a password of at least 8 characters.",
  /** 429 — the per-IP throttle. */
  rateLimited: "Too many attempts. Please wait a few minutes and try again.",
  /** 5xx / network. */
  generic: "Something went wrong. Please try again.",
} as const;

export const LOGIN_PAGE: AuthPageCopy = {
  title: "Sign in",
  lead: "Sign in",
  sub: "Access your workspace, projects, and feedback.",
  emailLabel: "Email",
  emailPlaceholder: "you@example.com",
  passwordLabel: "Password",
  passwordPlaceholder: "Your password",
  submitLabel: "Sign in",
  submitPendingLabel: "Signing in…",
  altPrompt: "No account yet?",
  altLinkLabel: "Create one",
  altHref: "/signup",
};

export const SIGNUP_PAGE: AuthPageCopy = {
  title: "Create account",
  lead: "Create your account",
  sub: "A workspace is created for you automatically.",
  emailLabel: "Email",
  emailPlaceholder: "you@example.com",
  passwordLabel: "Password",
  passwordPlaceholder: "At least 8 characters",
  passwordHint: "Use at least 8 characters.",
  submitLabel: "Create account",
  submitPendingLabel: "Creating account…",
  altPrompt: "Already have an account?",
  altLinkLabel: "Sign in",
  altHref: "/login",
};
