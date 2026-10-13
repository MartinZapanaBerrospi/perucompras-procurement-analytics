"""Las cifras del análisis (Fase 5) son las mismas que muestra el tablero (medidas DAX)."""

import pandas as pd
import pytest

from src import config

ANALYSIS = config.REPORTS / "analisis"


@pytest.fixture(scope="module")
def dax():
    d = pd.read_csv(config.REPORTS / "medidas_dax.csv", dtype=str)
    d.columns = [c.strip("[]") for c in d.columns]
    d["valor"] = pd.to_numeric(d["valor"].str.replace(",", ".", regex=False), errors="coerce")
    return d.set_index(["contexto", "clave", "medida"])["valor"]


@pytest.fixture(scope="module")
def key():
    k = pd.read_csv(ANALYSIS / "cifras_clave.csv")
    return k.set_index("cifra")["valor"]


@pytest.mark.parametrize("column, measure", [
    ("hhi", "HHI"),
    ("proveedores_80", "Proveedores para el 80 %"),
    ("participacion_top3", "Participación top 3 proveedores"),
    ("participacion_lider", "Participación del líder"),
    ("monto", "Monto"),
])
def test_concentracion_por_catalogo_igual_al_tablero(dax, column, measure):
    catalogs = pd.read_csv(ANALYSIS / "p2_catalogos.csv")
    for row in catalogs.itertuples():
        assert getattr(row, column) == pytest.approx(dax[("catalogo", row.catalogo, measure)], rel=1e-9), row.catalogo


def test_cifras_anuales_iguales_al_tablero(dax):
    annual = pd.read_csv(ANALYSIS / "p1_anual.csv", index_col="anio")
    for year, row in annual.iterrows():
        assert row["monto"] == pytest.approx(dax[("anio", str(year), "Monto")], rel=1e-9)
        assert row["ordenes"] == dax[("anio", str(year), "Órdenes")]


def test_cifras_clave_coherentes(key, dax):
    lineage = pd.read_csv(config.REPORTS / "linaje.csv").set_index("paso")
    assert float(key["monto_total"]) == pytest.approx(lineage.loc["1. raw", "monto"], abs=0.05)
    assert float(key["var_ene_set_2026"]) == pytest.approx(dax[("anio", "2026", "Var. interanual")], rel=1e-9)
    assert float(key["pct_gran_compra_2025"]) == pytest.approx(dax[("anio", "2025", "% Gran Compra")], rel=1e-9)
    assert int(float(key["ordinarias_sobre_umbral"])) == dax[("global", "total", "Órdenes ordinarias sobre el umbral")]


def test_el_umbral_muestra_el_amontonamiento(key):
    hist = pd.read_csv(ANALYSIS / "p5_umbral_histograma.csv")
    just_below = hist.loc[hist["desde"] == 99_000, "ordenes"].item()
    just_above = hist.loc[hist["desde"] == 100_000, "ordenes"].item()
    assert just_below > 2 * float(key["promedio_tramos_vecinos_90_99k"])
    assert just_above < just_below / 5


def test_posible_fraccionamiento_cumple_su_definicion():
    split = pd.read_csv(ANALYSIS / "p5_posible_fraccionamiento.csv")
    assert (split["ordenes"] >= 2).all()
    assert (split["monto"] >= config.GRAN_COMPRA_THRESHOLD).all()
    assert (split["mayor"] < config.GRAN_COMPRA_THRESHOLD).all()
