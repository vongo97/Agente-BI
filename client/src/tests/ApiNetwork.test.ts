import { describe, it, expect, vi, beforeEach, afterEach, type Mock } from 'vitest';
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

/**
 * Acceso tipado al mock de `fetch`.
 *
 * Antes se usaba `(globalThis.fetch as any)`: el `any` tapaba justo lo que el
 * test comprueba (que `fetch` se llame con la URL, las cabeceras y el
 * `AbortSignal` esperados). Con `Mock` el compilador exige que esas
 * aserciones se_keepen tipadas.
 */
const fetchMock = () => globalThis.fetch as unknown as Mock<typeof fetch>;

/** Instala un mock de `fetch` globalmente y lo devuelve tipado. */
function mockFetch(): Mock<typeof fetch> {
  const mock = vi.fn() as unknown as Mock<typeof fetch>;
  globalThis.fetch = mock as unknown as typeof fetch;
  return mock;
}

beforeEach(() => {
  setApiAuthToken('test-token');
  vi.mocked(signOut).mockClear();
  mockFetch();
  vi.restoreAllMocks();
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  vi.restoreAllMocks();
});

describe('P-08 securedFetch red (timeout, retry, auth)', () => {
  it('resuelve correctamente con HTTP 200 y envía Authorization', async () => {
    mockFetch().mockResolvedValue(mockResponse(200, { ok: true }));

    const res = await securedFetch('http://localhost:8000/api/v1/test');

    expect(res.status).toBe(200);
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
    const [url, opts] = fetchMock().mock.calls[0];
    expect(url).toBe('http://localhost:8000/api/v1/test');
    // `securedFetch` construye las cabeceras como objeto plano
    // (`Record<string, string>`), no como `Headers`.
    const init = opts as RequestInit & { headers: Record<string, string> };
    expect(init.headers.Authorization).toBe('Bearer test-token');
    expect(init.signal).toBeInstanceOf(AbortSignal);
  });

  it('reintenta en errores de red y tiene éxito en el tercer intento', async () => {
    let calls = 0;
    mockFetch().mockImplementation(() => {
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
    mockFetch().mockRejectedValue(new TypeError('Failed to fetch'));

    await expect(securedFetch('http://localhost:8000/api/v1/fail')).rejects.toThrow(
      /Failed to fetch/
    );

    expect(globalThis.fetch).toHaveBeenCalledTimes(3);
  });

  it('401 cierra sesión y lanza AuthError sin reintentos', async () => {
    mockFetch().mockResolvedValue(mockResponse(401, { detail: 'Token expirado' }));

    await expect(securedFetch('http://localhost:8000/api/v1/protected')).rejects.toMatchObject({
      isAuthError: true,
      status: 401,
    });

    expect(signOut).toHaveBeenCalledWith({ callbackUrl: '/login' });
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
  });

  it('403 cierra sesión y lanza AuthError sin reintentos', async () => {
    mockFetch().mockResolvedValue(mockResponse(403, { detail: 'Prohibido' }));

    await expect(securedFetch('http://localhost:8000/api/v1/forbidden')).rejects.toMatchObject({
      isAuthError: true,
      status: 403,
    });

    expect(signOut).toHaveBeenCalledWith({ callbackUrl: '/login' });
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
  });

  it('pasa AbortSignal a fetch (base del timeout de 30 s)', async () => {
    mockFetch().mockResolvedValue(mockResponse(200, { ok: true }));

    await securedFetch('http://localhost:8000/api/v1/test');

    const [, opts] = fetchMock().mock.calls[0];
    const init = opts as RequestInit;
    expect(init.signal).toBeInstanceOf(AbortSignal);
    expect((init.signal as AbortSignal).aborted).toBe(false);
  });
});
