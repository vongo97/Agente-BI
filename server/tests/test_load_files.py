"""
Tests de robustez de la carga de archivos (subida de stress test).

Contexto: el stress test destapo tres fallos reales en load_file_data():
  1. Un CSV de 0 bytes reventaba con EmptyDataError y el router lo traducía a un
     500 "error en el servidor, verifica el formato" (mensaje que culpa al archivo
     cuando el problema es del archivo, pero con el código HTTP equivocado).
  2. Un CSV con solo la fila de encabezados pasaba como "cargado" devolviendo un
     DataFrame 0x0: los nombres de columna se perdían en silencio.
  3. Un CSV cuyo encabezado contenía ';' dentro de un texto (p.ej. cabeceras con
     SQL injection) se parseaba con ';' como separador: 7 columnas de las que solo
     una tenía datos. El criterio de aceptación era "más de una columna => vale",
     así que se aceptaba el parseo corrupto y se perdían 4 de 5 columnas.
"""
import os
import sys

import pandas as pd
import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_load_files.db")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.connectors.data_connectors import ArchivoInvalido, load_file_data


@pytest.fixture()
def csv(tmp_path):
    def _make(content: str, name: str = "t.csv"):
        p = tmp_path / name
        if content == "":
            p.write_bytes(b"")
        else:
            p.write_text(content, encoding="utf-8")
        return str(p)
    return _make


class TestArchivosInvalidos:
    def test_vacio_da_mensaje_explicito(self, csv):
        with pytest.raises(ArchivoInvalido) as exc:
            load_file_data(csv(""))
        msg = str(exc.value).lower()
        assert "vacio" in msg or "vacío" in msg
        # No debe ser un error genérico de servidor
        assert "error al leer" not in msg

    def test_solo_encabezados_no_pasa_como_cargado(self, csv):
        with pytest.raises(ArchivoInvalido) as exc:
            load_file_data(csv("id,nombre,valor\n"))
        assert "encabezados" in str(exc.value).lower()

    def test_espacios_en_blanco_tambien_se_rechazan(self, csv):
        with pytest.raises(ArchivoInvalido):
            load_file_data(csv("\n\n   \n"))


class TestParseoRobusto:
    def test_punto_y_coma_como_separador(self, csv):
        df = load_file_data(csv("id;nombre;valor\n1;ana;10\n2;luis;20\n"))
        assert list(df.columns) == ["id", "nombre", "valor"]
        assert len(df) == 2

    def test_coma_no_se_parte_por_punto_y_coma_dentro_de_texto(self, csv):
        """Regresión: cabecera con ';' dentro de un valor malicioso.

        Con separador ';' la cabecera se parte en varias columnas y las filas de datos
        se quedan con una sola,Filled con NaN. Debe ganar el parseo por coma.
        """
        contenido = (
            "id,nombre,nota,extra\n"
            "1,ana,'roto; DROP TABLE users;--',9\n"
            "2,luis,ok,8\n"
        )
        df = load_file_data(csv(contenido))
        assert len(df.columns) == 4, f"se perdieron columnas: {list(df.columns)}"
        assert len(df) == 2

    def test_tab_como_separador(self, csv):
        df = load_file_data(csv("id\tnombre\n1\tana\n2\tluis\n"))
        assert len(df) == 2

    def test_csv_sucio_se_lee_o_se_rechaza_con_precision(self, csv):
        """Un CSV con comillas rotas debe leerse si se puede, y si no, rechazarse
        con el motivo real (nunca con un mensaje de 'solo encabezados' que no es
        cierto: el archivo sí tiene filas)."""
        contenido = 'id,ciudad,precio\n1,"Santander,300\n2,Medellín,45\n3,Cali,99\n'
        try:
            df = load_file_data(csv(contenido))
            assert not df.empty
        except ArchivoInvalido as exc:
            msg = str(exc).lower()
            assert "encabezados" not in msg, f"diagnostico engañoso: {msg}"
            assert "interpretar" in msg or "comillas" in msg

    def test_utf8_con_acentos(self, csv):
        df = load_file_data(csv("id,ciudad\n1,Santiago\n2,Valparaíso\n"))
        assert list(df.columns) == ["id", "ciudad"]

    def test_columnas_duplicadas_se_hacen_unicas(self, csv):
        df = load_file_data(csv("id,id,valor\n1,2,3\n"))
        assert len(set(df.columns)) == len(df.columns)


class TestExcel:
    def test_xlsx_basico(self, tmp_path):
        p = tmp_path / "libro.xlsx"
        with pd.ExcelWriter(p, engine="openpyxl") as w:
            pd.DataFrame({"trimestre": ["Q1"], "ingresos": [100]}).to_excel(w, index=False)
        df = load_file_data(str(p))
        assert not df.empty