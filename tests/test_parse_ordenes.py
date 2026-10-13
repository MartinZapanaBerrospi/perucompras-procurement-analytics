"""Pruebas de las reglas de limpieza con recortes reales de los archivos más difíciles.

- ordenes_2022-01_recorte.csv: Windows-1252, con tildes en el acuerdo marco y su código.
- ordenes_2024-03_recorte.csv: UTF-8, fin de línea CRLF y un tabulador al inicio de cada campo.
- ordenes_2024-06_recorte.csv: fechas 'D/MM/AAAA hh:mm', con días de uno y dos dígitos.
"""

from pathlib import Path

import pandas as pd
import pytest

from src import config
from src.parse_ordenes import (COLUMNS, decode, normalize_text, parse_date, read_raw, ruc_is_valid,
                               split_framework, strip_fields)
from src.quality import is_empty, spelling_key

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(period: str) -> Path:
    return FIXTURES / f"ordenes_{period}_recorte.csv"


@pytest.mark.parametrize("period, encoding", [("2022-01", "cp1252"), ("2024-03", "utf-8"), ("2024-06", "cp1252")])
def test_detecta_la_codificacion(period, encoding):
    _, detected = decode(fixture(period).read_bytes())
    assert detected == encoding


@pytest.mark.parametrize("period", ["2022-01", "2024-03", "2024-06"])
def test_lee_las_19_columnas_con_nombres_del_proyecto(period):
    df = read_raw(fixture(period))
    assert list(df.columns) == list(COLUMNS.values())
    assert len(df) == 3


def test_las_tildes_sobreviven_en_windows_1252():
    df = read_raw(fixture("2022-01"))
    assert "PORTÁTILES" in df["acuerdo_marco"].iloc[0]


def test_quita_los_tabuladores_de_2024_03():
    raw = read_raw(fixture("2024-03"))
    assert raw["estado"].str.startswith("\t").all()
    clean = strip_fields(raw)
    assert clean["estado"].isin(config.VALID_STATES).all()
    assert clean["ruc_proveedor"].str.fullmatch(r"\d{11}").all()
    assert not clean.apply(lambda s: s.str.contains("\t", regex=False)).to_numpy().any()


def test_fechas_de_2024_06_se_leen_dia_mes():
    df = strip_fields(read_raw(fixture("2024-06")))
    dates = parse_date(df["fecha_formalizacion"])
    assert dates.tolist() == [pd.Timestamp("2024-06-30 23:05"), pd.Timestamp("2024-06-03 23:57"),
                              pd.Timestamp("2024-06-10 23:55")]


def test_fechas_iso_con_segundos():
    df = strip_fields(read_raw(fixture("2024-03")))
    assert parse_date(df["fecha_formalizacion"]).notna().all()


@pytest.mark.parametrize("ruc, valid", [
    ("20131312955", True),     # SUNAT
    ("20100003351", True),     # proveedor real de los archivos
    ("20131312956", False),    # dígito verificador alterado
    ("2013131295", False),     # 10 dígitos
    ("2013131295A", False),
])
def test_ruc_con_digito_verificador(ruc, valid):
    assert ruc_is_valid(ruc) is valid


@pytest.mark.parametrize("value, code, name", [
    ("EXT-CE-2021-6 IMPRESORAS, CONSUMIBLES", "EXT-CE-2021-6", "IMPRESORAS, CONSUMIBLES"),
    ("IM-CE-2020-5 COMPUTADORAS DE ESCRITORIO", "IM-CE-2020-5", "COMPUTADORAS DE ESCRITORIO"),
    ("BIENES Y HERRAMIENTAS PARA USOS DIVERSOS", "", "BIENES Y HERRAMIENTAS PARA USOS DIVERSOS"),
])
def test_separa_codigo_y_nombre_del_acuerdo_marco(value, code, name):
    assert split_framework(value) == (code, name)


def test_normaliza_tildes_y_espacios():
    assert normalize_text("Baterías,  pilas y accesorios ") == "BATERIAS, PILAS Y ACCESORIOS"


def test_catalogo_de_referencia_coherente():
    catalogs = pd.read_csv(config.CATALOGS)
    assert catalogs["clave_normalizada"].is_unique
    assert (catalogs["clave_normalizada"].map(normalize_text) == catalogs["clave_normalizada"]).all()
    assert catalogs[["catalogo", "rubro"]].notna().all().all()


@pytest.mark.parametrize("period", ["2022-01", "2024-03", "2024-06"])
def test_los_acuerdos_de_los_recortes_tienen_catalogo(period):
    keys = set(pd.read_csv(config.CATALOGS)["clave_normalizada"])
    df = strip_fields(read_raw(fixture(period)))
    found = df["acuerdo_marco"].map(lambda v: normalize_text(split_framework(v)[1]))
    assert found.isin(keys).all()


def test_vacio_con_el_tipo_de_texto_de_pandas_3():
    values = pd.Series(["a", "", "  "]).str.strip()
    assert is_empty(values).tolist() == [False, True, True]
    assert is_empty(pd.Series([1.0, None])).tolist() == [False, True]


def test_variantes_de_escritura_de_un_nombre():
    assert spelling_key("EMPRESA DE ELECTRICIDAD DEL PERÚ S.A.") == spelling_key("Empresa de Electricidad del Peru SA")
    assert spelling_key("SOFTYS PERU S.A.C.") != spelling_key("PRODUCTOS TISSUE DEL PERU S.A.C")
