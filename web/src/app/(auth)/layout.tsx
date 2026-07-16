import type { Metadata } from "next";

// P4.S2 — public auth area (login + signup). Deliberately minimal and
// deliberately UNGUARDED: the login page must stay reachable, so the session gate
// lives one level over in the sibling `(app)` group's layout, not here. The
// `(auth)` group is invisible in the URL, so these render at /login and /signup.
//
// `robots: { index: false, follow: false }` keeps the whole auth subtree out of
// search indexes.
export const metadata: Metadata = {
  robots: { index: false, follow: false },
};

export default function AuthLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <div className="flex min-h-dvh flex-col justify-center bg-surface px-5 py-12">
      <main id="main-content">{children}</main>
    </div>
  );
}
