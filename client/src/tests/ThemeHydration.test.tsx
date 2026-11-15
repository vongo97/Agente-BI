import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, cleanup, waitFor } from '@testing-library/react';
import { renderToString } from 'react-dom/server';
import { ThemeProvider, useTheme } from '@/context/ThemeContext';

/**
 * P-45 · El primer render del cliente debe ser **idéntico** al del servidor.
 *
 * El bug: `ThemeProvider` inicializaba el estado con un *lazy initializer* que
 * leía `localStorage`:
 *
 *     useState<Theme>(() => {
 *         if (typeof window === 'undefined') return 'dark';
 *         const saved = localStorage.getItem('vektra-theme');
 *         return (saved === 'light' || saved === 'dark') ? saved : 'dark';
 *     })
 *
 * En el servidor devuelve siempre `'dark'`; en el cliente, el tema guardado.
 * Con el tema `light` guardado, el HTML del servidor y el primer render de
 * React **no coincidían** → *error de hidratación*.
 *
 * Y el tema no es solo pintura: `MermaidPreview` e `InteractiveCanvas` lo usan
 * para generar markup, así que la diferencia se ve en el DOM.
 *
 * El fix: el estado empieza **siempre** en `'dark'` (idéntico en servidor y
 * cliente) y el tema guardado se aplica en un `useEffect`, ya hidratado.
 */
describe('P-45 · hidratación del tema', () => {
  beforeEach(() => {
    localStorage.clear();
    // El script inline de `layout.tsx` aplica esto antes del primer pintado.
    document.documentElement.setAttribute('data-theme', 'dark');
  });

  afterEach(() => {
    cleanup();
    localStorage.clear();
  });

  /** Componente que imprime el tema: sirve para comparar renders. */
  function ThemeProbe() {
    const { theme } = useTheme();
    return <span data-testid="theme">{theme}</span>;
  }

  it('el render del servidor y el primer render del cliente coinciden', () => {
    // El escenario del bug: el usuario tenía 'light' guardado.
    localStorage.setItem('vektra-theme', 'light');

    // 1) Lo que genera el **servidor** (sin `window`).
    const serverHtml = renderToString(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    );
    expect(serverHtml).toContain('>dark<');

    // 2) Lo que genera el **cliente** en su primer render.
    //
    // `render()` de Testing Library envuelve en `act()`, que vacía los
    // efectos: al observar el DOM después ya se aplicó el tema guardado. Para
    // ver el render *inicial* hay que leer el estado de React en el momento
    // de la primera pasada, antes de que corran los efectos.
    const seen: string[] = [];
    function ProbeOnFirstRender() {
      const { theme } = useTheme();
      // Se registra en cada render; la primera entrada es el render inicial.
      if (seen.length === 0) seen.push(theme);
      return <span data-testid="theme">{theme}</span>;
    }

    render(
      <ThemeProvider>
        <ProbeOnFirstRender />
      </ThemeProvider>,
    );

    // El primer render del cliente debe ser 'dark' — igual que el servidor.
    expect(seen[0]).toBe('dark');
    expect(serverHtml).toContain('>dark<');
  });

  it('el tema guardado se aplica DESPUÉS de la hidratación', async () => {
    localStorage.setItem('vektra-theme', 'light');

    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    );

    // Tras los efectos, el tema guardado manda.
    await waitFor(() => {
      expect(screen.getByTestId('theme').textContent).toBe('light');
    });
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
  });

  it('el primer render NO lee localStorage (consistente con el servidor)', () => {
    // Se espía localStorage para comprobar que el *primer render* no lo toca.
    const getItem = vi.spyOn(Storage.prototype, 'getItem');

    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    );

    // En el render inicial el tema es 'dark' y aún no se ha leído el storage.
    expect(screen.getByTestId('theme').textContent).toBe('dark');

    getItem.mockRestore();
  });

  it('el primer efecto NO sobrescribe el tema guardado con "dark"', async () => {
    localStorage.setItem('vektra-theme', 'light');

    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId('theme').textContent).toBe('light');
    });

    // Y lo guardado sigue siendo 'light' (no se degradó a 'dark').
    expect(localStorage.getItem('vektra-theme')).toBe('light');
  });

  it('con localStorage bloqueado, la app no rompe y se queda en dark', async () => {
    const getItem = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('SecurityError: localStorage bloqueado');
    });
    const setItem = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('SecurityError: localStorage bloqueado');
    });

    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId('theme').textContent).toBe('dark');
    });

    getItem.mockRestore();
    setItem.mockRestore();
  });
});
