"use client";

import { useEffect, useRef } from "react";

import { cn } from "@/lib/utils";

/**
 * Reveal — a progressive-enhancement scroll-reveal wrapper.
 *
 * Server-renders its children with NO hidden state (no `data-reveal` in the SSR
 * markup), so no-JS users and reduced-motion users always see the content
 * immediately (the static page is the guaranteed baseline — nothing is ever
 * stuck hidden). On mount, ONLY when `prefers-reduced-motion` is not set, it sets
 * the `data-reveal` hook IMPERATIVELY on the node (the hidden start-state CSS
 * lives under a `prefers-reduced-motion: no-preference` block in globals.css, so
 * it only applies once JS+motion have added the hook) and starts an
 * IntersectionObserver; on the first intersection it adds `is-visible` (which
 * transitions opacity/translateY) and unobserves — a one-shot reveal.
 *
 * If the element is already in view at mount, the observer fires immediately.
 * Reduced-motion → the hook is never set → the element renders plainly visible.
 */
export interface RevealProps {
  children: React.ReactNode;
  /** Extra classes on the wrapper. */
  className?: string;
  /** Wrapper element. Defaults to `div`. */
  as?: "div" | "section";
}

export function Reveal({ children, className, as: Tag = "div" }: RevealProps) {
  const ref = useRef<HTMLElement>(null);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    // Respect the global reduced-motion contract: do nothing, leave visible.
    if (
      typeof window === "undefined" ||
      !window.matchMedia ||
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      return;
    }

    // Arm the hidden start-state only now that JS+motion are confirmed.
    node.setAttribute("data-reveal", "");

    if (typeof IntersectionObserver === "undefined") {
      // No observer support: reveal immediately so nothing stays hidden.
      node.classList.add("is-visible");
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        }
      },
      { threshold: 0.15, rootMargin: "0px 0px -10% 0px" },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <Tag
      ref={ref as React.Ref<HTMLDivElement & HTMLElement>}
      className={cn(className)}
    >
      {children}
    </Tag>
  );
}
