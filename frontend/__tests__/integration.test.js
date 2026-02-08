import { describe, it, expect, vi } from 'vitest';
import { Editor } from '@tiptap/core';
import StarterKit from '@tiptap/starter-kit';
import { TEMPLATES } from '../utils/templates';
describe('template workflow', () => {
    it('loads template, saves revision, and restores it', async () => {
        const revisions = [];
        vi.stubGlobal('fetch', (url, options = {}) => {
            if (typeof url === 'string' && url.startsWith('/templates/')) {
                const id = url.split('/').pop();
                return Promise.resolve({ ok: true, json: () => Promise.resolve({ content: TEMPLATES[id].content }) });
            }
            if (url === '/documents/demo/revisions' && options.method === 'POST') {
                const body = JSON.parse(options.body);
                const rev = { id: String(revisions.length + 1), content: body.content };
                revisions.push(rev);
                return Promise.resolve({ ok: true, json: () => Promise.resolve(rev) });
            }
            if (url === '/documents/demo/revisions') {
                return Promise.resolve({ ok: true, json: () => Promise.resolve(revisions) });
            }
            if (typeof url === 'string' && url.startsWith('/documents/demo/revisions/')) {
                const id = url.split('/').pop();
                const rev = revisions.find(r => r.id === id);
                return Promise.resolve({ ok: true, json: () => Promise.resolve(rev) });
            }
            return Promise.reject(new Error('Unknown endpoint'));
        });
        const editor = new Editor({ extensions: [StarterKit] });
        // Load template
        const tpl = await fetch('/templates/standard').then(r => r.json());
        editor.commands.setContent(tpl.content);
        expect(editor.getHTML()).toContain('Standard Document Template');
        // Edit and save revision
        editor.chain().focus().insertContent('<p>Extra</p>').run();
        const first = editor.getHTML();
        await fetch('/documents/demo/revisions', { method: 'POST', body: JSON.stringify({ content: first }) });
        expect(revisions).toHaveLength(1);
        // Make another edit and save second revision
        editor.chain().focus().insertContent('<p>Another</p>').run();
        await fetch('/documents/demo/revisions', { method: 'POST', body: JSON.stringify({ content: editor.getHTML() }) });
        expect(revisions).toHaveLength(2);
        // Restore first revision
        const saved = await fetch('/documents/demo/revisions/1').then(r => r.json());
        editor.commands.setContent(saved.content);
        expect(editor.getHTML()).toBe(first);
    });
});
