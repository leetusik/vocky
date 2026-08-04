import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

/**
 * Small mono tag/pill. Renders a `<span>`. `default` is the neutral tag used for
 * feedback-detail tags (replacing the bespoke `rounded-full` span); `filter` is
 * the active-filter pill (mint border, soft-green fill). When `removable`, a
 * trailing ✕ `<button aria-label>` fires `onRemove` — pass it from a client
 * component (the primitive itself stays domain-free, like `Button`).
 */
export const chipVariants = cva(
  "inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5 font-mono text-caption",
  {
    variants: {
      variant: {
        default: "border-hairline bg-surface text-slate",
        filter: "border-mint bg-green-soft text-green-dark",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface ChipProps
  extends
    Omit<HTMLAttributes<HTMLSpanElement>, "onRemove">,
    VariantProps<typeof chipVariants> {
  /** Render a trailing ✕ remove button. */
  removable?: boolean;
  /** Fired when the remove button is clicked (parent must be a client component). */
  onRemove?: () => void;
  /** Accessible label for the remove button. */
  removeLabel?: string;
}

export function Chip({
  className,
  variant,
  removable,
  onRemove,
  removeLabel = "Remove",
  children,
  ...props
}: ChipProps) {
  return (
    <span className={cn(chipVariants({ variant }), className)} {...props}>
      {children}
      {removable && (
        <button
          type="button"
          aria-label={removeLabel}
          onClick={onRemove}
          className="-mr-0.5 ml-0.5 inline-flex size-3.5 items-center justify-center rounded-full leading-none transition-colors hover:bg-black/5 hover:text-ink focus-visible:outline-none"
        >
          <span aria-hidden="true">✕</span>
        </button>
      )}
    </span>
  );
}
