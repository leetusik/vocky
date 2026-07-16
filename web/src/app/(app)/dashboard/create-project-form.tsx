"use client";

import { useActionState, useEffect, useId, useRef } from "react";

import { Button, FieldError, Input, Label } from "@/components/ui";
import { DASHBOARD } from "@/content";
import { createProjectAction, type CreateProjectState } from "./actions";

/**
 * The form's initial state lives HERE, not in `actions.ts`: that file is
 * `"use server"`, where every export is registered as a callable server action,
 * so exporting a plain object from it makes Next throw "A 'use server' file can
 * only export async functions" at request time. A type-only import is safe
 * (erased at compile time).
 */
const INITIAL_STATE: CreateProjectState = { error: null };

/**
 * P4.S3 — the create-project client island.
 *
 * The ONLY client component on the dashboard: everything else (usage tiles,
 * trend, projects table) is server-rendered, so no vocky data crosses a client
 * boundary. This island exists purely for the pending/error affordances.
 *
 * `useActionState` posts to the server action, which revalidates `/dashboard` on
 * success — the new row and the refreshed usage arrive with the server re-render;
 * there is no client-side list state to keep in sync. The `<form action={...}>`
 * also means submitting works before hydration.
 */
export function CreateProjectForm() {
  const [state, formAction, pending] = useActionState(
    createProjectAction,
    INITIAL_STATE,
  );

  const copy = DASHBOARD.createProject;
  const baseId = useId();
  const nameId = `${baseId}-name`;
  const errorId = `${baseId}-error`;
  const formRef = useRef<HTMLFormElement>(null);

  // Clear the field after a successful create. Keyed off `ok` (bumped per
  // success) rather than `error === null`, which is also the INITIAL state and
  // would reset the form on first render.
  useEffect(() => {
    if (state.ok) formRef.current?.reset();
  }, [state.ok]);

  const invalid = state.error !== null;

  return (
    <form ref={formRef} action={formAction} className="space-y-2">
      <Label htmlFor={nameId}>{copy.nameLabel}</Label>
      <div className="flex flex-wrap items-start gap-3">
        <Input
          id={nameId}
          name="name"
          type="text"
          placeholder={copy.namePlaceholder}
          maxLength={200}
          required
          disabled={pending}
          aria-invalid={invalid}
          aria-describedby={invalid ? errorId : undefined}
          className="min-w-0 flex-1"
        />
        <Button type="submit" variant="primary" disabled={pending}>
          {pending ? copy.submitPendingLabel : copy.submitLabel}
        </Button>
      </div>
      <FieldError id={errorId}>{state.error ?? undefined}</FieldError>
    </form>
  );
}
