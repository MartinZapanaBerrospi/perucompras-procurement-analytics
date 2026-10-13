"""Fase 5 — Responde las preguntas P1 a P5′ con cifras, desde el modelo curado.

Escribe una tabla por pregunta en reports/analisis/ y las cifras clave que cita el README en
reports/analisis/cifras_clave.csv. Todas las comparaciones entre 2026 y años anteriores usan
enero–setiembre, porque 2026 llega hasta setiembre.

Uso:
    python -m src.analysis
"""

import sys

import numpy as np
import pandas as pd

from src import config

OUT = config.REPORTS / "analisis"
LAST_FULL_YEAR = 2025
CUTOFF_MONTH = config.END[1]          # 9: setiembre
BIG_CATALOG_SHARE = 0.03              # catálogos "grandes": al menos 3 % del monto del periodo


def load() -> pd.DataFrame:
    c = config.CURATED
    fact = pd.read_csv(c / "fact_orden.csv", dtype={"ruc_entidad": str, "ruc_proveedor": str}, parse_dates=["fecha"])
    catalogs = pd.read_csv(c / "dim_catalogo.csv")[["catalogo_id", "catalogo", "rubro"]]
    entities = pd.read_csv(c / "dim_entidad.csv", dtype={"ruc_entidad": str})[["ruc_entidad", "entidad_unica"]]
    providers = pd.read_csv(c / "dim_proveedor.csv", dtype={"ruc_proveedor": str})[["ruc_proveedor", "proveedor_unico"]]
    fact = fact.merge(catalogs, on="catalogo_id").merge(entities, on="ruc_entidad").merge(providers, on="ruc_proveedor")
    fact["anio"] = fact["fecha"].dt.year
    fact["mes"] = fact["fecha"].dt.month
    return fact


def concentration(d: pd.DataFrame) -> pd.Series:
    """HHI, proveedores, top 3, líder y proveedores para el 80 % (misma definición que la medida DAX)."""
    by_provider = d.groupby("ruc_proveedor")["total"].sum().sort_values(ascending=False)
    total = by_provider.sum()
    shares = by_provider / total
    before = by_provider.cumsum() - by_provider            # monto de los mayores (sin empates en la práctica)
    hhi = float(((shares * 100) ** 2).sum())
    return pd.Series({
        "monto": total,
        "proveedores": len(by_provider),
        "hhi": hhi,
        "nivel": "Baja" if hhi < 1500 else "Moderada" if hhi < 2500 else "Alta",
        "participacion_top3": shares.head(3).sum(),
        "participacion_lider": shares.iloc[0],
        "proveedores_80": int((before < 0.8 * total).sum()),
    })


# ---------------------------------------------------------------------------------------------
# P1. Cuánto, en qué y cómo cambia
# ---------------------------------------------------------------------------------------------

def p1(d: pd.DataFrame) -> dict:
    annual = d.groupby("anio").agg(monto=("total", "sum"), ordenes=("total", "size"), ticket_promedio=("total", "mean"),
                                    ticket_mediano=("total", "median"), entidades=("ruc_entidad", "nunique"),
                                    proveedores=("ruc_proveedor", "nunique"))
    annual["pct_ordenes_menores_1000"] = d.assign(s=d["total"] < 1000).groupby("anio")["s"].mean()
    annual["periodo"] = np.where(annual.index <= LAST_FULL_YEAR, "año completo", "enero–setiembre")

    comparable = d[d["mes"] <= CUTOFF_MONTH].groupby("anio").agg(
        monto=("total", "sum"), ordenes=("total", "size"), proveedores=("ruc_proveedor", "nunique"),
        entidades=("ruc_entidad", "nunique"))
    comparable["var_monto"] = comparable["monto"].pct_change()

    full = d[d["anio"] <= LAST_FULL_YEAR]
    rubros = full.pivot_table(index="rubro", columns="anio", values="total", aggfunc="sum")
    rubros = rubros / rubros.sum()
    rubros["periodo_completo"] = d.groupby("rubro")["total"].sum() / d["total"].sum()
    rubros = rubros.sort_values("periodo_completo", ascending=False)

    annual.to_csv(OUT / "p1_anual.csv")
    comparable.to_csv(OUT / "p1_enero_setiembre.csv")
    rubros.to_csv(OUT / "p1_rubros.csv")

    first, last = annual.loc[2022], annual.loc[LAST_FULL_YEAR]
    top2 = rubros["periodo_completo"].head(2)
    return {
        "monto_total": d["total"].sum(),
        "ordenes_total": len(d),
        "monto_2022": first["monto"], "monto_2025": last["monto"],
        "var_monto_2022_2025": last["monto"] / first["monto"] - 1,
        "var_ordenes_2022_2025": last["ordenes"] / first["ordenes"] - 1,
        "ticket_mediano_2022": first["ticket_mediano"], "ticket_mediano_2025": last["ticket_mediano"],
        "monto_ene_set_2026": comparable.loc[2026, "monto"],
        "var_ene_set_2026": comparable.loc[2026, "var_monto"],
        "rubros_top2": " y ".join(top2.index), "participacion_rubros_top2": top2.sum(),
    }


# ---------------------------------------------------------------------------------------------
# P2. Concentración por catálogo
# ---------------------------------------------------------------------------------------------

def p2(d: pd.DataFrame) -> dict:
    catalogs = d.groupby(["catalogo", "rubro"]).apply(concentration, include_groups=False).reset_index()
    catalogs["participacion_monto"] = catalogs["monto"] / catalogs["monto"].sum()
    catalogs = catalogs.sort_values("monto", ascending=False)
    catalogs.to_csv(OUT / "p2_catalogos.csv", index=False)

    big = catalogs.loc[catalogs["participacion_monto"] >= BIG_CATALOG_SHARE, "catalogo"]
    comparable = d[(d["mes"] <= CUTOFF_MONTH) & d["catalogo"].isin(big)]
    trend = comparable.groupby(["catalogo", "anio"]).apply(concentration, include_groups=False).reset_index()
    trend.to_csv(OUT / "p2_catalogos_grandes_enero_setiembre.csv", index=False)

    providers = d[d["mes"] <= CUTOFF_MONTH].groupby("anio")["ruc_proveedor"].nunique()
    moderate_or_high = catalogs[catalogs["nivel"] != "Baja"]
    pivot = trend.pivot(index="catalogo", columns="anio", values="proveedores")
    return {
        "catalogos_grandes": len(big),
        "participacion_catalogos_grandes": catalogs.loc[catalogs["catalogo"].isin(big), "participacion_monto"].sum(),
        "hhi_max_catalogos_grandes": catalogs.loc[catalogs["catalogo"].isin(big), "hhi"].max(),
        "catalogos_concentrados": len(moderate_or_high),
        "participacion_catalogos_concentrados": moderate_or_high["participacion_monto"].sum(),
        "proveedores_ene_set_2022": providers.loc[2022], "proveedores_ene_set_2026": providers.loc[2026],
        "var_proveedores_ene_set_2022_2026": providers.loc[2026] / providers.loc[2022] - 1,
        "proveedores_impresoras_2022": pivot.loc["Impresoras y consumibles", 2022],
        "proveedores_impresoras_2026": pivot.loc["Impresoras y consumibles", 2026],
    }


# ---------------------------------------------------------------------------------------------
# P3. Entidades
# ---------------------------------------------------------------------------------------------

def p3(d: pd.DataFrame) -> dict:
    g = d.groupby(["ruc_entidad", "entidad_unica"]).agg(monto=("total", "sum"), ordenes=("total", "size"),
                                                         catalogos=("catalogo_id", "nunique")).reset_index()
    g = g.sort_values("monto", ascending=False).reset_index(drop=True)
    g["participacion"] = g["monto"] / g["monto"].sum()
    g["acumulado"] = g["participacion"].cumsum()
    g.head(30).to_csv(OUT / "p3_entidades_top30.csv", index=False)
    n50 = int((g["acumulado"] < 0.5).sum()) + 1
    n80 = int((g["acumulado"] < 0.8).sum()) + 1
    yearly = d[d["anio"] <= LAST_FULL_YEAR].groupby(["anio", "ruc_entidad"])["total"].sum()
    return {
        "entidades": len(g),
        "entidades_para_50": n50, "pct_entidades_para_50": n50 / len(g),
        "entidades_para_80": n80, "pct_entidades_para_80": n80 / len(g),
        "entidad_lider": g.loc[0, "entidad_unica"], "monto_entidad_lider": g.loc[0, "monto"],
        "participacion_entidad_lider": g.loc[0, "participacion"],
        "gasto_anual_mediano_entidad_2025": yearly.loc[LAST_FULL_YEAR].median(),
    }


# ---------------------------------------------------------------------------------------------
# P4. Calendario
# ---------------------------------------------------------------------------------------------

def p4(d: pd.DataFrame) -> dict:
    full = d[d["anio"] <= LAST_FULL_YEAR]
    months = full.pivot_table(index="mes", columns="anio", values="total", aggfunc="sum")
    months = months / months.sum()
    months["promedio"] = months.mean(axis=1)
    months.to_csv(OUT / "p4_estacionalidad.csv")
    q4 = full[full["mes"] >= 10].groupby("anio")["total"].sum() / full.groupby("anio")["total"].sum()
    last_days = full[(full["mes"] == 12) & (full["fecha"].dt.day >= 22)].groupby("anio")["total"].sum() \
        / full.groupby("anio")["total"].sum()
    return {
        "participacion_t4_min": q4.min(), "participacion_t4_max": q4.max(), "participacion_t4_prom": q4.mean(),
        "mes_pico": int(months["promedio"].idxmax()), "participacion_mes_pico": months["promedio"].max(),
        "participacion_enero": months.loc[1, "promedio"], "participacion_febrero": months.loc[2, "promedio"],
        "participacion_ultimos_10_dias_prom": last_days.mean(),
    }


# ---------------------------------------------------------------------------------------------
# P5′. Gran Compra
# ---------------------------------------------------------------------------------------------

def p5(d: pd.DataFrame) -> dict:
    threshold = config.GRAN_COMPRA_THRESHOLD
    ordinary = d[d["gran_compra"] == 0]
    by_year = d.groupby("anio").apply(lambda g: pd.Series({
        "pct_gran_compra": g.loc[g["gran_compra"] == 1, "total"].sum() / g["total"].sum(),
        "ordinarias_sobre_umbral": int(g["ordinaria_sobre_umbral"].sum()),
        "monto_ordinario_sobre_umbral": g.loc[g["ordinaria_sobre_umbral"] == 1, "total"].sum(),
        "ordinarias_90_95k": int(((g["gran_compra"] == 0) & g["total"].between(90_000, 95_000, inclusive="left")).sum()),
        "ordinarias_95_100k": int(((g["gran_compra"] == 0) & g["total"].between(95_000, threshold, inclusive="left")).sum()),
    }), include_groups=False)
    by_year.to_csv(OUT / "p5_gran_compra_anual.csv")

    # Distribución de las compras ordinarias alrededor del umbral, en tramos de S/ 1 000
    edges = np.arange(80_000, 120_001, 1_000)
    hist = pd.cut(ordinary["total"], edges, right=False).value_counts().sort_index()
    hist = pd.DataFrame({"desde": edges[:-1], "hasta": edges[1:], "ordenes": hist.to_numpy()})
    hist.to_csv(OUT / "p5_umbral_histograma.csv", index=False)

    # Esperado en S/ 95 000–99 999 según la tendencia de los tramos de S/ 5 000 entre S/ 50 000 y S/ 95 000
    bins = np.arange(50_000, 95_001, 5_000)
    counts = pd.cut(ordinary["total"], bins, right=False).value_counts().sort_index().to_numpy()
    slope, intercept = np.polyfit(np.arange(len(counts)), np.log(counts), 1)
    expected = float(np.exp(intercept + slope * len(counts)))
    observed = int(ordinary["total"].between(95_000, threshold, inclusive="left").sum())
    last_thousand = int(ordinary["total"].between(threshold - 1_000, threshold, inclusive="left").sum())
    neighbours = hist[(hist["desde"] >= 90_000) & (hist["desde"] < 99_000)]["ordenes"].mean()
    above = int(ordinary["total"].between(threshold, threshold + 1_000, inclusive="left").sum())

    # Posible fraccionamiento: misma entidad, proveedor, catálogo y día; 2+ compras ordinarias,
    # cada una bajo el umbral, que juntas lo superan
    groups = ordinary.groupby(["ruc_entidad", "entidad_unica", "ruc_proveedor", "proveedor_unico", "catalogo", "fecha"]) \
        .agg(ordenes=("total", "size"), monto=("total", "sum"), mayor=("total", "max")).reset_index()
    split = groups[(groups["ordenes"] >= 2) & (groups["monto"] >= threshold) & (groups["mayor"] < threshold)]
    split = split.sort_values("monto", ascending=False)
    split.to_csv(OUT / "p5_posible_fraccionamiento.csv", index=False)

    over = d[d["ordinaria_sobre_umbral"] == 1]
    return {
        "pct_gran_compra_total": d.loc[d["gran_compra"] == 1, "total"].sum() / d["total"].sum(),
        "pct_gran_compra_2025": by_year.loc[LAST_FULL_YEAR, "pct_gran_compra"],
        "ordinarias_sobre_umbral": len(over), "monto_ordinario_sobre_umbral": over["total"].sum(),
        "pct_monto_ordinario_sobre_umbral": over["total"].sum() / ordinary["total"].sum(),
        "ordinarias_95_100k_observadas": observed, "ordinarias_95_100k_esperadas": expected,
        "exceso_95_100k": observed - expected,
        "ordinarias_99_100k": last_thousand, "promedio_tramos_vecinos_90_99k": neighbours,
        "ordinarias_100_101k": above,
        "grupos_posible_fraccionamiento": len(split), "ordenes_posible_fraccionamiento": int(split["ordenes"].sum()),
        "monto_posible_fraccionamiento": split["monto"].sum(),
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    d = load()
    key = {}
    for question, fn in [("P1", p1), ("P2", p2), ("P3", p3), ("P4", p4), ("P5", p5)]:
        for name, value in fn(d).items():
            key[(question, name)] = value
    table = pd.DataFrame([(q, n, v) for (q, n), v in key.items()], columns=["pregunta", "cifra", "valor"])
    table.to_csv(OUT / "cifras_clave.csv", index=False)
    with pd.option_context("display.max_rows", None, "display.width", 200, "display.float_format", "{:,.4f}".format):
        print(table.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
