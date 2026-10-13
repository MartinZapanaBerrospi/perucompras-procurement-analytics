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


def from_curated() -> pd.DataFrame:
    """Las órdenes del modelo curado, con las columnas que usa compare()."""
    fact = pd.read_csv(config.CURATED / "fact_orden.csv", usecols=["orden", "fecha", "gran_compra", "total"],
                       parse_dates=["fecha"])
    return pd.DataFrame({
        "orden": fact["orden"],
        "fecha_formalizacion": fact["fecha"],
        "tipo_procedimiento": fact["gran_compra"].map({1: "Gran Compra", 0: "Compra ordinaria"}),
        "total": fact["total"],
    })


def main() -> int:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    result = compare(from_curated())
    config.REPORTS.mkdir(parents=True, exist_ok=True)
    result.to_csv(config.REPORTS / "validaciones.csv", index=False)
    print(result[["anio", "concepto", "medida", "oficial", "calculado", "diferencia_pct", "resultado"]].to_string(index=False))
    failed = result[result["resultado"] != "cumple"]
    return 1 if len(failed) else 0


if __name__ == "__main__":
    raise SystemExit(main())
