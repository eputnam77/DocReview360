// slash-command.ts
import { Extension, mergeAttributes } from '@tiptap/core';
import Suggestion from '@tiptap/suggestion';

export interface SlashCommandOptions {
  suggestion: Parameters<typeof Suggestion>[0];
}

export default Extension.create<SlashCommandOptions>({
  name: 'slash-command',
  addOptions() {
    return {
      suggestion: {
        char: '/',
        startOfLine: true,
        command: ({ editor, range, props }) => {
          // default: insert text
          editor
            .chain()
            .focus()
            .deleteRange(range)
            .insertContent(props.label)
            .run();
        },
        items: () => [],
      },
    };
  },
  addProseMirrorPlugins() {
    return [
      Suggestion({
        editor: this.editor,
        ...this.options.suggestion,
      }),
    ];
  },
});
