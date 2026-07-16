import { cva, type VariantProps } from "class-variance-authority";
import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

/**
 * Button styling, token-driven via CVA so anchor CTAs can reuse the exact same
 * classes. Anchors render `<a className={cn(buttonVariants({ variant }))}>` — no
 * @radix-ui/react-slot / asChild dependency.
 *
 * The base pairs `focus-visible:outline-none` with the global accent-deep
 * `:focus-visible` ring from globals.css: the ring still shows; we only suppress
 * the browser default so the accent outline is the single visible focus state.
 * The `link` variant strips the pill shape / min-height. (Shadow rgba values are
 * retoned to the placeholder indigo accent — see globals.css.)
 */
export const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-full font-en text-button-md font-bold transition focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        primary:
          "bg-green text-on-primary shadow-[0_12px_30px_-8px_rgba(79,70,229,0.5)] hover:-translate-y-0.5 hover:bg-green-deep hover:shadow-[0_18px_38px_-10px_rgba(79,70,229,0.62)]",
        secondary:
          "border border-hairline-strong bg-canvas font-semibold text-ink hover:bg-surface",
        secondaryOnDark:
          "border border-hairline-dark bg-transparent text-on-dark hover:bg-white/10",
        link: "h-auto min-h-0 rounded-none bg-transparent p-0 text-body-md-medium text-green-dark hover:underline",
      },
      size: {
        default: "min-h-11 px-[22px] py-[11px]",
        lg: "min-h-[52px] px-7",
        sm: "min-h-10 px-[18px]",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends
    ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

/**
 * Real `<button type="button">` (a11y: never a div for an action). For anchor
 * CTAs use the exported `buttonVariants` on an `<a>` instead.
 */
export function Button({
  className,
  variant,
  size,
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  );
}
