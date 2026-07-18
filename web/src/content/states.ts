// Copy for the four net-new framework states (P9.S5, build-prompt §6): the app
// shell's loading skeleton, the error boundary, the 404 not-found, and the
// root-layout global-error fallback. Plain data (no `server-only`) so the client
// boundary components (`error.tsx`, `global-error.tsx`) can import it too.
//
// Every string here is VERBATIM from build-prompt §6 — the 404 subcopy in
// particular is a locked floor (404-never-403: it never confirms whether a
// resource exists), so it must not be paraphrased.

export const STATES = {
  /**
   * The loading skeleton has no visible copy (it mirrors the real layout in
   * placeholder blocks); this is the screen-reader-only status for the busy
   * region so assistive tech announces the wait.
   */
  loading: {
    label: "Loading",
  },
  /** Error boundary (`error.tsx`). Never surfaces `error.message`. */
  error: {
    title: "Something went wrong",
    body: "We couldn't load this page. Please try again.",
    retry: "Try again",
  },
  /**
   * Not-found (`not-found.tsx` + `(app)/not-found.tsx`). The body is the locked
   * 404-never-403 line — it never confirms a resource exists. Two back-links:
   * `back` sends the in-app 404 to the dashboard; `backHome` sends the public
   * (root) 404 to the landing `/`, since an unmatched public URL has no session.
   */
  notFound: {
    code: "404",
    title: "This page doesn't exist",
    body: "The page you asked for isn't here — or isn't yours to see.",
    back: "Back to dashboard",
    backHome: "Back to home",
  },
  /**
   * Global-error (`global-error.tsx`) — the minimal full-page fallback shown when
   * the root layout itself crashes. Mirrors the error boundary's wording.
   */
  globalError: {
    title: "Something went wrong",
    retry: "Try again",
  },
} as const;
