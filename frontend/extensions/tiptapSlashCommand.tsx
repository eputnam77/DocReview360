// slash-command.ts
import { Extension } from '@tiptap/core';
import Suggestion from '@tiptap/suggestion';

export default Extension.create({
  name: 'slash-command',
  addOptions() {
    return {
      suggestion: {
        char: '/',
        startOfLine: true,
        command: ({ editor, range, props }: { editor: any; range: any; props: any }) => {
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
