declare module "diff-match-patch" {
  export type Diff = [number, string];

  export class diff_match_patch {
    static DIFF_DELETE: -1;
    static DIFF_INSERT: 1;
    static DIFF_EQUAL: 0;

    diff_main(text1: string, text2: string): Diff[];
    diff_cleanupSemantic(diffs: Diff[]): void;
  }
}
