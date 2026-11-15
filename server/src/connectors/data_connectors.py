import logging
import re
import requests
import pandas as pd
from sqlalchemy import create_engine, inspect
from urllib.parse import quote_plus
from typing import Optional
import urllib.parse

from src.utils.logging_config import log_ignored_error

logger = logging.getLogger(__name__)

# Cache en memoria para sesiones
sql_engines = {}

def clean_sql_url(url):
    """
    Soluciona el problema de SQLAlchemy cuando la contraseña contiene una '@'.
    Ejemplo problemático: postgresql://user:P@assword@host:5432/db
    """
    if "://" not in url or "@" not in url:
        return url
        
    try:
        # Dividir por el ÚLTIMO '@' que separa credenciales del host
        parts = url.rsplit('@', 1)
        if len(parts) != 2: return url
        
        creds_part, host_part = parts
        
        # Separar el esquema (postgresql://) de las credenciales (user:pass)
        scheme_parts = creds_part.split('://', 1)
        if len(scheme_parts) != 2: return url
        
        scheme, user_and_pass = scheme_parts
        
        # Separar usuario de contraseña
        up_parts = user_and_pass.split(':', 1)
        if len(up_parts) == 2:
            user, pwd = up_parts
            # Codificar solo la contraseña
            pwd_encoded = quote_plus(urllib.parse.unquote_plus(pwd))
            return f"{scheme}://{user}:{pwd_encoded}@{host_part}"
        elif len(up_parts) == 1:
            # Sin contraseña
            return url
    except Exception as e:
        from src.database import sanitize_db_error
        logger.debug("Error parseando URL SQL cruda: %s", sanitize_db_error(str(e)))
        return url
        
    return url

def get_sql_engine(url):
    """Crea y devuelve el motor de SQLAlchemy asegurando una URL limpia.

    Valida la URL contra SSRF en el punto único de creación de motores: cubre tanto
    `/connect-sql` como las reconexiones de fuentes guardadas (`ensure_user_session`),
    de modo que una URL persistida tampoco pueda apuntar a la red interna.
    """
    from src.utils.security import validate_external_url_host

    clean_url = clean_sql_url(url)
    validate_external_url_host(clean_url)

    if clean_url not in sql_engines:
        sql_engines[clean_url] = create_engine(clean_url)
    return sql_engines[clean_url]

def get_db_schema(engine):
    """Obtiene el esquema de la base de datos."""
    inspector = inspect(engine)
    schema_info = ""
    for table_name in inspector.get_table_names():
        columns = inspector.get_columns(table_name)
        col_names = [col['name'] for col in columns]
        schema_info += f"Table: {table_name}, Columns: {col_names}\n"
    return schema_info


def get_db_schema_structured(engine):
    """Devuelve el esquema como estructura, no como texto (P-48).

    ``get_db_schema`` devuelve una cadena formateada pensada para prompts de
    LLM. Para validar nombres de tabla y columna contra el catálogo real hace
    falta la estructura: una lista de ``{"table": str, "columns": [str]}``.

    Se introspecta el engine vivo (no el texto guardado), porque el esquema
    guardado es una foto que puede quedarse obsoleta.
    """
    inspector = inspect(engine)
    schema = []
    for table_name in inspector.get_table_names():
        try:
            columns = inspector.get_columns(table_name)
        except Exception as exc:
            # Una tabla que no se puede inspeccionar (permisos, vista rota)
            # no debe tumbar el filtrado completo.
            # P-36: se registra para poder diagnosticar qué tabla se saltó.
            log_ignored_error(
                logger,
                "inspección de columnas de una tabla",
                exc,
                level=logging.WARNING,
                table=table_name,
            )
            continue
        schema.append({
            "table": table_name,
            "columns": [col["name"] for col in columns],
        })
    return schema

def _clean_dataframe(df):
    """Limpieza robusta con detección inteligente de header válido y sanador de mojibake."""
    import re
    import unicodedata

    def repair_mojibake(text):
        if not isinstance(text, str):
            return text
        # Mojibake comunes en español
        patterns = ["Ã“", "Ã³", "Ã¡", "Ã©", "Ã*", "Ãº", "Ã±", "Ã‘", "Â¿", "Â¡"]
        if any(p in text for p in patterns):
            try:
                return text.encode('cp1252').decode('utf-8')
            except (UnicodeEncodeError, UnicodeDecodeError) as cp1252_err:
                try:
                    return text.encode('latin-1').decode('utf-8')
                except (UnicodeEncodeError, UnicodeDecodeError) as latin1_err:
                    # P-36: el texto no es decodificable con ninguna de las dos
                    # codificaciones. No es recuperable, así que se devuelve tal
                    # cual — pero se registra, no se traga en silencio.
                    log_ignored_error(
                        logger,
                        "reparación de mojibake (cp1252 y latin-1 fallaron)",
                        latin1_err,
                        level=logging.DEBUG,
                        cp1252_error=type(cp1252_err).__name__,
                    )
        return text

    def slugify_column(name):
        name = repair_mojibake(str(name))
        name = name.strip().replace('"', '').replace("'", "")
        name = "".join(c for c in unicodedata.normalize('NFD', name) if unicodedata.category(c) != 'Mn')
        name = re.sub(r'[^a-zA-Z0-9]', '_', name).lower()
        name = re.sub(r'_+', '_', name).strip('_')
        return name if name else "nan"

    # 1. Limpieza inicial: Eliminar filas/columnas vacías
    df = df.dropna(how='all').dropna(axis=1, how='all').reset_index(drop=True)
    if df.empty:
        return df

    # 2. Detección de Header:
    cols_are_numeric = all(
        str(c).strip().lstrip('-').replace('.', '', 1).isdigit()
        for c in df.columns
    )

    if not cols_are_numeric:
        # ✅ Caso normal: CSV con header correcto → solo normalizar nombres
        df.columns = [slugify_column(c) for c in df.columns]
    else:
        # 🔧 Caso Excel/CSV sin header: buscar la fila que actúa como cabecera
        for i in range(min(10, len(df))):
            row_as_str = df.iloc[i].astype(str)
            if row_as_str.str.contains(r'[a-zA-Z]').any() and not row_as_str.str.match(r'^\d+\.?\d*$').all():
                header_data = df.iloc[i].fillna("").astype(str)
                df.columns = [slugify_column(c) for c in header_data]
                df = df.iloc[i + 1:].reset_index(drop=True)
                break

    # 3. Forzar Nombres Únicos
    cols = []
    seen = {}
    for c in df.columns:
        c_str = str(c)
        if c_str in seen:
            seen[c_str] += 1
            cols.append(f"{c_str}_{seen[c_str]}")
        else:
            seen[c_str] = 0
            cols.append(c_str)
    df.columns = cols

    # 4. Limpieza de datos: convertir columnas numéricas, de fecha y reparar mojibake
    for col in df.columns:
        if df[col].dtype == 'object':
            # Reparar mojibake en todas las columnas de texto (object/string)
            try:
                df[col] = df[col].apply(repair_mojibake)
            except Exception as e:
                logger.warning("Error reparando mojibake en columna %s: %s", col, e)

            # Intentar conversión numérica
            cleaned = df[col].astype(str).str.replace(r'[^-0-9,.]', '', regex=True).str.replace(',', '.')
            num_series = pd.to_numeric(cleaned, errors='coerce')
            if num_series.notnull().sum() > (len(df) * 0.5):
                df[col] = num_series

        # Conversión de fecha por nombre de columna
        if 'fecha' in col.lower() or 'date' in col.lower() or 'mes' in col.lower():
            try:
                df[col] = pd.to_datetime(df[col], errors='coerce')
            except Exception as exc:
                # P-36: la columna se queda como texto (no se pierde el dato) pero
                # el motivo queda registrado en lugar de desaparecer.
                log_ignored_error(
                    logger,
                    "conversión a datetime de una columna",
                    exc,
                    level=logging.WARNING,
                    column=col,
                )

    # 5. Eliminar filas tipo "nota de pie" (texto largo en pocas celdas)
    if not df.empty and len(df) > 1:
        def is_metadata_note(row):
            text_cells = [str(val) for val in row if len(str(val)) > 50]
            return len(text_cells) >= 1 and row.count() <= 3
        mask = df.apply(is_metadata_note, axis=1)
        df = df[~mask].reset_index(drop=True)

    return df

class ArchivoInvalido(Exception):
    """El archivo se rechaza por su contenido, no por un fallo del servidor.
    El router lo traduce a 400 con el mensaje, en lugar de un 500 generico."""


def _parse_score(df) -> int:
    """Puntua un parseo para elegir el mejor candidato.

    Un parseo con el separador equivocado produce muchas columnas pero casi todas
    vacias: p.ej. un CSV cuya cabecera contiene ';' dentro de un texto se parte en 7
    columnas mientras que cada fila real aporta 1 campo. El criterio antiguo
    ('si tiene mas de una columna, vale') aceptaba ese resultado corrupto y perdia
    todas las columnas. Aqui se puntua cuantas columnas traen datos de verdad.
    """
    if df is None or df.shape[1] == 0:
        return 0
    if df.shape[0] == 0:
        return 1  # solo encabezados: vale algo, pero no hay datos
    return sum(1 for col in df.columns if not df[col].isna().all())


def load_file_data(file_path):
    """Carga archivos CSV o Excel con deteccion de encoding robusta priorizando UTF-8."""
    import os
    ext = file_path.lower()
    basename = os.path.basename(file_path)

    # Archivo de 0 bytes: se rechaza con un mensaje claro en vez de dejar que pandas
    # reviente con EmptyDataError y acabe en un 500 "revisa el formato".
    try:
        if os.path.getsize(file_path) == 0:
            raise ArchivoInvalido(
                "El archivo esta vacio (0 bytes). Sube un CSV o Excel con al menos una fila de datos."
            )
    except OSError as exc:
        # No se puede leer el tamaño del archivo (permisos, ruta montada que no
        # responde). No es motivo para abortar: la lectura posterior decidirá.
        # P-36: se registra el motivo en vez de ignorarlo en silencio.
        log_ignored_error(
            logger,
            "lectura del tamaño del archivo (0-byte check)",
            exc,
            level=logging.WARNING,
            file=basename,
        )

    try:
        if ext.endswith('.csv'):
            # UTF-8 y UTF-8-sig se priorizan estrictamente antes de latin-1
            encodings = ['utf-8', 'utf-8-sig', 'cp1252', 'iso-8859-1', 'latin-1']
            # Coma primero: la coma nunca aparece dentro de un valor de texto,
            # el punto y coma si (p.ej. cabeceras con SQL injection).
            separators = [',', ';', '\t']

            best_df, best_score = None, 0
            parse_failures = 0
            for encoding in encodings:
                for sep in separators:
                    try:
                        decimal = ',' if sep == ';' else '.'
                        df = pd.read_csv(file_path, encoding=encoding, sep=sep, decimal=decimal)
                    except Exception as exc:
                        # P-36: probar encoding x separador es un barrido a ciegas: la
                        # mayoría de combinaciones FALLAN y eso es lo esperado. Por eso
                        # el fallo individual se registra a nivel DEBUG (ruido) pero se
                        # cuenta, y el total se registra a WARNING si el barrido
                        # entero termina sin éxito.
                        parse_failures += 1
                        log_ignored_error(
                            logger,
                            "parseo CSV (barrido encoding/separador)",
                            exc,
                            level=logging.DEBUG,
                            file=basename,
                            encoding=encoding,
                            sep=sep,
                        )
                        continue
                    score = _parse_score(df)
                    if score > best_score:
                        best_df, best_score = df, score
                if best_score > 1:
                    break  # ya hay un parseo con datos de verdad

            if best_df is not None and best_score > 1:
                logger.debug("CSV cargado file=%s cols_con_datos=%d", basename, best_score)
                return _clean_dataframe(best_df)

            # Ultimo recurso: motor python con deteccion automatica y saltando lineas
            # rotas. Necesario para CSV sucios (comillas sin cerrar, filas partidas):
            # se prueba ANTES de concluir que el archivo solo tiene encabezados.
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding, sep=None, engine='python', on_bad_lines='skip')
                    if _parse_score(df) > 1:
                        logger.info("CSV leido con motor python (lineas dañadas omitidas) file=%s", basename)
                        return _clean_dataframe(df)
                except Exception as exc:
                    # P-36: mismo barrido a ciegas que arriba; el fallo se registra a
                    # DEBUG y el total se resume cuando el barrido no encuentra nada.
                    parse_failures += 1
                    log_ignored_error(
                        logger,
                        "parseo CSV (motor python, fallback)",
                        exc,
                        level=logging.DEBUG,
                        file=basename,
                        encoding=encoding,
                    )
                    continue

            # Ningún parseo funcionó: se deja traza del motivo real antes de
            # devolver el mensaje de usuario. P-36: sin esto el fallo era invisible.
            logger.warning(
                "CSV no parseable file=%s combinaciones_fallidas=%d",
                basename, parse_failures,
            )

            # Solo encabezados o archivo ilegible: se distingue para no culpar al usuario de
            # un problema que no es el suyo (un CSV corrupto no es "solo encabezados").
            if best_df is not None and best_df.shape[1] >= 2 and best_df.shape[0] == 0:
                raise ArchivoInvalido(
                    "El archivo no contiene datos, solo la fila de encabezados. "
                    "Anade al menos una fila con datos."
                )

            raise ArchivoInvalido(
                "No se pudo interpretar el archivo. Comprueba que sea un CSV valido "
                "(separador coma o punto y coma, codificacion UTF-8) y que las "
                "comillas o comas esten bien cerradas."
            )
        elif ext.endswith(('.xls', '.xlsx', '.xlsm')):
            logger.debug("Cargando archivo Excel (Context-safe): file=%s", basename)
            engine = 'openpyxl' if ext.endswith('.xlsx') else None
            
            best_df = None
            max_cells = -1
            
            # Usar 'with' para asegurar que Windows libere el archivo inmediatamente
            with pd.ExcelFile(file_path, engine=engine) as excel_file:
                sheets = excel_file.sheet_names
                for sheet in sheets:
                    try:
                        temp_df = pd.read_excel(excel_file, sheet_name=sheet, header=None)
                        cells_count = temp_df.notnull().sum().sum()
                        logger.debug("Hoja '%s': %d celdas.", sheet, cells_count)
                        
                        if cells_count > max_cells:
                            max_cells = cells_count
                            best_df = temp_df
                    except Exception as sheet_err:
                        logger.debug("Error leyendo hoja '%s': %s", sheet, type(sheet_err).__name__)
                        continue
            
            if best_df is not None:
                return _clean_dataframe(best_df)
            else:
                raise Exception("El archivo Excel parece estar vacío.")
        else:
            # Motor de carga de CSV Ultra-Resiliente (Detección automática)
            logger.debug("Cargando archivo CSV (Auto-Sense): file=%s", basename)
            encodings = ['utf-8-sig', 'utf-8', 'cp1252', 'iso-8859-1', 'latin-1']
            best_df = None
            
            for enc in encodings:
                try:
                    best_df = pd.read_csv(file_path, sep=None, engine='python', encoding=enc)
                    if best_df.shape[1] > 1:
                        break
                except Exception as exc:
                    # P-36: barrido de encodings; el fallo se registra a DEBUG.
                    log_ignored_error(
                        logger,
                        "parseo CSV (auto-sense de encoding)",
                        exc,
                        level=logging.DEBUG,
                        file=basename,
                        encoding=enc,
                    )
                    continue
            
            if best_df is not None:
                return _clean_dataframe(best_df)
            else:
                return _clean_dataframe(pd.read_csv(file_path))
    except ArchivoInvalido:
        # Ya es un mensaje pensado para el usuario final: no lo reenvolvemos.
        raise
    except Exception as e:
        logger.error("Error crítico cargando archivo file=%s: %s", basename, type(e).__name__)
        raise Exception(f"Error al leer el archivo: {type(e).__name__}")


def load_file_data_from_bytes(raw_bytes: bytes, filename: str) -> pd.DataFrame:
    """Carga un CSV o Excel desde bytes en memoria (sin escribir a disco).
    
    Usado para leer archivos cifrados: se descifran en RAM y se parsean
    directamente desde el buffer, nunca tocando el sistema de archivos.
    """
    import io
    basename = filename or "buffer"
    ext = (filename or "").lower()
    try:
        if ext.endswith('.csv'):
            encodings = ['utf-8', 'utf-8-sig', 'cp1252', 'iso-8859-1', 'latin-1']
            separators = [';', ',', '\t']
            parse_failures = 0
            for encoding in encodings:
                for sep in separators:
                    try:
                        decimal = ',' if sep == ';' else '.'
                        df = pd.read_csv(
                            io.BytesIO(raw_bytes),
                            encoding=encoding, sep=sep, decimal=decimal
                        )
                        if len(df.columns) > 1:
                            logger.debug("CSV (bytes) cargado (sep=%r, enc=%s)", sep, encoding)
                            return _clean_dataframe(df)
                    except Exception as exc:
                        # P-36: barrido a ciegas encoding x separador (el fallo es el
                        # caso normal); se registra a DEBUG y se cuenta.
                        parse_failures += 1
                        log_ignored_error(
                            logger,
                            "parseo CSV cifrado (barrido encoding/separador)",
                            exc,
                            level=logging.DEBUG,
                            file=basename,
                            encoding=encoding,
                            sep=sep,
                        )
                        continue
            # Último recurso
            for encoding in encodings:
                try:
                    df = pd.read_csv(io.BytesIO(raw_bytes), encoding=encoding, sep=None, engine='python', on_bad_lines='skip')
                    return _clean_dataframe(df)
                except Exception as exc:
                    parse_failures += 1
                    log_ignored_error(
                        logger,
                        "parseo CSV cifrado (motor python, fallback)",
                        exc,
                        level=logging.DEBUG,
                        file=basename,
                        encoding=encoding,
                    )
                    continue
            logger.warning(
                "CSV cifrado no parseable file=%s combinaciones_fallidas=%d",
                basename, parse_failures,
            )
            raise Exception("No se pudo determinar el formato del CSV cifrado.")
        elif ext.endswith(('.xls', '.xlsx', '.xlsm')):
            engine = 'openpyxl' if ext.endswith('.xlsx') else None
            best_df = None
            max_cells = -1
            with pd.ExcelFile(io.BytesIO(raw_bytes), engine=engine) as excel_file:
                for sheet in excel_file.sheet_names:
                    try:
                        temp_df = pd.read_excel(excel_file, sheet_name=sheet, header=None)
                        cells_count = temp_df.notnull().sum().sum()
                        if cells_count > max_cells:
                            max_cells = cells_count
                            best_df = temp_df
                    except Exception as exc:
                        # P-36: una hoja ilegible no invalida el resto del Excel.
                        log_ignored_error(
                            logger,
                            "lectura de una hoja de Excel cifrado",
                            exc,
                            level=logging.WARNING,
                            file=basename,
                            sheet=sheet,
                        )
                        continue
            if best_df is not None:
                return _clean_dataframe(best_df)
            raise Exception("El archivo Excel cifrado parece estar vacío.")
        else:
            # Fallback: intentar como CSV
            for encoding in ['utf-8-sig', 'utf-8', 'cp1252', 'latin-1']:
                try:
                    df = pd.read_csv(io.BytesIO(raw_bytes), sep=None, engine='python', encoding=encoding)
                    if df.shape[1] > 1:
                        return _clean_dataframe(df)
                except Exception as exc:
                    # P-36: barrido de encodings; el fallo individual se registra.
                    log_ignored_error(
                        logger,
                        "parseo CSV cifrado (fallback de formato)",
                        exc,
                        level=logging.DEBUG,
                        file=basename,
                        encoding=encoding,
                    )
                    continue
            raise Exception("Formato de archivo cifrado no reconocido.")
    except Exception as e:
        logger.error("Error crítico cargando bytes file=%s: %s", basename, type(e).__name__)
        raise Exception(f"Error al leer el archivo cifrado: {type(e).__name__}")


def load_source_df(file_path: str, is_encrypted: bool, filename: str, nrows: Optional[int] = None) -> pd.DataFrame:
    """Carga un DataFrame desde la ruta física de un DataSource respetando el cifrado.

    - Si `is_encrypted`, descifra en memoria (Fernet) y parsea desde el buffer,
      sin escribir el contenido descifrado a disco.
    - `nrows` limita las filas leídas para previews/contexto (p. ej. simulador).
    """
    import io
    lower = (file_path or "").lower()
    if is_encrypted:
        from src.utils.security import decrypt_file_to_bytes
        raw = decrypt_file_to_bytes(file_path)
        if nrows is not None:
            if lower.endswith('.csv'):
                return pd.read_csv(io.BytesIO(raw), nrows=nrows)
            return pd.read_excel(io.BytesIO(raw), nrows=nrows)
        return load_file_data_from_bytes(raw, filename)

    if nrows is not None:
        if lower.endswith('.csv'):
            return pd.read_csv(file_path, nrows=nrows)
        return pd.read_excel(file_path, nrows=nrows)
    return load_file_data(file_path)


def load_gsheets_data(gs_url):
    """Carga datos de una URL pública de Google Sheets y limpia los nombres de columnas."""
    try:
        match_id = re.search(r"/d/([a-zA-Z0-9-_]+)", gs_url)
        if not match_id:
            logger.warning("GSheets: Sheet ID no encontrado en URL.")
            return None
        
        sheet_id = match_id.group(1)
        match_gid = re.search(r"gid=([0-9]+)", gs_url)
        gid = match_gid.group(1) if match_gid else "0"
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        
        # Intento 1: Export CSV
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
        logger.debug("GSheets: intentando export (attempt=1)")
        response = requests.get(csv_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            from io import StringIO
            df = pd.read_csv(StringIO(response.text))
            return _clean_dataframe(df)
        
        logger.debug("GSheets: Intento 1 falló status=%d. Probando alternativa...", response.status_code)
        
        # Intento 2: Formato pub
        pub_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/pub?output=csv&gid={gid}"
        logger.debug("GSheets: intentando pub (attempt=2)")
        response = requests.get(pub_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            from io import StringIO
            df = pd.read_csv(StringIO(response.text))
            return _clean_dataframe(df)

        # Intento 3: Gviz Visualization API
        gviz_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={gid}"
        logger.debug("GSheets: intentando gviz (attempt=3)")
        response = requests.get(gviz_url, headers=headers, timeout=10)

        if response.status_code == 200:
            from io import StringIO
            df = pd.read_csv(StringIO(response.text))
            return _clean_dataframe(df)
            
        status = response.status_code
        error_context = "Acceso Denegado (401/403)" if status in [401, 403] else f"Error {status}"
        
        help_msg = f"""
        Google rechazó la conexión ({error_context}). 
        
        Sigue estos pasos EXACTOS en tu Google Sheet:
        1. Botón 'Compartir' (arriba a la derecha).
        2. En 'Acceso general', cambia a 'Cualquier persona con el enlace'.
        3. Asegúrate de que diga 'Lector'.
        4. Copia el ENLACE de la barra de direcciones y pégalo aquí de nuevo.
        """
        logger.debug("GSheets: fallaron todos los intentos con status=%d", status)
        raise Exception(help_msg.strip())
        
    except Exception as e:
        if "HTTP" in str(e) or "Google rechazó" in str(e):
            raise e
        logger.error("GSheets: excepción inesperada: %s", type(e).__name__)
        raise Exception("Error técnico al conectar con Google Sheets. Verifica que el documento sea público.")
