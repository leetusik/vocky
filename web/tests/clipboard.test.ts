import { describe, expect, it } from "vitest";

import { attemptCopy } from "@/lib/clipboard";

// P11.S6 — round 02's copy affordances hang their whole state machine off this
// one decision: `copied` reverts after 2s, `failed` PERSISTS and instead selects
// the text for a manual ⌘C. Mistaking a failure for a success would therefore
// flash "✓ Copied" and clear itself while the clipboard still held something
// else. The Node-env suite has no jsdom, so the DOM read and `navigator.clipboard`
// are injected — which also pins the rule that the READ can fail too (the text
// comes from a DOM node's `textContent`, never a separately-typed string).

describe("attemptCopy", () => {
  it("reports copied when the clipboard write resolves", async () => {
    const written: string[] = [];
    await expect(
      attemptCopy(
        () => "curl -fsSL https://vocky.hi2vi.com/install.sh | bash",
        async (text) => {
          written.push(text);
        },
      ),
    ).resolves.toBe("copied");
    expect(written).toEqual([
      "curl -fsSL https://vocky.hi2vi.com/install.sh | bash",
    ]);
  });

  it("reports failed when the write rejects (denied clipboard, insecure origin)", async () => {
    await expect(
      attemptCopy(
        () => "vocky capture",
        () => Promise.reject(new Error("NotAllowedError")),
      ),
    ).resolves.toBe("failed");
  });

  it("reports failed when reading the command node throws", async () => {
    let wrote = false;
    await expect(
      attemptCopy(
        () => {
          throw new Error("no command node");
        },
        async () => {
          wrote = true;
        },
      ),
    ).resolves.toBe("failed");
    expect(wrote).toBe(false);
  });
});
