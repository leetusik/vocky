// Barrel for the typed @/content module. Consumers import structured content +
// types from "@/content" — never hardcode copy or anchor ids inline. Feature
// copy (dashboard / project / feedback surfaces) is added by later slices.
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
