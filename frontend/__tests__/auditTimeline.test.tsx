import { describe, it, expect } from 'vitest';
import { createRoot } from 'react-dom/client';
import React from 'react';
import AuditTimeline, { type AuditEntry } from '../components/AuditTimeline';

describe('AuditTimeline approval events', () => {
  it('renders approval events with readable messages', async () => {
    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = createRoot(container);
    const events: AuditEntry[] = [
      {
        id: '1',
        timestamp: '2024-01-01T10:00:00Z',
        message: 'signature_verified',
        type: 'approval',
      },
      {
        id: '2',
        timestamp: '2024-01-01T11:00:00Z',
        message: 'signature_hash_mismatch',
        type: 'approval',
      },
    ];
    root.render(<AuditTimeline events={events} />);
    await new Promise(r => setTimeout(r, 0));
    const text = container.textContent || '';
    expect(text).toContain('Signature verified');
    expect(text).toContain('Signature hash mismatch');
    root.unmount();
  });
});
