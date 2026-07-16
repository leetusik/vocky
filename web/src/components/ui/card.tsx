import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

/**
 * Surface card. Renders a `<div>`; children-only — the caller supplies the inner
 * heading/body structure. Shadow rgba + the one-off `archive` border are retoned
 * to the placeholder palette (slate/indigo).
 */
export const cardVariants = cva("", {
  variants: {
    variant: {
      base: "rounded-lg border border-hairline bg-canvas p-6",
      feature:
        "rounded-xl border border-hairline bg-canvas p-7 shadow-[0_12px_32px_-18px_rgba(15,23,42,0.16)]",
      featureMuted: "rounded-xl border border-hairline-soft bg-surface p-6",
      dark: "rounded-xl border border-hairline-dark bg-forest p-8 text-on-dark",
      archive: "rounded-xl border border-[#e2e8f0] bg-surface-archive p-8",
      security: "rounded-xl border border-hairline bg-surface-security p-8",
      pricing:
        "rounded-xl border border-hairline bg-canvas p-8 shadow-[0_14px_38px_-22px_rgba(15,23,42,0.18)]",
      pricingFeatured:
        "rounded-xl border border-[rgba(79,70,229,0.55)] bg-canvas p-8 shadow-[0_26px_60px_-22px_rgba(79,70,229,0.40)]",
    },
  },
  defaultVariants: {
    variant: "base",
  },
});

export interface CardProps
  extends HTMLAttributes<HTMLDivElement>, VariantProps<typeof cardVariants> {}

export function Card({ className, variant, ...props }: CardProps) {
  return (
    <div className={cn(cardVariants({ variant }), className)} {...props} />
  );
}
