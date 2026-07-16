import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes } from "react";

import type { SectionId } from "@/content";
import { cn } from "@/lib/utils";

import { Reveal } from "./reveal";

/**
 * Full-bleed tonal band that hosts a page section. When `id` is set the band
 * carries a baked `scroll-mt-24` so in-page anchor jumps clear a sticky header
 * (the `id` prop is typed `SectionId`, so callers never hardcode a `#...`). The
 * inner container (on by default) centers content at `max-w-page` with
 * responsive gutters; pass `container={false}` for a section that owns its width.
 */
export const sectionVariants = cva("py-section md:py-section-lg", {
  variants: {
    tone: {
      default: "bg-canvas text-ink",
      surface: "bg-surface text-ink",
      surfaceSoft: "bg-surface-soft text-ink",
      band: "bg-surface-band text-ink",
      security: "bg-surface-security text-ink",
      archive: "bg-surface-archive text-ink",
      ink: "bg-ink text-on-dark",
      forest: "bg-forest text-on-dark",
    },
  },
  defaultVariants: {
    tone: "default",
  },
});

export interface SectionProps
  extends
    Omit<HTMLAttributes<HTMLElement>, "id">,
    VariantProps<typeof sectionVariants> {
  /** In-page anchor target. Typed to SECTION_IDS so anchors never hardcode `#...`. */
  id?: SectionId;
  /** Semantic element for the band. Defaults to `section`. */
  as?: "section" | "div";
  /** Render the centered inner container. Defaults to true. */
  container?: boolean;
  /** Extra classes for the inner container (only when `container`). */
  containerClassName?: string;
  /**
   * Opt-in scroll-reveal. Wraps the inner container's CONTENT in `<Reveal>` (the
   * tonal band itself stays static), so below-the-fold sections fade/rise in on
   * first scroll. Progressive enhancement: no-JS and reduced-motion users see
   * the content immediately. Only valid when `container` is true.
   */
  reveal?: boolean;
}

export function Section({
  className,
  containerClassName,
  tone,
  id,
  as: Tag = "section",
  container = true,
  reveal = false,
  children,
  ...props
}: SectionProps) {
  return (
    <Tag
      id={id}
      className={cn(sectionVariants({ tone }), id && "scroll-mt-24", className)}
      {...props}
    >
      {container ? (
        <div
          className={cn("mx-auto max-w-page px-5 md:px-14", containerClassName)}
        >
          {reveal ? <Reveal>{children}</Reveal> : children}
        </div>
      ) : (
        children
      )}
    </Tag>
  );
}
