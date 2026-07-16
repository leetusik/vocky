import type { Metadata } from "next";

import { LOGIN_PAGE } from "@/content";
import { redirectIfAuthenticated } from "@/lib/auth-guards";

import { AuthCard } from "../auth-card";
import { LoginForm } from "./login-form";

// P4.S2 — /login. Server component: an already-signed-in visitor is bounced to the
// dashboard (verified against vocky — see `redirectIfAuthenticated`), everyone else
// gets the card + the client form island. Reading the session cookie makes this
// route dynamic, so it is never prerendered.
export const metadata: Metadata = { title: LOGIN_PAGE.title };

export default async function LoginPage() {
  await redirectIfAuthenticated();

  return (
    <AuthCard copy={LOGIN_PAGE}>
      <LoginForm />
    </AuthCard>
  );
}
