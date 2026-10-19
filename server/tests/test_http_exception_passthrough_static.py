"""Guarda estatica contra el anti-patron P-43 en TODOS los routers.

Un `except Exception` que envuelve un `raise HTTPException(...)` deliberado
convierte el 400/404 en un 500 "Error interno" y el usuario pierde el motivo.

Este test recorre el AST de cada router y falla si encuentra un `try` cuyo
cuerpo lanza `HTTPException` y cuyos handlers no incluyen un
`except HTTPException` previo al `except Exception` (o equivalente).
"""
import ast
import os
import unittest

RAIZ_SERVIDOR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DIR_ROUTERS = os.path.join(RAIZ_SERVIDOR, "src", "routers")

TIPOS_CAPTURA_TOTAL = {"Exception", "BaseException"}


def _es_http_exception(nodo) -> bool:
    """True si el nodo del AST es `HTTPException` (con o sin `as e`)."""
    return isinstance(nodo, ast.Name) and nodo.id == "HTTPException"


def _handler_captura_http_exception(handler: ast.ExceptHandler) -> bool:
    tipo = handler.type
    if tipo is None:  # `except:` desnudo
        return False
    if _es_http_exception(tipo):
        return True
    if isinstance(tipo, ast.Tuple):
        return any(_es_http_exception(t) for t in tipo.elts)
    return False


def _handler_captura_todo(handler: ast.ExceptHandler) -> bool:
    if handler.type is None:
        return True
    if isinstance(handler.type, ast.Name) and handler.type.id in TIPOS_CAPTURA_TOTAL:
        return True
    if isinstance(handler.type, ast.Tuple):
        return any(
            isinstance(t, ast.Name) and t.id in TIPOS_CAPTURA_TOTAL
            for t in handler.type.elts
        )
    return False


def _lanza_http_exception(nodos) -> bool:
    """Busca `raise HTTPException(...)` saltando los `try` anidados (tienen su
    propio manejo y no son responsabilidad del try exterior)."""
    pila = list(nodos)
    while pila:
        nodo = pila.pop()
        if isinstance(nodo, ast.Try):
            continue  # el manejo del try anidado es del try anidado
        if isinstance(nodo, ast.Raise):
            exc = nodo.exc
            if isinstance(exc, ast.Call) and _es_http_exception(exc.func):
                return True
            if _es_http_exception(exc):
                return True
        pila.extend(ast.iter_child_nodes(nodo))
    return False


def _primer_handler_total(handlers):
    for indice, handler in enumerate(handlers):
        if _handler_captura_todo(handler):
            return indice
    return None


def auditar_archivo(ruta: str):
    """Devuelve la lista de (funcion, linea) con el anti-patron."""
    with open(ruta, "r", encoding="utf-8") as fh:
        arbol = ast.parse(fh.read(), filename=ruta)

    hallazgos = []

    class Visitante(ast.NodeVisitor):
        def __init__(self):
            self.funcion = "<modulo>"

        def visit_FunctionDef(self, nodo):  # noqa: N802
            anterior = self.funcion
            self.funcion = nodo.name
            self.generic_visit(nodo)
            self.funcion = anterior

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Try(self, nodo):  # noqa: N802
            indice_total = _primer_handler_total(nodo.handlers)
            if indice_total is not None and _lanza_http_exception(nodo.body):
                previos = nodo.handlers[:indice_total]
                if not any(_handler_captura_http_exception(h) for h in previos):
                    hallazgos.append((self.funcion, nodo.lineno))
            self.generic_visit(nodo)

    Visitante().visit(arbol)
    return hallazgos


class NadieSeTragaUnHttpExceptionTest(unittest.TestCase):
    def test_todos_los_routers(self):
        problemas = []
        for nombre in sorted(os.listdir(DIR_ROUTERS)):
            if not nombre.endswith(".py"):
                continue
            ruta = os.path.join(DIR_ROUTERS, nombre)
            for funcion, linea in auditar_archivo(ruta):
                problemas.append(f"src/routers/{nombre}:{linea} ({funcion})")

        self.assertEqual(
            [],
            problemas,
            "P-43: anade `except HTTPException: raise` antes del `except Exception` "
            "en estos endpoints:\n  " + "\n  ".join(problemas),
        )


if __name__ == "__main__":
    unittest.main()
