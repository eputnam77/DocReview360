import { describe, it, expect } from 'vitest';
import { generateDiffHtml } from '../utils/diff';
describe('generateDiffHtml', () => {
    it('returns original HTML when inputs are identical', () => {
        const html = '<p>Hello</p>';
        expect(generateDiffHtml(html, html)).toBe(html);
    });
    it('wraps insertions and deletions', () => {
        const added = generateDiffHtml('<p>Hello</p>', '<p>Hello world</p>');
        expect(added).toContain('<ins> world</ins>');
        const removed = generateDiffHtml('<p>Hello world</p>', '<p>Hello</p>');
        expect(removed).toContain('<del> world</del>');
    });
});
