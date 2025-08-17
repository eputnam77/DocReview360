import { describe, it, expect, beforeAll } from 'vitest';
import { createRoot } from 'react-dom/client';
import React from 'react';
import axe from 'axe-core';
import { toolbarButton } from '../components/ToolbarButton';

beforeAll(() => {
  Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', {
    value: () => null,
  });
});

describe('toolbar accessibility', () => {
  it('renders button with proper aria attributes', async () => {
    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = createRoot(container);
    root.render(toolbarButton(<span>icon</span>, () => {}, false, 'Bold'));
    await new Promise(r => setTimeout(r, 0));
    const button = container.querySelector('button');
    expect(button?.getAttribute('aria-label')).toBe('Bold');
    expect(button?.getAttribute('role')).toBe('button');
    const results = await axe.run(container);
    expect(results.violations).toHaveLength(0);
    root.unmount();
  });
});
