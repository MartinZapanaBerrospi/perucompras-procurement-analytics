"""Pruebas del modelo en estrella versionado en data/curated (lo que lee Power BI)."""

import pandas as pd
import pytest

from src import config, transform, validate


@pytest.fixture(scope="module")
def tables():
    names = ["fact_orden", "dim_entidad", "dim_proveedor", "dim_catalogo", "dim_estado", "dim_fecha"]
    return {n: pd.read_csv(config.CURATED / f"{n}.csv", dtype={"ruc_entidad": str, "ruc_proveedor": str})
            for n in names}


def test_integridad_referencial_y_claves(tables):
    assert transform.check_integrity(tables) == []


def test_el_hecho_tiene_todas_las_ordenes_y_todo_el_monto(tables):
    lineage = pd.read_csv(config.REPORTS / "linaje.csv").set_index("paso")
    fact = tables["fact_orden"]
    assert len(fact) == lineage.loc["1. raw", "filas"] == 511_782
    assert abs(fact["total"].sum() - lineage.loc["1. raw", "monto"]) < 0.05


def test_coincide_con_las_cifras_oficiales():
    result = validate.compare(validate.from_curated())
    assert (result["resultado"] == "cumple").all(), result[result["resultado"] != "cumple"]


def test_marcas_coherentes_con_los_montos(tables):
    fact = tables["fact_orden"]
    assert (fact.loc[fact["igv_exonerado"] == 1, "igv"] == 0).all()
    assert not ((fact["igv_exonerado"] == 1) & (fact["igv_parcial"] == 1)).any()
    over = fact["ordinaria_sobre_umbral"] == 1
    assert (fact.loc[over, "gran_compra"] == 0).all()
    assert (fact.loc[over, "total"] >= config.GRAN_COMPRA_THRESHOLD).all()
    assert fact.loc[fact["atipico_alto"] == 1, "total"].min() > fact.loc[fact["atipico_alto"] == 0, "total"].max() * 0.99


def test_nombres_unicos_para_el_tablero(tables):
    assert tables["dim_entidad"]["entidad_unica"].is_unique
    assert tables["dim_proveedor"]["proveedor_unico"].is_unique
    shared = tables["dim_entidad"][tables["dim_entidad"]["entidad_unica"].str.contains("(RUC ", regex=False)]
    assert len(shared) > 0  # los nombres compartidos (p. ej. Miraflores) llevan su RUC


def test_calendario_cubre_el_periodo(tables):
    dates = tables["dim_fecha"]["fecha"]
    assert dates.min() == "2022-01-01" and dates.max() == "2026-09-30"
    assert len(dates) == (pd.Timestamp("2026-09-30") - pd.Timestamp("2022-01-01")).days + 1


def test_catalogos_y_rubros(tables):
    catalogs = tables["dim_catalogo"]
    assert len(catalogs) == 29
    assert catalogs["rubro"].nunique() == 10


def test_unique_label_agrega_el_ruc_solo_si_hace_falta():
    dim = pd.DataFrame({"ruc": ["1", "2", "3"], "nombre": ["MIRAFLORES", "MIRAFLORES", "SUNAT"]})
    assert transform.unique_label(dim, "ruc", "nombre").tolist() == [
        "MIRAFLORES (RUC 1)", "MIRAFLORES (RUC 2)", "SUNAT"]


def test_latest_names_usa_el_nombre_mas_reciente():
    df = pd.DataFrame({
        "ruc": ["20266352337", "20266352337"],
        "nombre": ["PRODUCTOS TISSUE DEL PERU S.A.C", "SOFTYS PERU S.A.C."],
        "fecha_formalizacion": pd.to_datetime(["2022-01-10", "2025-03-01"]),
        "orden": ["a", "b"],
    })
    out = transform.latest_names(df, "ruc", "nombre")
    assert out.loc[0, "nombre"] == "SOFTYS PERU S.A.C."
    assert out.loc[0, "nombres_historicos"] == 2
