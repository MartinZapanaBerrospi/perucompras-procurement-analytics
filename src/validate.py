"""Exactitud: compara los montos calculados con las cifras oficiales de Perú Compras.

Las cifras salen de los boletines estadísticos (2022, 2023) y de las Infocifras (2024, 2025) que
están en docs/fuentes/, transcritas en data/reference/cifras_oficiales.csv. La definición
oficial incluye todas las órdenes formalizadas, así que aquí no se excluye ningún estado.
"""

import pandas as pd

from src import config

PROCEDURE_KEY = {"Gran Compra": "gran_compra", "Compra ordinaria": "compra_ordinaria"}


def computed_by_year(orders: pd.DataFrame) -> pd.DataFrame:
    """Monto y órdenes por año y concepto (bienes, gran_compra, compra_ordinaria)."""
    by_year = orders.assign(anio=orders["fecha_formalizacion"].dt.year)
    per_procedure = (by_year.assign(concepto=by_year["tipo_procedimiento"].map(PROCEDURE_KEY))
                     .groupby(["anio", "concepto"]).agg(monto=("total", "sum"), ordenes=("orden", "size")))
    total = by_year.groupby("anio").agg(monto=("total", "sum"), ordenes=("orden", "size"))
    total["concepto"] = "bienes"
    return pd.concat([per_procedure.reset_index(), total.reset_index()], ignore_index=True)


def compare(orders: pd.DataFrame) -> pd.DataFrame:
    official = pd.read_csv(config.OFFICIAL)
    merged = official.merge(computed_by_year(orders), on=["anio", "concepto"], how="left")
    rows = []
    for r in merged.itertuples():
        rows.append({"anio": r.anio, "concepto": r.concepto, "medida": "monto_soles",
                     "oficial": r.monto_soles, "calculado": round(r.monto, 2), "fuente": r.fuente})
        if pd.notna(r.ordenes_x):
            rows.append({"anio": r.anio, "concepto": r.concepto, "medida": "ordenes",
                         "oficial": r.ordenes_x, "calculado": r.ordenes_y, "fuente": r.fuente})
    out = pd.DataFrame(rows)
    out["diferencia_pct"] = (100 * (out["calculado"] / out["oficial"] - 1)).round(3)
    out["tolerancia_pct"] = 100 * config.OFFICIAL_TOLERANCE
    out["resultado"] = out["diferencia_pct"].abs().le(out["tolerancia_pct"]).map({True: "cumple", False: "falla"})
    return out
