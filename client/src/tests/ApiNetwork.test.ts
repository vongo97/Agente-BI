import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { securedFetch, setApiAuthToken } from '@/lib/api';
import { signOut } from 'next-auth/react';

// Mock de next-auth/react a nivel de módulo (hoisted por vitest)
vi.mock('next-auth/react', () => ({
  signOut: vi.fn(),
}));

const originalFetch = globalThis.fetch as typeof fetch;

const mockResponse = (status: number, body: unknown = {}) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });

beforeEach(() => {
  setApiAuthToken('test-token');
  vi.mocked(signOut).mockClear();
  (globalThis.fetch as any) = vi.fn();
  vi.restoreAllMocks();
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  vi.restoreAllMocks();
});

describe('P-08 securedFetch red (timeout, retry, auth)', () => {
  it('resuelve correctamente con HTTP 200 y envía Authorization', async () => {
    (globalThis.fetch as any) = vi.fn().mockResolvedValue(mockResponse(200, { ok: true }));

    const res = await securedFetch('http://localhost:8000/api/v1/test');

    expect(res.status).toBe(200);
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
    const [url, opts] = (globalThis.fetch as any).mock.calls[0];
    expect(url).toBe('http://localhost:8000/api/v1/test');
    expect(opts.headers.Authorization).toBe('Bearer test-token');
    expect(opts.signal).toBeInstanceOf(AbortSignal);
  });

  it('reintenta en errores de red y tiene éxito en el tercer intento', async () => {
    let calls = 0;
    (globalThis.fetch as any) = vi.fn().mockImplementation(() => {
      calls++;
      if (calls < 3) {
        return Promise.reject(new TypeError('Failed to fetch'));
      }
      return Promise.resolve(mockResponse(200, { ok: true }));
    });

    const res = await securedFetch('http://localhost:8000/api/v1/retry');

    expect(res.status).toBe(200);
    expect(calls).toBe(3);
  });

  it('tras 3 intentos de red fallidos lanza el error original', async () => {
    (globalThis.fetch as any) = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'));

    await expect(securedFetch('http://localhost:8000/api/v1/fail')).rejects.toThrow(
      /Failed to fetch/
    );

    expect(globalThis.fetch).toHaveBeenCalledTimes(3);
  });

  it('401 cierra sesión y lanza AuthError sin reintentos', async () => {
    (globalThis.fetch as any) = vi.fn().mockResolvedValue(mockResponse(401, { detail: 'Token expirado' }));

    await expect(securedFetch('http://localhost:8000/api/v1/protected')).rejects.toMatchObject({
      isAuthError: true,
      status: 401,
    });

    expect(signOut).toHaveBeenCalledWith({ callbackUrl: '/login' });
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
  });

  it('403 cierra sesión y lanza AuthError sin reintentos', async () => {
    (globalThis.fetch as any) = vi.fn().mockResolvedValue(mockResponse(403, { detail: 'Prohibido' }));

    await expect(securedFetch('http://localhost:8000/api/v1/forbidden')).rejects.toMatchObject({
      isAuthError: true,
      status: 403,
    });

    expect(signOut).toHaveBeenCalledWith({ callbackUrl: '/login' });
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
  });

  it('pasa AbortSignal a fetch (base del timeout de 30 s)', async () => {
    (globalThis.fetch as any) = vi.fn().mockResolvedValue(mockResponse(200, { ok: true }));

    await securedFetch('http://localhost:8000/api/v1/test');

    const [, opts] = (globalThis.fetch as any).mock.calls[0];
    expect(opts.signal).toBeInstanceOf(AbortSignal);
    expect((opts.signal as AbortSignal).aborted).toBe(false);
  });
});
