import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';

const DEFAULT_DOCS_URL = 'https://eputnam77.github.io/DocReview360/';

describe('DocsPage', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    cleanup();
  });

  it('uses the default documentation URL when NEXT_PUBLIC_DOCS_URL is not set', async () => {
    vi.unstubAllEnvs();

    const { default: DocsPage } = await import('../pages/docs');
    render(<DocsPage />);

    expect(screen.getByTitle('Documentation').getAttribute('src')).toBe(DEFAULT_DOCS_URL);
  });

  it('uses NEXT_PUBLIC_DOCS_URL when provided', async () => {
    const customDocsUrl = 'https://docs.docreview360.dev/';
    vi.stubEnv('NEXT_PUBLIC_DOCS_URL', customDocsUrl);

    const { default: DocsPage } = await import('../pages/docs');
    render(<DocsPage />);

    expect(screen.getByTitle('Documentation').getAttribute('src')).toBe(customDocsUrl);
  });
});
