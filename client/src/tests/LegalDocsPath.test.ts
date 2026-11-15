import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

/**
 * P-20 · Las páginas legales no deben depender de la raíz del repositorio.
 *
 * Antes: `path.join(process.cwd(), "..", "docs", "legal", file)` leía los
 * `.md` de `docs/legal/`, **fuera de `client/`**. Eso funcionaba en
 * `npm run dev` (donde `process.cwd()` es `client/`) y rompía en el build
 * standalone / Docker, donde `process.cwd()` no tiene un `docs/` al lado →
 * 404 en las tres páginas legales.
 *
 * Ahora los `.md` viven en `client/content/legal/` y la resolución prueba
 * **todas** las candidatas posibles según cómo se arrancó el proceso.
 *
 * Este test verifica lo que importa: que **desde cualquier `cwd`** se
 * encuentra el documento, y que el contenido no está vacío (un archivo
 * placeholder no serviría).
 */
describe('P-20 · rutas de los documentos legales', () => {
  const LEGAL_FILES = [
    'politica-privacidad.md',
    'terminos-de-uso.md',
    'aviso-cookies.md',
  ];

  /** Réplica de `resolveLegalFile` (misma lógica que la página). */
  function resolveLegalFile(fileName: string): string | null {
    const candidates = [
      path.join(process.cwd(), 'content', 'legal', fileName),
      path.join(process.cwd(), 'client', 'content', 'legal', fileName),
      path.join(process.cwd(), '..', 'client', 'content', 'legal', fileName),
    ];

    for (const candidate of candidates) {
      if (fs.existsSync(candidate)) return candidate;
    }
    return null;
  }

  const REPO_ROOT = path.resolve(__dirname, '..', '..', '..');
  const CLIENT_ROOT = path.resolve(REPO_ROOT, 'client');

  it('los .md viven DENTRO de client/ (no en la raíz del repo)', () => {
    for (const file of LEGAL_FILES) {
      const inClient = path.join(CLIENT_ROOT, 'content', 'legal', file);
      expect(fs.existsSync(inClient), `falta ${file} en client/content/legal/`).toBe(true);

      // Y ya NO deben existir en docs/legal/ de la raíz.
      const inRepoRoot = path.join(REPO_ROOT, 'docs', 'legal', file);
      expect(
        fs.existsSync(inRepoRoot),
        `${file} sigue en docs/legal/: es lo que rompía el build standalone`,
      ).toBe(false);
    }
  });

  it('el documento se encuentra con cwd = client/', () => {
    for (const file of LEGAL_FILES) {
      const original = process.cwd();
      try {
        process.chdir(CLIENT_ROOT);
        const resolved = resolveLegalFile(file);
        expect(resolved, `no se resolvió ${file} con cwd=client/`).not.toBeNull();
      } finally {
        process.chdir(original);
      }
    }
  });

  it('el documento se encuentra con cwd = raíz del repo (standalone/Docker)', () => {
    for (const file of LEGAL_FILES) {
      const original = process.cwd();
      try {
        process.chdir(REPO_ROOT);
        const resolved = resolveLegalFile(file);
        expect(resolved, `no se resolvió ${file} con cwd=raíz del repo`).not.toBeNull();
      } finally {
        process.chdir(original);
      }
    }
  });

  it('el contenido no está vacío (no es un placeholder)', () => {
    for (const file of LEGAL_FILES) {
      const resolved = resolveLegalFile(file);
      expect(resolved).not.toBeNull();
      const content = fs.readFileSync(resolved as string, 'utf8');
      expect(content.trim().length, `${file} está vacío`).toBeGreaterThan(200);
    }
  });

  it('la página NO lee de fuera de client/', () => {
    const pagePath = path.join(
      CLIENT_ROOT,
      'src',
      'app',
      'legal',
      '[slug]',
      'page.tsx',
    );
    const source = fs.readFileSync(pagePath, 'utf8');

    // Se quitan los comentarios: la página documenta el patrón roto en un
    // comentario, y ese texto no es código (si no, el test se dispararía
    // contra su propia explicación).
    const code = source
      .split('\n')
      .filter((line) => !line.trim().startsWith('//'))
      .join('\n');

    // El patrón roto era leer `docs/legal` relativo al cwd.
    const readsDocsOutside =
      /["']\.\.?["']\s*,\s*["']docs["']|["']docs["']\s*,\s*["']legal["']/.test(
        code,
      );
    expect(
      readsDocsOutside,
      'la página vuelve a leer de docs/ fuera de client/',
    ).toBe(false);

    // Y toda ruta que menciona debe apuntar dentro de `content/legal`.
    // El join puede anidar `process.cwd()`, así que el patrón es "no avaro"
    // (`.*`) hasta la última llave del bloque.
    const legalJoins = code.match(/path\.join\(.*\)/g) ?? [];
    expect(legalJoins.length).toBeGreaterThan(0);
    for (const join of legalJoins) {
      expect(join, `join sin 'content': ${join}`).toContain('content');
      expect(join, `join con 'docs': ${join}`).not.toContain('docs');
    }
  });

  /**
   * P-75 · Turbopack no debe arrastrar el proyecto entero al output de despliegue.
   *
   * Con una ruta calculada en un bucle (`fs.existsSync(candidate)` sobre rutas
   * dinámicas), Turbopack avisa:
   *
   *   Warning: Dynamic filesystem access causes tracing of the whole project
   *
   * y empaqueta **todo** el proyecto (incluido `public/`) en el output del
   * servidor: infla el bundle y puede disparar los límites de tamaño de Render.
   *
   * Turbopack ofrece `/* turbopackIgnore: true *\/` como opt-out explícito
   * para lecturas **deliberadas y acotadas** — que es exactamente este caso.
   * El control comprueba que **toda** llamada a `fs` lo lleva: si alguien
   * añade una lectura sin marcar, el aviso vuelve.
   */
  it('toda lectura de fs lleva el opt-out turbopackIgnore (P-75)', () => {
    const pagePath = path.join(
      CLIENT_ROOT,
      'src',
      'app',
      'legal',
      '[slug]',
      'page.tsx',
    );
    const source = fs.readFileSync(pagePath, 'utf8');
    const code = source
      .split('\n')
      .filter((line) => !line.trim().startsWith('//'))
      .join('\n');

    const llamadas = code.match(/fs\.(existsSync|readFileSync)\([^)]*\)/g) ?? [];
    expect(llamadas.length, 'la página ya no lee ficheros: revisa el test').toBeGreaterThan(0);

    for (const llamada of llamadas) {
      expect(
        llamada,
        `llamada a fs sin turbopackIgnore: ${llamada} (Turbopack arrastrará todo el proyecto)`,
      ).toContain('turbopackIgnore');
    }
  });
});
