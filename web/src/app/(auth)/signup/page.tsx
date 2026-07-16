import type { Metadata } from "next";

import { SIGNUP_PAGE } from "@/content";
import { redirectIfAuthenticated } from "@/lib/auth-guards";

import { AuthCard } from "../auth-card";
import { SignupForm } from "./signup-form";

// P4.S2 — /signup. Same shape as /login: bounce an already-signed-in visitor,
// otherwise render the card + the client form island. Dynamic (reads the cookie).
export const metadata: Metadata = { title: SIGNUP_PAGE.title };

export default async function SignupPage() {
  await redirectIfAuthenticated();

  return (
    <AuthCard copy={SIGNUP_PAGE}>
      <SignupForm />
    </AuthCard>
  );
}
