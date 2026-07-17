// Barrel for the typed @/content module. Consumers import structured content +
// types from "@/content" — never hardcode copy or anchor ids inline.
export { SECTION_IDS } from "./section-ids";
export type { SectionId } from "./section-ids";

export { SITE } from "./site";
export { NAV_LINKS, SKIP_TO_CONTENT } from "./nav";

export type { Cta, NavLink, SiteMeta } from "./types";

// Auth surface (P4.S2) — public login/signup copy + the status-keyed errors.
export { AUTH_ERRORS, LOGIN_PAGE, SIGNUP_PAGE } from "./auth";
export type { AuthPageCopy } from "./auth";

// Authenticated app shell (P4.S2) — chrome labels + rail nav.
export { APP_NAV, APP_SHELL } from "./app";
export type { AppNavItem } from "./app";

// Tenant dashboard (P4.S3) — usage/trend/projects copy + the create-project form.
export { CREATE_PROJECT_ERRORS, DASHBOARD } from "./dashboard";
export type { StatTileCopy } from "./dashboard";

// Project detail (P4.S4) — per-project usage + credentials, mint/revoke copy.
export {
  MINT_CREDENTIAL_ERRORS,
  PROJECT,
  REVOKE_CREDENTIAL_ERRORS,
} from "./project";

// Feedback (P4.S5) — the cross-project list/search + one record's detail.
export { FEEDBACK } from "./feedback";

// Net-new framework states (P9.S5) — loading / error / not-found / global-error.
export { STATES } from "./states";

// Public landing (P9.S6) — the signed-out `/` marketing surface's copy-as-data.
export { LANDING } from "./landing";
