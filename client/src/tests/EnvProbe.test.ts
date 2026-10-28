import { describe, it, expect } from 'vitest';

/**
 * P-65: regresión del entorno de pruebas.
 *
 * Node >= 24 expone un `localStorage` experimental vacío sin
 * --localstorage-file, y el populateGlobal de vitest excluye las claves de
 * jsdom que ya existen en Node. Sin el polyfill de setup.ts, los tests ven
 * `undefined` y componentes como ThemeContext o DashboardContext fallan con
 * "Cannot read properties of undefined (reading 'getItem')".
 */
describe('test environment storage', () => {
  it('exposes a working localStorage', () => {
    expect(typeof localStorage).toBe('object');
    localStorage.setItem('vektra-theme', 'dark');
    expect(localStorage.getItem('vektra-theme')).toBe('dark');
    localStorage.removeItem('vektra-theme');
    expect(localStorage.getItem('vektra-theme')).toBeNull();
    localStorage.clear();
    expect(localStorage.length).toBe(0);
  });

  it('exposes a working sessionStorage', () => {
    expect(typeof sessionStorage).toBe('object');
    sessionStorage.setItem('probe', '1');
    expect(sessionStorage.getItem('probe')).toBe('1');
    sessionStorage.clear();
    expect(sessionStorage.length).toBe(0);
  });
});
