import { Mark, Wordmark } from "@/components/brand";
import { APP_SHELL } from "@/content";
import type { VockyIdentity } from "@/lib/vocky/types";

import { LogoutButton } from "./logout-button";
import { RailNav } from "./rail-nav";

/**
 * The authenticated app shell (P4.S2; restyled to the vocky system in P9.S3) —
 * the chrome S3–S5 render inside. A sticky topbar (brand mark + wordmark ·
 * org/user · `flex-1` spacer · logout) over a `[rail | main]` grid that
 * collapses to a single column below the `app` breakpoint (900px).
 *
 * Unlike hi2vi's one-big-client-island console, this is a SERVER component: the
 * identity is server-fetched by the `(app)` layout and rendered here, so a live
 * session token's surroundings never cross a client boundary. Only the two
 * genuinely-interactive bits — the logout button and the pathname-aware rail —
 * are client islands.
 */
export function AppShell({
  identity,
  children,
}: {
  identity: VockyIdentity;
  children: React.ReactNode;
}) {
  const tenantName = identity.tenant?.name ?? APP_SHELL.noTenant;

  return (
    <>
      <header className="sticky top-0 z-20 flex items-center gap-3.5 border-b border-hairline bg-canvas px-6 py-3">
        <span className="flex items-center gap-2">
          <Mark size={32} />
          <Wordmark />
        </span>
        <span className="h-5 w-px bg-hairline" />
        <span className="hidden text-body-sm text-steel sm:inline">
          {APP_SHELL.orgLabel}{" "}
          <b className="font-semibold text-charcoal">{tenantName}</b>
        </span>
        <span className="flex-1" />
        <span className="hidden text-caption text-steel md:inline">
          {identity.user.email}
        </span>
        <LogoutButton />
      </header>

      <div className="grid min-h-[calc(100dvh-57px)] grid-cols-1 app:grid-cols-[248px_minmax(0,1fr)]">
        <RailNav />
        <main id="main-content" className="relative px-4 pt-5 pb-10 app:px-6">
          {children}
        </main>
      </div>
    </>
  );
}
