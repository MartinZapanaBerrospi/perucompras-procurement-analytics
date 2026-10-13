"""Lectura de los CSV de órdenes de compra y reglas de limpieza a nivel de campo.

Cada función resuelve un problema del catálogo de la Fase 2 (docs/02_calidad.md); el número del
problema va en el comentario. La Fase 2 las usa para medir la calidad y la Fase 3 para construir
el modelo, así que las dos fases aplican exactamente las mismas reglas.
"""

import csv
import io
import re
import unicodedata
from pathlib import Path

import pandas as pd

# Nombre en el archivo -> nombre en el proyecto. El diccionario oficial llama DOCUMENTO_ESTADO a
# la columna que en los archivos es DOCUMENTO_ESTADO_OCAM (problema 3).
COLUMNS = {
    "FECHA_PROCESO": "fecha_proceso",
    "RUC_PROVEEDOR": "ruc_proveedor",
    "PROVEEDOR": "proveedor",
    "RUC_ENTIDAD": "ruc_entidad",
    "ENTIDAD": "entidad",
    "TIPO_PROCEDIMIENTO": "tipo_procedimiento",
    "ORDEN_ELECTRÓNICA": "orden",
    "ORDEN_ELECTRÓNICA_GENERADA": "url_orden",
    "ESTADO_ORDEN_ELECTRÓNICA": "estado",
    "DOCUMENTO_ESTADO_OCAM": "url_documento_estado",
    "FECHA_FORMALIZACIÓN": "fecha_formalizacion",
    "FECHA_ÚLTIMO_ESTADO": "fecha_ultimo_estado",
    "SUB_TOTAL": "sub_total",
    "IGV": "igv",
    "TOTAL": "total",
    "ORDEN_DIGITALIZADA": "url_orden_digitalizada",
    "DESCRIPCIÓN_ESTADO": "descripcion_estado",
    "DESCRIPCIÓN_CESIÓN_DERECHOS": "descripcion_cesion_derechos",
    "ACUERDO_MARCO": "acuerdo_marco",
}
DATE_COLUMNS = ["fecha_proceso", "fecha_formalizacion", "fecha_ultimo_estado"]
AMOUNT_COLUMNS = ["sub_total", "igv", "total"]
RUC_WEIGHTS = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
FRAMEWORK_RE = re.compile(r"^(?P<codigo>(?:IM|EXT)-CE-\d{4}-\d+)?\s*(?P<nombre>.*)$")


def decode(content: bytes) -> tuple[str, str]:
    """Problema 1: 56 meses vienen en Windows-1252 y uno (2024-03) en UTF-8."""
    try:
        text, encoding = content.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        text, encoding = content.decode("cp1252"), "cp1252"
    return text.lstrip("﻿"), encoding


def read_raw(path: Path) -> pd.DataFrame:
    """Lee un CSV mensual tal como viene: todo como texto, sin interpretar comillas ni nulos.

    Ningún archivo usa comillas y ningún campo contiene ';', así que QUOTE_NONE reproduce
    exactamente la estructura del archivo.
    """
    text, _ = decode(path.read_bytes())
    df = pd.read_csv(io.StringIO(text), sep=";", dtype=str, keep_default_na=False,
                     quoting=csv.QUOTE_NONE)
    unknown = set(df.columns) - set(COLUMNS)
    if unknown:
        raise ValueError(f"{path.name}: columnas no reconocidas {sorted(unknown)}")
    return df.rename(columns=COLUMNS)


def strip_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Problema 2: en 2024-03 todos los campos empiezan con un tabulador; además hay espacios al
    final en nombres y acuerdos marco. Se quitan los espacios de los extremos y se colapsan los
    espacios repetidos."""
    return df.apply(lambda s: s.str.replace(r"\s+", " ", regex=True).str.strip())


def parse_date(values: pd.Series) -> pd.Series:
    """Problema 4: 56 meses usan 'AAAA-MM-DD hh:mm:ss' y 2024-06 usa 'D/MM/AAAA hh:mm'."""
    iso = pd.to_datetime(values, format="%Y-%m-%d %H:%M:%S", errors="coerce")
    dmy = pd.to_datetime(values, format="%d/%m/%Y %H:%M", errors="coerce")
    return iso.fillna(dmy)


def parse_amount(values: pd.Series) -> pd.Series:
    """Montos en soles con punto decimal. Lo que no sea número queda vacío y se cuenta en la Fase 2."""
    return pd.to_numeric(values, errors="coerce")


def ruc_is_valid(ruc: str) -> bool:
    """RUC de 11 dígitos con dígito verificador correcto (módulo 11, pesos de la SUNAT)."""
    if len(ruc) != 11 or not ruc.isdigit():
        return False
    check = 11 - sum(int(d) * w for d, w in zip(ruc[:10], RUC_WEIGHTS)) % 11
    return {10: 0, 11: 1}.get(check, check) == int(ruc[10])


def normalize_text(value: str) -> str:
    """Mayúsculas, sin tildes y con espacios simples: la clave para comparar nombres que la fuente
    escribe de varias formas (problema 6)."""
    plain = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", plain).strip().upper()


def split_framework(value: str) -> tuple[str, str]:
    """Problema 6: hasta 2024-05 el acuerdo marco trae su código ('EXT-CE-2021-6 IMPRESORAS…');
    desde 2024-06, solo el nombre. Devuelve (código o '', nombre)."""
    match = FRAMEWORK_RE.match(value.strip())
    return match.group("codigo") or "", match.group("nombre").strip()
