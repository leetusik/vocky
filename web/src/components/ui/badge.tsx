import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

/**
 * Non-interactive label chip. Renders a `<span>` — never a button/link. Retoned
 * to the placeholder palette (the `archive` text color has no token, so it uses
 * the slate text token).
 */
export const badgeVariants = cva(
  "inline-flex items-center rounded-full px-2.5 py-1 text-caption",
  {
    variants: {
      variant: {
        signal: "bg-green text-on-primary",
        softGreen: "bg-green-soft text-green-dark",
        archive: "bg-archive-cream text-slate",
        security: "bg-security-mint text-ink",
        dark: "bg-ink text-green",
      },
    },
    defaultVariants: {
      variant: "signal",
    },
  },
);

export interface BadgeProps
  extends HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}
