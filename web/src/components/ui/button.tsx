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
 * The `link` variant strips the pill shape / min-height. Buttons are `rounded-md`
 * (compact vocky radius) and `font-en` renders in Pretendard; `primary`'s shadow
 * uses the deep-emerald signature rgba (`0C7A52`, see globals.css §2.5).
 */
export const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-md font-en text-button-md font-semibold transition focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        primary:
          "bg-green text-on-primary shadow-[0_10px_24px_-12px_rgba(12,122,82,0.5)] hover:-translate-y-0.5 hover:bg-green-deep hover:shadow-[0_14px_30px_-12px_rgba(12,122,82,0.62)]",
        secondary:
          "border border-hairline-strong bg-canvas text-ink hover:bg-surface",
        ghost:
          "bg-transparent text-steel hover:bg-surface-soft hover:text-charcoal",
        destructive: "bg-danger text-on-dark hover:bg-danger-deep",
        destructiveOutline:
          "border border-hairline-danger bg-canvas text-danger-deep hover:bg-surface-danger",
        dark: "border border-hairline-dark bg-transparent text-on-dark hover:bg-white/10",
        link: "h-auto min-h-0 rounded-none bg-transparent p-0 text-body-md-medium text-green-dark hover:underline",
      },
      size: {
        default: "min-h-10 px-[18px] py-2",
        sm: "min-h-9 px-3.5",
        lg: "min-h-12 px-7 text-[15px]",
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
