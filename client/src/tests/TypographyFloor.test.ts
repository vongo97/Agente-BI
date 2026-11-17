import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

/**
 * P-40 · El texto no puede bajar de 10 px, y los sidebars deben ser responsivos.
 *
 * El cierre de P-40 del 2026-10-22 decía "corregido" pero solo tocó **4**
 * pantallas. Al reconciliar el registro contra el código (ronda 9, 2026-11-15)
 * un `grep` encontró **38 ocurrencias** de `text-[Npx]` con N < 10 repartidas
 * en **10 ficheros** (hasta 7 píxeles), y el historial de ensayos
 * (`SimHistory.tsx`) seguía siendo una **columna fija** en móvil que se
 * comía el ancho de la pantalla.
 *
 * Este test convierte el criterio de cierre del registro en un **control
 * mecánico**: si alguien reintroduce una tipografía por debajo de 10 px, o
 * devuelve el historial a una columna fija en móvil, la suite falla.
 *
 * Nota: este fichero se escanea a sí mismo, así que su propia documentación
 * no puede escribir literalmente la clase prohibida (de ahí "7 píxeles" con
 * palabras en lugar del valor exacto).
 *
 * Es un control de la forma "un control desconectado no existe": no comprueba
 * que el texto *diga* algo, comprueba que el **código** cumple el suelo.
 */
describe('P-40 · suelo tipográfico y sidebars responsivos', () => {
  const REPO_ROOT = path.resolve(__dirname, '..', '..', '..');
  const CLIENT_ROOT = path.resolve(REPO_ROOT, 'client');
  const SRC_ROOT = path.join(CLIENT_ROOT, 'src');

  /** Lista recursiva de ficheros .tsx/.ts/.jsx/.js dentro de client/src. */
  function walk(dir: string): string[] {
    const salida: string[] = [];
    for (const entrada of fs.readdirSync(dir, { withFileTypes: true })) {
      const completo = path.join(dir, entrada.name);
      if (entrada.isDirectory()) {
        salida.push(...walk(completo));
      } else if (/\.(tsx?|jsx?)$/.test(entrada.name)) {
        salida.push(completo);
      }
    }
    return salida;
  }

  const ficheros = walk(SRC_ROOT);
  const RELATIVO = (f: string) => path.relative(CLIENT_ROOT, f).replace(/\\/g, '/');

  it('el árbol de fuentes existe (el control no puede pasar por vacío)', () => {
    expect(ficheros.length).toBeGreaterThan(10);
  });

  it('cero text-[Npx] con N < 10 en client/src/', () => {
    const infracciones: string[] = [];

    for (const fichero of ficheros) {
      const source = fs.readFileSync(fichero, 'utf8');
      const patron = /text-\[(\d+)px\]/g;
      let coincidencia: RegExpExecArray | null;
      while ((coincidencia = patron.exec(source)) !== null) {
        const px = Number(coincidencia[1]);
        if (px < 10) {
          const linea = source.slice(0, coincidencia.index).split('\n').length;
          infracciones.push(
            `${RELATIVO(fichero)}:${linea} -> text-[${px}px] (el suelo es 10px)`,
          );
        }
      }
    }

    expect(
      infracciones,
      `texto por debajo de 10px:\n${infracciones.join('\n')}`,
    ).toEqual([]);
  });

  it('el historial de ensayos es responsivo: cajon en móvil, columna desde md:', () => {
    const simHistoryPath = path.join(SRC_ROOT, 'components', 'simulation', 'SimHistory.tsx');
    const source = fs.readFileSync(simHistoryPath, 'utf8');

    // La columna debe poder esconderse por debajo de `md:` (translate fuera de
    // pantalla) y volver a su sitio desde `md:`.
    expect(
      source,
      'SimHistory debe usar el breakpoint `md:` para volver a su sitio',
    ).toContain('md:translate-x-0');
    expect(
      source,
      'SimHistory debe poder salirse de la pantalla en móvil',
    ).toContain('-translate-x-full');

    // Y debe ser `fixed` en móvil + `relative` desde `md:`: si se queda
    // `fixed` en escritorio, se superpone al contenido.
    expect(source, 'SimHistory debe ser fixed en móvil').toContain('fixed md:relative');

    // El velo y el botón de cerrar solo existen en móvil.
    expect(source, 'falta el velo del cajón').toContain('md:hidden');
    expect(source, 'falta el botón de cerrar').toContain('Cerrar historial');
  });

  it('el sidebar principal también es condicional en móvil', () => {
    const sidebarPath = path.join(SRC_ROOT, 'components', 'Sidebar.tsx');
    const source = fs.readFileSync(sidebarPath, 'utf8');

    expect(source, 'el sidebar principal debe salirse de pantalla en móvil').toContain(
      '-translate-x-full',
    );
    expect(source, 'el sidebar principal debe volver desde lg:').toContain(
      'lg:translate-x-0',
    );
  });
});
