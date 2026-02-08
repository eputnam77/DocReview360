import { diff_match_patch } from 'diff-match-patch';
export function generateDiffHtml(oldHtml, newHtml) {
    const dmp = new diff_match_patch();
    const diff = dmp.diff_main(oldHtml, newHtml);
    dmp.diff_cleanupSemantic(diff);
    return diff
        .map(([op, text]) => {
        switch (op) {
            case diff_match_patch.DIFF_INSERT:
                return `<ins>${text}</ins>`;
            case diff_match_patch.DIFF_DELETE:
                return `<del>${text}</del>`;
            default:
                return text;
        }
    })
        .join('');
}
