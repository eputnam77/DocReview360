import { describe, it, expect, vi } from 'vitest';
import { logSaveError, isOffline } from '../utils/saveStatus';
describe('save status helper', () => {
    it('detects offline status', async () => {
        const fetchMock = vi.fn().mockResolvedValue({ ok: true });
        vi.stubGlobal('fetch', fetchMock);
        Object.defineProperty(global, 'navigator', { value: { onLine: false }, configurable: true });
        const status = await logSaveError(new Error('fail'));
        expect(status).toBe('offline');
        expect(fetchMock).toHaveBeenCalled();
        expect(isOffline()).toBe(true);
    });
    it('returns error when online', async () => {
        const fetchMock = vi.fn().mockResolvedValue({ ok: true });
        vi.stubGlobal('fetch', fetchMock);
        Object.defineProperty(global, 'navigator', { value: { onLine: true }, configurable: true });
        const status = await logSaveError(new Error('fail'));
        expect(status).toBe('error');
        expect(isOffline()).toBe(false);
    });
});
