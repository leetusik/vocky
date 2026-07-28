import { useSyncExternalStore } from "react";

/**
 * P11.S6 — "has this component hydrated yet?", for mount-gated client islands.
 *
 * Round 02 locks a no-JS floor (build-prompt §8): a visitor without JavaScript
 * must see NO copy button at all, never a present-but-inert one. The way to get
 * that is to render the control only once the client has taken over — the server
 * HTML is the guaranteed baseline and JS only ever ADDS to it, the same contract
 * `ui/reveal.tsx` states for its reveal hook.
 *
 * Implemented with `useSyncExternalStore` rather than the usual
 * `useState(false)` + `useEffect(() => setMounted(true))`: React renders (and
 * hydrates) with `getServerSnapshot` → `false`, then re-renders with the client
 * snapshot → `true` once hydration is done. Same observable behaviour, no
 * hydration mismatch, and no setState inside an effect (which the React Compiler
 * lint rule `react-hooks/set-state-in-effect` rejects outright — this repo's
 * `pnpm lint` fails on the useEffect spelling).
 *
 * The store never emits, so `subscribe` is a module-level no-op: it must be a
 * STABLE reference or React resubscribes on every render.
 */
const subscribe = () => () => {};
const getSnapshot = () => true;
const getServerSnapshot = () => false;

export function useIsHydrated(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
