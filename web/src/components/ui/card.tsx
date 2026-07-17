import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

/**
 * Surface card. Renders a `<div>`; children-only — the caller supplies the inner
 * heading/body structure. Compact vocky density (`p-5` base); shadow rgba use the
 * ink signature (`0E1A16` → `rgba(14,26,22,…)`) and `pricingFeatured` the emerald
 * green border + glow (see globals.css §2.5). The placeholder-only `security` /
 * `archive` variants are dropped — the credential "Revoked" case moved to the
 * `revoked` Badge.
 */
export const cardVariants = cva("", {
  variants: {
    variant: {
      base: "rounded-lg border border-hairline bg-canvas p-5",
      feature:
        "rounded-xl border border-hairline bg-canvas p-6 shadow-[0_12px_32px_-18px_rgba(14,26,22,0.16)]",
      featureMuted: "rounded-xl border border-hairline-soft bg-surface p-5",
      dark: "rounded-xl border border-hairline-dark bg-forest p-7 text-on-dark",
      pricing:
        "rounded-xl border border-hairline bg-canvas p-7 shadow-[0_14px_38px_-22px_rgba(14,26,22,0.18)]",
      pricingFeatured:
        "rounded-xl border-2 border-green bg-canvas p-7 shadow-[0_24px_56px_-28px_rgba(12,122,82,0.34)]",
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
