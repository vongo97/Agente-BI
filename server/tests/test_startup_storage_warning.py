"""P-49 · El arranque debe avisar de que el almacenamiento en nube no está listo.

P-49 decía: *"Sin `SUPABASE_*` el endpoint devuelve 503 y **el arranque no lo
avisa**"*. Desde la ronda del 2026-11-14 el contrato de `/upload` ya no aborta
con 503 (devuelve 200 con `persisted=false`), así que la mitad (a) del criterio
de cierre —el aviso al arrancar— es la que faltaba.

Por qué importa: en Render el disco del contenedor es **efímero**. Si nadie
mira los logs, el síntoma es que "las subidas desaparecen" sin explicación
nadie sabe si es un fallo del servidor o que el archivo nunca llegó a la nube.

Este test es un **control mecánico** del aviso. Para que no sea un control
vacuo (que pasa siempre, incluso con el código roto), el bloque de auditoría
se **extrae del código real con AST y se ejecuta** con un `storage_configured`
controlado: así se comprueba el comportamiento, no la presencia de una cadena
en el fichero.

No se importa `main` directamente (arrancaría el servicio): se extrae el
bloque `if not storage_configured(): ...` del AST y se ejecuta en aislamiento.
"""
from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MAIN_PY = REPO_ROOT / "server" / "main.py"

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def _cuerpo_de_main() -> str:
    """El código fuente de `main.py`, que es donde vive la auditoría."""
    return MAIN_PY.read_text(encoding="utf-8")


def _bloque_de_auditoria() -> ast.If:
    """El `if` del módulo que decide si el almacenamiento está configurado.

    Se localiza por AST para no depender del formato, y se exige que sea
    **de nivel de módulo** (no dentro de una función): lo que significa
    "al arrancar" es exactamente eso.
    """
    arbol = ast.parse(_cuerpo_de_main())
    for nodo in arbol.body:
        if not isinstance(nodo, ast.If):
            continue
        if "storage_configured" in ast.unparse(nodo.test):
            return nodo
    raise AssertionError(
        "main.py no tiene un bloque de auditoría de almacenamiento a nivel de "
        "módulo; P-49 exige que el aviso salga al iniciar, no solo en /upload"
    )


def _ejecutar_auditoria(configurado: bool) -> list[str]:
    """Ejecuta el bloque de auditoría y devuelve los avisos que emitió.

    El bloque se compila y se ejecuta con un namespace propio donde
    `storage_configured` y `logger` están controlados por el test. Así se
    comprueba el **comportamiento** de la rama real del código, no su texto.
    """
    import logging

    bloque = _bloque_de_auditoria()
    modulo = ast.Module(body=[bloque], type_ignores=[])
    ast.fix_missing_locations(modulo)
    codigo = compile(modulo, filename="<auditoria_almacenamiento>", mode="exec")

    # Logger que captura los avisos en una lista.
    capturado: list[str] = []

    class _Capturador(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            capturado.append(record.getMessage())

    logger = logging.getLogger("test_auditoria_almacenamiento")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    logger.handlers = [_Capturador()]

    namespace = {
        "storage_configured": lambda: configurado,
        "logger": logger,
    }
    exec(codigo, namespace)  # noqa: S102 - se ejecuta código del propio repo

    return capturado


def _avisos_de_arranque() -> list[str]:
    """Todos los mensajes de aviso que `main.py` emite al arrancar.

    Se localizan por AST (no por grep) para no depender del formato: se
    buscan las llamadas a `logger.warning(...)` que están **a nivel de módulo**
    (no dentro de una función), que es exactamente lo que significa "al
    arrancar".
    """
    arbol = ast.parse(_cuerpo_de_main())
    mensajes: list[str] = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Expr) or not isinstance(nodo.value, ast.Call):
            continue
        llamada = nodo.value
        func = llamada.func
        if not (isinstance(func, ast.Attribute) and func.attr == "warning"):
            continue
        # `logger.warning(...)`: el primer argumento debe ser un logger cuyo
        # nombre sea "logger" (el del módulo), no uno de otro objeto.
        if not (isinstance(func.value, ast.Name) and func.value.id == "logger"):
            continue
        if not llamada.args:
            continue
        primero = llamada.args[0]
        if isinstance(primero, ast.Constant) and isinstance(primero.value, str):
            mensajes.append(primero.value)
    return mensajes


class TestAvisoDeAlmacenamientoAlArrancar:
    """P-49: el arranque avisa del estado del almacenamiento."""

    def test_existe_el_bloque_de_auditoria_de_almacenamiento(self):
        """`main.py` debe auditar el almacenamiento al arrancar."""
        # `_bloque_de_auditoria()` lanza si no existe: es la comprobación.
        assert _bloque_de_auditoria() is not None

    def test_avisa_cuando_el_almacenamiento_no_esta_configurado(self):
        """Sin nube configurada, el arranque DEBE emitir un aviso.

        Este es el control que falla si alguien neutraliza la rama (por
        ejemplo `if False:`), porque ejecuta el bloque de verdad.
        """
        avisos = _ejecutar_auditoria(configurado=False)
        assert any("SUPABASE_URL" in a for a in avisos), (
            "el arranque no avisa de que SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY "
            f"no están configuradas. Avisos emitidos: {avisos}"
        )

    def test_no_avisa_cuando_el_almacenamiento_si_esta_configurado(self):
        """Con la nube configurada NO debe salir el aviso de "no configurado".

        Sin este test, el control anterior pasaría aunque el aviso se emitiera
        siempre: el ruido en los logs de producción.hidden hide real problems.
        """
        avisos = _ejecutar_auditoria(configurado=True)
        assert not any("no configuradas" in a for a in avisos), (
            "el arranque avisa de que falta la nube aunque esté configurada: "
            f"ruido falso en los logs. Avisos emitidos: {avisos}"
        )

    def test_el_aviso_es_accionable(self):
        """El aviso dice QUÉ definir, no solo que algo falta."""
        avisos = _ejecutar_auditoria(configurado=False)
        aviso = next(
            (a for a in avisos if "SUPABASE_URL" in a and "SUPABASE_SERVICE_ROLE_KEY" in a),
            None,
        )
        assert aviso is not None, (
            "no hay un aviso de arranque que nombre SUPABASE_URL y "
            "SUPABASE_SERVICE_ROLE_KEY; el aviso debe ser accionable"
        )
        # Y debe explicar la consecuencia, no solo el síntoma.
        assert "disco local" in aviso or "persisted" in aviso, (
            "el aviso debe explicar qué pasa con los archivos sin nube"
        )

    def test_el_aviso_no_exige_la_nube_para_arrancar(self):
        """El arranque NO puede abortar si falta la nube: se degrada con aviso.

        Es la diferencia entre "fail-closed" y "no se puede trabajar". El
        criterio de P-49 pide degradar con aviso explícito, no impedir el
        arranque: un `raise` en la auditoría de almacenamiento convertiría
        un servicio con almacenamiento local en un servicio que no arranca.
        """
        bloque = _bloque_de_auditoria()
        for interno in ast.walk(bloque):
            if isinstance(interno, ast.Raise):
                raise AssertionError(
                    "la auditoría de almacenamiento aborta el arranque con "
                    "raise; P-49 exige degradar con aviso, no impedir arrancar"
                )

    def test_el_mensaje_no_filtra_credenciales(self):
        """El aviso no puede imprimir la clave ni la URL de la nube."""
        avisos = _ejecutar_auditoria(configurado=False)
        aviso = next((a for a in avisos if "SUPABASE_URL" in a), "")
        assert "sb_secret_" not in aviso
        assert "eyJ" not in aviso
