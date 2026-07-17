import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

/**
 * Non-interactive status/label chip. Renders a `<span>` — never a button/link.
 * The overloaded placeholder `archive` variant is split into semantic vocky
 * variants: rating (`liked`/`disliked`/`unrated`) and credential status
 * (`active`/`revoked`), plus a filled `accent`. Optionally renders a leading dot
 * (the base `gap-1.5` spaces it) so stat tiles / feedback can opt in — the dot's
 * color is derived from the variant.
 */
export const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-caption font-semibold",
  {
    variants: {
      variant: {
        liked: "bg-green-soft text-green-dark",
        disliked: "bg-surface-danger text-danger-deep",
        unrated: "bg-surface-soft text-steel",
        active: "bg-green-soft text-green-dark",
        revoked: "bg-surface-soft text-steel",
        accent: "bg-green text-on-primary",
      },
    },
    defaultVariants: {
      variant: "unrated",
    },
  },
);

type BadgeVariant = NonNullable<VariantProps<typeof badgeVariants>["variant"]>;

/** Leading-dot color per variant (semantic swatch for the optional dot). */
const dotColor: Record<BadgeVariant, string> = {
  liked: "bg-green",
  disliked: "bg-danger",
  unrated: "bg-muted",
  active: "bg-green",
  revoked: "bg-muted",
  accent: "bg-on-primary",
};

export interface BadgeProps
  extends HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {
  /** Prepend a small leading dot colored to the variant. */
  dot?: boolean;
}

export function Badge({
  className,
  variant,
  dot,
  children,
  ...props
}: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props}>
      {dot && (
        <span
          aria-hidden="true"
          className={cn(
            "inline-block size-1.5 rounded-full",
            dotColor[variant ?? "unrated"],
          )}
        />
      )}
      {children}
    </span>
  );
}
