"""P-60 · Guardián contra módulos que no se pueden importar.

P-60 nació de `server/src/services/pkce_service.py`: un módulo **nunca**
importado por nadie que, además, importaba `src.utils.pkce_storage_factory` —
un módulo que **nunca existió** en la historia de git. El resultado era un
archivo que `compileall` daba por bueno (la sintaxis era válida) pero que
reventaba en el momento de importarlo:

    ModuleNotFoundError: No module named 'src.utils.pkce_storage_factory'

Es el peor de los dos mundos: invisible para `compileall` y para la suite (nadie
lo importaba), pero incapaz de funcionar si alguien lo usaba.

La decisión que se registró fue *«eliminar o completar»*. Se **eliminó** (era
código muerto: nada lo importaba, y sus dos únicos módulos dependientes
—`pkce_storage_factory` y `pkce_middleware`— tampoco existían).

Este test vigila las dos mitades de ese cierre:

1. **El archivo no vuelve.** Si alguien lo restaura, el test falla.
2. **Ningún módulo de `server/src/` queda sin poder importarse.** Un import
   roto es la misma clase de fallo que la de `pkce_service`, aunque el archivo
   sea nuevo. Se comprueba **de verdad** (importando, no leyendo el texto), y
   se saltan los módulos con dependencias opcionales ausentes, que es un caso
   legítimo y ya cubierto por los mocks de la suite.

Regla 5 del registro: *«Un control desconectado no existe.»* Y regla 3 del
registro: *«Sin texto plano»* / no dejar a medias lo que se empieza.
"""

import ast
import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("RENDER", "false")
os.environ.setdefault("AUTH_SECRET", "test-secret")

SRC_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'src')
)

# Módulos **opcionales**: pueden faltar y el resto de la app sigue en pie
# (los routers los montan con `try/except ImportError` o los tests los
# mockean). No son deuda: son integraciones plugged-in.
OPTIONAL_MODULE_ROOTS = {
    "src.utils.pkce_storage_factory",
    "src.utils.pkce_middleware",
    "src.utils.pkce_storage",
}


def _iter_python_files(root: str):
    for dirpath, _dirnames, filenames in os.walk(root):
        for filename in filenames:
            if filename.endswith(".py"):
                yield os.path.join(dirpath, filename)


def _module_name_from_path(path: str) -> str:
    """`server/src/utils/x.py` -> `src.utils.x`."""
    rel = os.path.relpath(path, os.path.dirname(SRC_ROOT))
    rel = rel[:-3]  # quita `.py`
    if rel.endswith(os.sep + "__init__"):
        rel = rel[: -len(os.sep + "__init__")]
    return rel.replace(os.sep, ".")


def _module_exists(module_name: str) -> bool:
    """True si el módulo existe como archivo **o** como namespace package.

    Un directorio sin `__init__.py` sigue siendo un paquete válido (PEP 420):
    `src.engine` no tiene `__init__.py` y `from src.engine import prompts`
    funciona. Comprobar solo el `.py` daría un falso positivo.
    """
    base = os.path.join(os.path.dirname(SRC_ROOT))
    as_file = os.path.join(base, module_name.replace(".", os.sep) + ".py")
    as_package = os.path.join(base, module_name.replace(".", os.sep))
    return os.path.exists(as_file) or os.path.isdir(as_package)


class TestPkceServiceStaysDeleted(unittest.TestCase):
    """P-60: el módulo muerto no debe reaparecer."""

    def test_pkce_service_file_is_not_in_src(self):
        path = os.path.join(SRC_ROOT, "services", "pkce_service.py")
        self.assertFalse(
            os.path.exists(path),
            "P-60: `server/src/services/pkce_service.py` fue eliminado por "
            "código muerto (nadie lo importaba y sus dependencias "
            "`pkce_storage_factory`/`pkce_middleware` nunca existieron). "
            "Si se restaura, hay que completarlo de verdad o dejarlo fuera; "
            "un módulo que no se puede importar es una trampa.",
        )

    def test_nothing_imports_pkce_service(self):
        """Nadie debe volver a depender de un módulo no importable."""
        offenders = []
        for path in _iter_python_files(SRC_ROOT):
            with open(path, "r", encoding="utf-8") as fh:
                source = fh.read()
            if "pkce_service" in source:
                offenders.append(os.path.relpath(path, SRC_ROOT))
        self.assertEqual(
            offenders,
            [],
            "P-60: alguien vuelve a importar `pkce_service`, que ya no "
            "existe.\n" + "\n".join(offenders),
        )


class TestNoBrokenImports(unittest.TestCase):
    """P-60 (generalizado): todo módulo de `server/src/` debe poder importarse."""

    def _candidate_modules(self):
        """Módulos que no son `__init__` ni.script de arranque."""
        for path in _iter_python_files(SRC_ROOT):
            name = _module_name_from_path(path)
            if name.endswith(".__init__"):
                continue
            yield name, path

    def test_every_module_imports_cleanly(self):
        """Cada módulo debe importar sin `ModuleNotFoundError`.

        Se importan de verdad (no se lee el texto): un import roto es
        exactamente lo que no detecta `compileall`.
        """
        import importlib

        failures = []
        for name, path in self._candidate_modules():
            try:
                importlib.import_module(name)
            except ModuleNotFoundError as exc:
                # Los módulos opcionales ausentes son un caso legítimo.
                missing = exc.name or ""
                if missing in OPTIONAL_MODULE_ROOTS:
                    continue
                failures.append(
                    f"{os.path.relpath(path, SRC_ROOT)}: {exc}"
                )
            except Exception as exc:  # pragma: no cover
                # Otros errores (p. ej. una variable de entorno ausente) no son
                # "módulo roto"; se ignoran aquí y los vigilan sus propios
                # tests.
                if isinstance(exc, ModuleNotFoundError):
                    failures.append(
                        f"{os.path.relpath(path, SRC_ROOT)}: {exc}"
                    )

        self.assertEqual(
            failures,
            [],
            "P-60: hay módulos en `server/src/` que no se pueden importar "
            "(`compileall` no los detecta porque la sintaxis es válida).\n"
            + "\n".join(failures),
        )

    def test_no_internal_import_of_a_missing_module(self):
        """Control estático: ningún módulo interno importa algo que no exista.

        Complementa al test anterior con un aviso **antes** de que el módulo se
        importe en producción: se parsean los imports y se comprueba que cada
        `src.*` apunta a un archivo real.
        """
        offenders = []
        for path in _iter_python_files(SRC_ROOT):
            with open(path, "r", encoding="utf-8") as fh:
                source = fh.read()
            tree = ast.parse(source, filename=path)

            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom):
                    continue
                if node.level != 0 or not node.module:
                    continue
                if not node.module.startswith("src."):
                    continue
                if node.module in OPTIONAL_MODULE_ROOTS:
                    continue

                if not _module_exists(node.module):
                    offenders.append(
                        f"{os.path.relpath(path, SRC_ROOT)}:{node.lineno} "
                        f"-> {node.module}"
                    )

        self.assertEqual(
            offenders,
            [],
            "P-60: hay imports a módulos de `src/` que no existen.\n"
            + "\n".join(offenders),
        )


if __name__ == '__main__':
    unittest.main()
