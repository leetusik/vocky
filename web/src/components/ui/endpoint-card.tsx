import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * Dark code/endpoint panel. Renders its content as real, selectable text in a
 * `<pre>` (a11y: code is HTML text, not an image). The optional `label` shows as
 * a small dark chip above the code. Pass JSON/code as `children`. Token-styled to
 * the vocky forest panel (soft-forest border, brighter data-teal label text).
 */
export interface EndpointCardProps extends Omit<
  HTMLAttributes<HTMLDivElement>,
  "children"
> {
  /** Small dark chip above the code panel (e.g. a method/endpoint name). */
  label?: ReactNode;
  /** Code/JSON to render verbatim inside the `<pre>`. */
  children: ReactNode;
}

export function EndpointCard({
  className,
  label,
  children,
  ...props
}: EndpointCardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border border-forest-soft bg-forest-mid p-6 text-on-dark",
        className,
      )}
      {...props}
    >
      {label != null && (
        <span className="mb-3 inline-flex items-center rounded-full bg-ink px-2.5 py-1 font-mono text-caption text-teal">
          {label}
        </span>
      )}
      <pre className="overflow-x-auto font-mono text-code-md">{children}</pre>
    </div>
  );
}
