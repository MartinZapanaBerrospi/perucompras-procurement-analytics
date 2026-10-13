"""Pruebas de la comparación con cifras oficiales."""

import pandas as pd

from src import config, validate


def orders():
    return pd.DataFrame({
        "orden": ["a", "b", "c"],
        "tipo_procedimiento": ["Gran Compra", "Compra ordinaria", "Compra ordinaria"],
        "fecha_formalizacion": pd.to_datetime(["2023-03-01", "2023-05-01", "2024-01-01"]),
        "total": [100.0, 50.0, 10.0],
    })


def test_agrega_por_anio_y_tipo_de_procedimiento():
    out = validate.computed_by_year(orders()).set_index(["anio", "concepto"])
    assert out.loc[(2023, "bienes"), "monto"] == 150
    assert out.loc[(2023, "gran_compra"), "ordenes"] == 1
    assert out.loc[(2024, "compra_ordinaria"), "monto"] == 10


def test_marca_falla_fuera_de_tolerancia(tmp_path, monkeypatch):
    official = tmp_path / "oficial.csv"
    official.write_text("anio,concepto,monto_soles,ordenes,fuente,ubicacion\n"
                        "2023,bienes,150,2,x,x\n2023,gran_compra,120,,x,x\n", encoding="utf-8")
    monkeypatch.setattr(config, "OFFICIAL", official)
    out = validate.compare(orders()).set_index(["concepto", "medida"])
    assert out.loc[("bienes", "monto_soles"), "resultado"] == "cumple"
    assert out.loc[("bienes", "ordenes"), "resultado"] == "cumple"
    assert out.loc[("gran_compra", "monto_soles"), "resultado"] == "falla"


def test_cifras_oficiales_cubren_2022_a_2025():
    official = pd.read_csv(config.OFFICIAL)
    assert set(official["anio"]) == {2022, 2023, 2024, 2025}
    bienes = official[official["concepto"] == "bienes"].set_index("anio")["monto_soles"]
    parts = official[official["concepto"] != "bienes"].groupby("anio")["monto_soles"].sum()
    # En cada año, Gran Compra + Compra ordinaria = bienes (±S/ 0,01 millones por redondeo)
    assert ((bienes - parts).abs() <= 10_000).all()
