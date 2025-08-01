// Simple lint extension placeholder
import { Extension } from "@tiptap/core";

export default Extension.create({
  name: "lint",
  addGlobalAttributes() {
    return [
      {
        types: ["paragraph"],
        attributes: {
          "data-lint": {
            default: null,
            parseHTML: () => null,
            renderHTML: () => ({}),
          },
        },
      },
    ];
  },
});
