/**
 * P11.S6 — clipboard decision logic, deliberately DOM-free.
 *
 * The web test suite is Node-environment vitest with no jsdom and no RTL
 * (`web/vitest.config.ts`), so anything touching `document`, `navigator` or a
 * React tree is structurally untestable here. `attemptCopy` is therefore the pure
 * seam: the caller supplies BOTH sides of the effect — how to read the text and
 * how to write it — and this module only decides which state the attempt lands in.
 *
 * Reading is a CALLBACK, not a string, because of round 02's locked clipboard
 * rule (build-prompt §3.1): the clipboard gets the DOM node's `textContent`, never
 * a separately-typed string. The read can therefore only happen at click time, and
 * it can itself fail — which is why it lives inside the same `try`.
 */

/** The three states a copy affordance can be in (build-prompt §7). */
export type CopyState = "idle" | "copied" | "failed";

/**
 * Attempt a copy and report the state it lands in.
 *
 * `"copied"` when the write resolves; `"failed"` when either the read or the write
 * throws — a denied clipboard, an insecure origin (no `navigator.clipboard` at
 * all), or a command node that is gone. The `catch` is VALUELESS on purpose: the
 * text being copied is never logged (same rule as `show-once-key.tsx`, where the
 * value is a plaintext `vk_` key).
 */
export async function attemptCopy(
  getText: () => string,
  write: (text: string) => Promise<void>,
): Promise<CopyState> {
  try {
    await write(getText());
    return "copied";
  } catch {
    return "failed";
  }
}
