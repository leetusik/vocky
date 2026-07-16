"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { APP_NAV, APP_SHELL } from "@/content";
import { cn } from "@/lib/utils";

/**
 * The shell's rail navigation (P4.S2). A client island only because the active
 * item is derived from `usePathname()`; the rest of the shell stays server-rendered.
 *
 * Items flagged `soon` (a route announced before it exists) render as muted,
 * non-interactive text with a "Soon" tag rather than links that would 404. No
 * item sets it today — S5 shipped /feedback, the last one — but the affordance
 * stays for future surfaces.
 * Below 900px the rail collapses to a horizontal strip above the main column.
 */
export function RailNav() {
  const pathname = usePathname();

  return (
    <nav
      aria-label={APP_SHELL.navLabel}
      className="border-b border-hairline bg-surface px-3 py-4 min-[900px]:border-r min-[900px]:border-b-0"
    >
      <ul className="flex gap-1 min-[900px]:flex-col">
        {APP_NAV.map((item) => (
          <li key={item.href}>
            {item.soon ? (
              <span
                aria-disabled="true"
                className="flex items-center justify-between gap-2 rounded-md px-3 py-2 text-body-sm text-muted"
              >
                {item.label}
                <span className="rounded-full border border-hairline bg-canvas px-2 py-0.5 font-mono text-micro text-steel">
                  {APP_SHELL.soonTag}
                </span>
              </span>
            ) : (
              <Link
                href={item.href}
                aria-current={
                  pathname === item.href || pathname.startsWith(`${item.href}/`)
                    ? "page"
                    : undefined
                }
                className={cn(
                  "block rounded-md px-3 py-2 text-body-sm transition-colors",
                  pathname === item.href || pathname.startsWith(`${item.href}/`)
                    ? "bg-surface-green font-medium text-green-dark"
                    : "text-slate hover:bg-surface-soft hover:text-ink",
                )}
              >
                {item.label}
              </Link>
            )}
          </li>
        ))}
      </ul>
    </nav>
  );
}
