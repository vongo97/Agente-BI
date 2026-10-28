import '@testing-library/jest-dom/vitest';

// ── P-65: Storage del entorno de pruebas ────────────────────────────────────
// Node >= 24 expone un `localStorage` experimental que queda vacío sin
// --localstorage-file. El `populateGlobal` de vitest excluye las claves que
// ya existen en el global de Node, así que el localStorage/sessionStorage de
// jsdom NO se copian al entorno y los tests ven `undefined` (reproducido con
// Node v24.13.0: 'localStorage' in globalThis -> true, typeof -> undefined).
// Se reinstala un Storage en memoria con la interfaz del navegador, válida
// para cualquier versión de Node y en CI.
if (typeof globalThis.localStorage === 'undefined' || globalThis.localStorage === null) {
  const createMemoryStorage = (): Storage => {
    const data = new Map<string, string>();
    return {
      get length() { return data.size; },
      clear() { data.clear(); },
      getItem(key: string) { return data.has(String(key)) ? (data.get(String(key)) as string) : null; },
      key(index: number) { return Array.from(data.keys())[index] ?? null; },
      removeItem(key: string) { data.delete(String(key)); },
      setItem(key: string, value: string) { data.set(String(key), String(value)); },
    };
  };
  Object.defineProperty(globalThis, 'localStorage', {
    value: createMemoryStorage(),
    configurable: true,
    writable: true,
  });
  Object.defineProperty(globalThis, 'sessionStorage', {
    value: createMemoryStorage(),
    configurable: true,
    writable: true,
  });
}
