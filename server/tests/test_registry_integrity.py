"""P-74 · Guardián de integridad del registro de problemas.

El registro (`docs/PROBLEMAS_CONOCIDOS.md`) es la **fuente de verdad** que todo
agente lee antes de tocar código. Durante la ronda 7 se descubrió que el propio
registro estaba dañado en cuatro formas independientes:

1. **Mojibake real**: 32 caracteres `U+FFFD` grabados en el fichero (no un
   artefacto de visualización). El fichero decodificaba como UTF-8 válido, así
   que ningún linter lo detectaba.
2. **Separadores rotos**: los `→` y `·` convertidos en `?` literal
   (`? CERRADO`, `texto de 8px ? 12px`), lo que dejaba el **estado** de
   varios P ilegible.
3. **Fila duplicada**: `P-41` aparecía dos veces, con contenido idéntico
   (65 filas para 64 IDs).
4. **Ficha partida dentro de una tabla**: el cuerpo de la ficha de P-40 estaba
   pegado entre dos filas de la tabla de BAJOS, partiendo la fila de P-41 y
   dejando la de P-40 sin celdas de estado ni evidencia.

Y los **totales de la cabecera** eran falsos: declaraban "28 medios · 10
bajos" cuando el conteo real era 30 y 8.

Este test convierte todo eso en un **control mecánico**: si alguien reintroduce
cualquiera de estas formas de deriva, la suite falla.

Es un control de la forma "un control desconectado no existe": no comprueba
que el registro *diga* algo, comprueba que el fichero sea **parseable** y que
sus contadores **cuadren** con lo que contiene.
"""
from __future__ import annotations

import re
import unittest
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY = REPO_ROOT / "docs" / "PROBLEMAS_CONOCIDOS.md"

# IDs con ficha pero SIN fila en el resumen. Son fichas de detalle que el
# resumen no lista: P-42 (deuda de registro declarada) y los P-57..P-65.
# La lista es explícita a propósito: si aparece un ID nuevo aqui, el test
# falla y hay que decidir explicitamente si entra al resumen o no.
FICHAS_SIN_RESUMEN = {42, 57, 58, 59, 61, 62, 63, 64, 65}

FICHAS_RE = re.compile(r"^(?:#{2,4}\s*|\*\*)P-(\d+)")
FILA_RE = re.compile(r"^\|\s*\*\*P-(\d+)\*\*\s*\|")
ESTADO_RE = re.compile(r"(CERRADO|ABIERTO|PARCIAL|ACEPTADO|BLOQUEADO|EN PROGRESO)")
SEVERIDADES = ("CRÍTICO", "ALTO", "MEDIO", "BAJO")


class TestRegistryIntegrity(unittest.TestCase):
    """El registro debe ser parseable, sin duplicados y con los contadores cuadrados."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = REGISTRY.read_bytes()
        cls.text = cls.raw.decode("utf-8")
        cls.lines = cls.text.split("\n")

    # ------------------------------------------------------------------
    # 1. Codificación
    # ------------------------------------------------------------------

    def test_no_bom(self) -> None:
        """El fichero se guarda sin BOM: un BOM rompe el parseo de la primera linea."""
        self.assertFalse(
            self.raw.startswith(b"\xef\xbb\xbf"),
            "docs/PROBLEMAS_CONOCIDOS.md tiene BOM UTF-8; guardalo sin BOM",
        )

    def test_no_caracteres_de_reemplazo(self) -> None:
        """Cero `U+FFFD`: el mojibake no puede quedar grabado en el fichero."""
        self.assertNotIn(
            "�",
            self.text,
            "hay caracteres U+FFFD (mojibake) en el registro; repara el texto",
        )

    def test_no_signo_de_interrogacion_como_separador(self) -> None:
        """El `?` no se usa como flecha ni como separador (daño de la ronda 7)."""
        # La ficha de P-74 *cita* los ejemplos del daño que corrigio (se escribe
        # "el separador '?' en vez de '→'"), así que su bloque queda eximido.
        # Se delimita por el encabezado de la ficha y el siguiente encabezado.
        inicio_exencion = None
        fin_exencion = None
        for i, linea in enumerate(self.lines):
            if linea.startswith("### P-74 ") and inicio_exencion is None:
                inicio_exencion = i
            elif inicio_exencion is not None and linea.startswith("### ") and i > inicio_exencion:
                fin_exencion = i
                break

        ofensas = []
        for numero, linea in enumerate(self.lines, start=1):
            indice = numero - 1
            if inicio_exencion is not None and inicio_exencion <= indice < (fin_exencion or len(self.lines)):
                continue
            for coincidencia in re.finditer(r"\S \? \S", linea):
                # El ternario de JS que se cita en una ficha es legitimo.
                if "(saved ===" in linea:
                    continue
                ofensas.append(f"L{numero}: {linea[max(0, coincidencia.start() - 40):coincidencia.end() + 40]!r}")
        self.assertEqual(
            [],
            ofensas,
            "'?' usado como separador/flecha (deberia ser '→' o '·'):\n" + "\n".join(ofensas),
        )

    # ------------------------------------------------------------------
    # 2. Filas del resumen
    # ------------------------------------------------------------------

    def _seccion_resumen(self) -> tuple[int, int]:
        inicio = next(i for i, l in enumerate(self.lines) if l.startswith("## 2. Resumen"))
        fin = next(i for i, l in enumerate(self.lines) if l.startswith("## 3."))
        return inicio, fin

    def _filas(self) -> list[tuple[int, int, str]]:
        """Devuelve (numero_de_linea, id, seccion) de cada fila del resumen."""
        inicio, fin = self._seccion_resumen()
        seccion = None
        filas = []
        for i in range(inicio, fin):
            linea = self.lines[i]
            if linea.startswith("### "):
                seccion = linea[4:].strip()
                continue
            coincidencia = FILA_RE.match(linea)
            if coincidencia and seccion is not None:
                filas.append((i + 1, int(coincidencia.group(1)), seccion))
        return filas

    def test_sin_filas_duplicadas(self) -> None:
        """Cada ID aparece una sola vez (P-41 estaba duplicado)."""
        ids = [pid for _, pid, _ in self._filas()]
        repetidos = [pid for pid, n in Counter(ids).items() if n > 1]
        self.assertEqual(
            [],
            repetidos,
            f"IDs con fila duplicada en el resumen: {repetidos}",
        )

    def test_toda_fila_tiene_5_celdas(self) -> None:
        """Toda fila tiene ID | Area | Problema | Estado | Evidencia."""
        infracciones = []
        for numero, linea in enumerate(self.lines, start=1):
            coincidencia = FILA_RE.match(linea)
            if not coincidencia:
                continue
            celdas = linea.strip().strip("|").split("|")
            if len(celdas) != 5:
                infracciones.append(f"L{numero}: P-{coincidencia.group(1)} tiene {len(celdas)} celdas")
        self.assertEqual([], infracciones, "filas con un numero de celdas distinto de 5:\n" + "\n".join(infracciones))

    def test_toda_fila_tiene_estado_legible(self) -> None:
        """La celda de estado no puede estar vacia ni corrupta (fue `? CERRADO`)."""
        infracciones = []
        for numero, linea in enumerate(self.lines, start=1):
            coincidencia = FILA_RE.match(linea)
            if not coincidencia:
                continue
            celdas = linea.strip().strip("|").split("|")
            if len(celdas) >= 4 and not ESTADO_RE.search(celdas[3]):
                infracciones.append(f"L{numero}: P-{coincidencia.group(1)} celda de estado = {celdas[3]!r}")
        self.assertEqual([], infracciones, "filas sin estado legible:\n" + "\n".join(infracciones))

    def test_cabeceras_de_tablas_declaran_5_columnas(self) -> None:
        """Las cuatro tablas del resumen declaran las mismas 5 columnas que sus filas."""
        inicio, fin = self._seccion_resumen()
        cabeceras = [l for l in self.lines[inicio:fin] if l.startswith("| ID |")]
        self.assertEqual(4, len(cabeceras), "se esperaban 4 tablas de resumen")
        for cabecera in cabeceras:
            self.assertEqual(
                "| ID | Área | Problema | Estado | Evidencia |",
                cabecera.strip(),
                "cabecera de tabla con columnas incorrectas",
            )

    def test_ninguna_ficha_dentro_de_una_tabla(self) -> None:
        """Las fichas van fuera de las tablas: pegadas dentro, rompen el parseo de filas.

        El bloque de la ficha de P-40 (`**Correccion aplicada.**` ...) estaba
        intercalado entre dos filas de la tabla de BAJOS.
        """
        inicio, fin = self._seccion_resumen()
        interferences = []
        for i in range(inicio, fin):
            linea = self.lines[i]
            # Lineas de tabla: empiezan y acaban en "|".
            if linea.startswith("|") and linea.rstrip().endswith("|"):
                continue
            # Una ficha pegada dentro de la tabla: texto en negrita con punto medio,
            # entre dos filas de la tabla.
            if re.match(r"^\*\*[^*]+\.\*\*\s*$", linea.strip()):
                interferences.append(f"L{i + 1}: {linea.strip()[:80]!r}")
        self.assertEqual(
            [],
            interferences,
            "bloques de ficha intercalados dentro de una tabla del resumen:\n" + "\n".join(interferences),
        )

    # ------------------------------------------------------------------
    # 3. Fichas <-> filas
    # ------------------------------------------------------------------

    def test_toda_fila_tiene_ficha(self) -> None:
        """Cada fila del resumen tiene su ficha detallada."""
        fichas = {int(m.group(1)) for l in self.lines if (m := FICHAS_RE.match(l))}
        sin_ficha = sorted({pid for _, pid, _ in self._filas()} - fichas)
        self.assertEqual(
            [],
            sin_ficha,
            f"filas de resumen sin ficha: {sin_ficha}",
        )

    def test_toda_ficha_tiene_fila_o_esta_declarada(self) -> None:
        """Cada ficha tiene fila de resumen, salvo las declaradas como deuda."""
        fichas = {int(m.group(1)) for l in self.lines if (m := FICHAS_RE.match(l))}
        filas = {pid for _, pid, _ in self._filas()}
        sin_fila = sorted(fichas - filas - FICHAS_SIN_RESUMEN)
        self.assertEqual(
            [],
            sin_fila,
            f"fichas sin fila de resumen (no declaradas en FICHAS_SIN_RESUMEN): {sin_fila}",
        )

    # ------------------------------------------------------------------
    # 4. Totales de la cabecera
    # ------------------------------------------------------------------

    def test_totales_declarados_cuadran_con_las_filas(self) -> None:
        """Los contadores de la cabecera se derivan de las filas, no se escriben a mano."""
        filas = self._filas()
        contados = {sev: 0 for sev in SEVERIDADES}
        for _, _, seccion in filas:
            for sev in SEVERIDADES:
                if sev in seccion:
                    contados[sev] += 1
                    break

        coincidencia = re.search(
            r"\*\*Totales:\*\*\s*(\d+)\s+críticos\s*·\s*(\d+)\s+altos\s*·\s*(\d+)\s+medios\s*·\s*"
            r"\*\*(\d+)\s+bajos\*\*",
            self.text,
        )
        self.assertIsNotNone(coincidencia, "no se encuentra la linea '**Totales:**' con el formato esperado")
        declarados = [int(x) for x in coincidencia.groups()]
        self.assertEqual(
            [contados[sev] for sev in SEVERIDADES],
            declarados,
            f"totales declarados {declarados} != contados desde las filas "
            f"{[contados[sev] for sev in SEVERIDADES]}",
        )


if __name__ == "__main__":
    unittest.main()
