import { describe, expect, it, vi } from "vitest";

import { canRunEditorCommand, runEditorCommand } from "../lib/tiptapCommandUtils";

describe("tiptapCommandUtils", () => {
  it("returns false instead of throwing when a command is unavailable", () => {
    const editor = {
      chain: () => ({
        focus: () => ({ run: () => true }),
      }),
      can: () => ({
        chain: () => ({
          focus: () => ({ run: () => true }),
        }),
      }),
    };

    expect(canRunEditorCommand(editor, "indent")).toBe(false);
    expect(runEditorCommand(editor, "indent")).toBe(false);
  });

  it("runs available commands through the focused chain", () => {
    const run = vi.fn(() => true);
    const command = vi.fn(() => ({ run }));
    const focus = vi.fn(() => ({ indent: command }));
    const editor = {
      chain: () => ({ focus }),
      can: () => ({
        chain: () => ({ focus }),
      }),
    };

    expect(canRunEditorCommand(editor, "indent")).toBe(true);
    expect(runEditorCommand(editor, "indent")).toBe(true);
    expect(focus).toHaveBeenCalledTimes(2);
    expect(command).toHaveBeenCalledTimes(2);
    expect(run).toHaveBeenCalledTimes(2);
  });
});
