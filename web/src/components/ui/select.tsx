import { cva, type VariantProps } from "class-variance-authority";
import type { ReactNode, SelectHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

import { inputVariants } from "./field";

/**
 * Styled native `<select>` — deliberately a real `<select>` (a11y: native
 * keyboard, mobile pickers, screen-reader semantics all for free). It reuses the
 * Input control base (so filter selects match the form fields), hides the native
 * chevron with `appearance-none`, and paints its own: a rotated bordered square
 * absolutely positioned inside the wrapper `<span>`. `className` targets the
 * `<select>`; `wrapperClassName` the positioning wrapper. Replaces the two raw
 * `<select className={inputVariants()}>` in the feedback filter bar (S4).
 */
export const selectVariants = cva(cn(inputVariants(), "appearance-none pr-9"));

export interface SelectProps
  extends
    SelectHTMLAttributes<HTMLSelectElement>,
    VariantProps<typeof selectVariants> {
  /** `<option>`s (and optionally `<optgroup>`s). */
  children: ReactNode;
  /** Extra classes on the positioning wrapper `<span>`. */
  wrapperClassName?: string;
}

export function Select({
  className,
  wrapperClassName,
  children,
  ...props
}: SelectProps) {
  return (
    <span className={cn("relative block", wrapperClassName)}>
      <select className={cn(selectVariants(), className)} {...props}>
        {children}
      </select>
      <span
        aria-hidden="true"
        className="pointer-events-none absolute top-1/2 right-3 size-2 -translate-y-2/3 rotate-45 border-r border-b border-steel"
      />
    </span>
  );
}
