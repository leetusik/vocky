import { clsx, type ClassValue } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

/**
 * The design system defines a custom font-size scale via Tailwind v4 `@theme`
 * (`text-heading-2`, `text-button-md`, `text-body-md-medium`, … — see
 * `globals.css`). tailwind-merge has no way to know these `text-*` utilities are
 * font SIZES, so by default it lumps them with the `text-<color>` group and, when
 * a size and a color appear in the same `cn()` call, it drops the size as a
 * "conflict" (last-wins) — silently stripping e.g. `text-heading-2` next to
 * `text-ink`. Plain-string classNames are never merged, so only `cn()`-composed
 * elements would break.
 *
 * Registering the scale in the `font-size` group makes size + color coexist, so
 * `cn()` behaves like a plain string for these tokens. Keep this list in sync with
 * the `--text-*` tokens in `globals.css` (token NAMES are shared with hi2vi_web,
 * so this list is unchanged even though the palette values are placeholders).
 */
const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      "font-size": [
        {
          text: [
            "hero-display",
            "display-lg",
            "heading-1",
            "heading-2",
            "heading-3",
            "heading-4",
            "body-lg",
            "body-md",
            "body-md-medium",
            "body-sm",
            "caption",
            "micro",
            "button-md",
            "code-md",
          ],
        },
      ],
    },
  },
});

/**
 * Merge class names: `clsx` resolves conditionals, `twMerge` de-duplicates
 * conflicting Tailwind utilities (last wins). The standard shadcn/ui helper,
 * extended above so our custom font-size scale isn't mistaken for text colors.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
