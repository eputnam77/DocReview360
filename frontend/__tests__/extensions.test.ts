import { describe, it, expect, vi } from 'vitest';
import { Editor } from '@tiptap/core';
import StarterKit from '@tiptap/starter-kit';

import lintExtension from '../extensions/lint';
import { tiptapIndentation } from '../extensions/tiptapIndentation';
import { tiptapSectionNode } from '../extensions/tiptapSectionNode';
import { tiptapStructure, isValidStructure } from '../extensions/tiptapStructure';
import { tiptapYjsCollab } from '../extensions/tiptapYjsCollab';
import { tiptapHeadingLock } from '../extensions/tiptapHeadingLock';
import { tiptapMarkReview } from '../extensions/tiptapMarkReview';
import SlashCommand from '../extensions/tiptapSlashCommand';
import { tiptapWatermark } from '../extensions/tiptapWatermark';

// Mock yjs and y-webrtc for collaboration tests
class MockDoc {}
const destroyMock = vi.fn();
vi.mock('yjs', () => ({ Doc: MockDoc }));
vi.mock('y-webrtc', () => ({
  WebrtcProvider: class {
    destroy = destroyMock;
    constructor(public room: string, public doc: any) {}
  },
}));

describe('lint extension', () => {
  it('registers data-lint attribute on paragraph schema', () => {
    const editor = new Editor({
      extensions: [StarterKit, lintExtension],
    });
    expect(editor.schema.nodes.paragraph.spec.attrs['data-lint']).toBeDefined();
    editor.destroy();
  });
});

describe('indentation commands', () => {
  it('indent and outdent adjust data-indent attribute', () => {
    const editor = new Editor({
      extensions: [StarterKit, tiptapIndentation()],
      content: '<p>Hello</p>',
    });
    editor.commands.indent();
    expect(editor.getHTML()).toContain('data-indent="1"');
    editor.commands.outdent();
    expect(editor.getHTML()).not.toContain('data-indent="1"');
    editor.destroy();
  });
});

describe('section-node extension', () => {
  it('registers section node', () => {
    const editor = new Editor({
      extensions: [StarterKit, tiptapSectionNode()],
      content: '<section><h2>Title</h2><p>Body</p></section>',
    });
    expect(editor.state.doc.firstChild?.type.name).toBe('section-node');
    editor.destroy();
  });
});

describe('structure extension', () => {
  it('prevents consecutive headings', () => {
    const editor = new Editor({
      extensions: [StarterKit, tiptapStructure()],
      content: '<h1>One</h1>',
    });
    editor.commands.setTextSelection(editor.state.doc.content.size);
    const before = editor.getHTML();
    editor.commands.insertContent('<h2>Two</h2>');
    expect(editor.getHTML()).toBe(before);
    editor.destroy();
  });

  it('validates structure helper', () => {
    expect(isValidStructure('<h1>A</h1><h2>B</h2>')).toBe(false);
    expect(isValidStructure('<h1>A</h1><p>B</p>')).toBe(true);
  });
});

describe('yjs collaboration extension', () => {
  it('stores doc and destroys provider on teardown', async () => {
    const editor = new Editor({ extensions: [StarterKit, tiptapYjsCollab()] });
    await new Promise(r => setTimeout(r, 0));
    const storage: any = (editor as any).storage.yjs;
    expect(storage.doc).toBeInstanceOf(MockDoc);
    editor.destroy();
    expect(destroyMock).toHaveBeenCalled();
  });
});

describe('heading lock extension', () => {
  it('provides backspace and delete handlers', () => {
    const ext = tiptapHeadingLock();
    const shortcuts = ext.config.addKeyboardShortcuts?.call(ext as any);
    expect(typeof shortcuts?.Backspace).toBe('function');
    expect(typeof shortcuts?.Delete).toBe('function');
  });

  it('allows edits outside locked headings', () => {
    const element = document.createElement('div');
    document.body.appendChild(element);
    const editor = new Editor({
      element,
      extensions: [StarterKit, tiptapHeadingLock()],
      content: '<h1>Locked</h1><p>Body</p>',
    });
    editor.commands.setTextSelection(editor.state.doc.content.size - 1);
    editor.commands.insertContent('!');
    expect(editor.getHTML()).toContain('<p>Body!</p>');
    editor.destroy();
    element.remove();
  });
});

describe('mark review extension', () => {
  it('warns when markreview package unavailable', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const editor = new Editor({ extensions: [StarterKit, tiptapMarkReview()] });
    await new Promise(r => setTimeout(r, 0));
    expect(warn).toHaveBeenCalled();
    editor.destroy();
    warn.mockRestore();
  });
});

describe('slash command extension', () => {
  it('inserts label via command', () => {
    const editor = new Editor({ extensions: [StarterKit, SlashCommand] });
    const ext: any = editor.extensionManager.extensions.find(e => e.name === 'slash-command');
    const command = ext.options.suggestion.command;
    command({ editor, range: { from: 1, to: 1 }, props: { label: 'Hello' } });
    expect(editor.getText()).toBe('Hello');
    editor.destroy();
  });
});

describe('watermark extension', () => {
  it('adds watermark element to DOM', () => {
    const outer = document.createElement('div');
    const inner = document.createElement('div');
    outer.appendChild(inner);
    document.body.appendChild(outer);
    const editor = new Editor({ element: inner, extensions: [StarterKit, tiptapWatermark('WM')] });
    const watermark = outer.querySelector('div:last-child');
    expect(watermark?.textContent).toBe('WM');
    editor.destroy();
  });
});


