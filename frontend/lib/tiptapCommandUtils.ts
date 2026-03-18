type ChainLike = {
  focus?: () => ChainLike;
  run?: () => boolean;
  [key: string]: unknown;
};

type EditorLike = {
  chain?: () => ChainLike;
  can?: () => { chain?: () => ChainLike };
};

function resolveCommandChain(
  editor: EditorLike | null | undefined,
  commandName: string,
  useCanChain: boolean,
): (() => boolean) | null {
  if (!editor) {
    return null;
  }

  const chainFactory = useCanChain ? editor.can?.()?.chain : editor.chain;
  if (typeof chainFactory !== "function") {
    return null;
  }

  const baseChain = chainFactory();
  const focusedChain =
    typeof baseChain.focus === "function" ? baseChain.focus() : baseChain;
  const command = focusedChain[commandName];

  if (typeof command !== "function") {
    return null;
  }

  const commandChain = command.call(focusedChain);
  if (!commandChain || typeof commandChain.run !== "function") {
    return null;
  }

  return () => commandChain.run();
}

export function canRunEditorCommand(
  editor: EditorLike | null | undefined,
  commandName: string,
): boolean {
  const runner = resolveCommandChain(editor, commandName, true);
  return runner ? runner() : false;
}

export function runEditorCommand(
  editor: EditorLike | null | undefined,
  commandName: string,
): boolean {
  const runner = resolveCommandChain(editor, commandName, false);
  return runner ? runner() : false;
}
