"""Valida las medidas DAX del modelo contra el mismo cálculo hecho en Python.

Dos pasos, porque la consulta DAX se ejecuta en Power BI Desktop (con el MCP de modelado o con
DAX Studio):

    python tools/validate_measures.py consulta            # escribe tools/validacion_medidas.dax
    (ejecutar esa consulta en Power BI y guardar el resultado como CSV)
    python tools/validate_measures.py comparar <csv_dax>  # compara y escribe reports/validacion_medidas.csv

La comparación cubre cada medida numérica en tres contextos: el total, cada año y cada catálogo.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import config  # noqa: E402

QUERY_FILE = ROOT / "tools" / "validacion_medidas.dax"
OUT = config.REPORTS / "validacion_medidas.csv"
TOLERANCE = 1e-6          # diferencia relativa admitida (redondeo de punto flotante)

GLOBAL = ["Monto", "Órdenes", "Ticket promedio", "Ticket mediano", "Entidades compradoras",
          "Proveedores con ventas", "Monto compra efectiva", "HHI", "Participación top 3 proveedores",
          "Participación top 10 proveedores", "Proveedores para el 80 %", "Participación del líder",
          "Participación top 10 entidades", "Catálogos usados", "Monto Gran Compra", "Monto compra ordinaria",
          "% Gran Compra", "Órdenes ordinarias sobre el umbral", "Monto ordinario sobre el umbral",
          "% ordinario sobre el umbral", "Monto con IGV exonerado", "Órdenes atípicas altas",
          "% del monto en atípicos altos", "Órdenes que no son compra", "Monto ordinario sobre el umbral (S/ millones)",
          "Órdenes en posibles compras partidas", "Monto en posibles compras partidas (S/ millones)",
          "Monto ene–set (S/ millones)", "Proveedores con ventas ene–set"]
BY_YEAR = ["Monto", "Órdenes", "Var. interanual", "% Gran Compra", "Participación del último trimestre",
           "Participación de diciembre", "HHI", "Entidades compradoras", "Monto ene–set (S/ millones)",
           "Proveedores con ventas ene–set"]
BY_CATALOG = ["Monto", "Órdenes", "HHI", "Participación top 3 proveedores", "Proveedores para el 80 %",
              "Participación del líder", "% Gran Compra", "% ordinario sobre el umbral"]
BY_MONTH = ["Participación promedio del mes"]      # contexto: cada mes (1 a 12)
BY_BAND = ["Órdenes en el tramo"]                            # contexto: cada tramo de S/ 1 000 entre S/ 80 000 y 119 999
CUTOFF_MONTH = config.END[1]
LAST_FULL_YEAR = config.END[0] if config.END[1] == 12 else config.END[0] - 1


# ---------------------------------------------------------------------------------------------
# Python
# ---------------------------------------------------------------------------------------------

def load() -> pd.DataFrame:
    fact = pd.read_csv(config.CURATED / "fact_orden.csv", dtype={"ruc_entidad": str, "ruc_proveedor": str},
                       parse_dates=["fecha"])
    catalogs = pd.read_csv(config.CURATED / "dim_catalogo.csv")[["catalogo_id", "catalogo"]]
    states = pd.read_csv(config.CURATED / "dim_estado.csv")[["estado_id", "compra_efectiva"]]
    return fact.merge(catalogs, on="catalogo_id").merge(states, on="estado_id")


def share_top(amounts: pd.Series, n: int) -> float:
    return amounts.nlargest(n).sum() / amounts.sum()


def providers_for_80(amounts: pd.Series) -> int:
    """Igual que la medida DAX: proveedores cuyo monto acumulado de los estrictamente mayores es < 80 %."""
    values = amounts.to_numpy()
    total = values.sum()
    order = np.sort(values)[::-1]
    cum = np.concatenate([[0], np.cumsum(order)])
    # suma de los estrictamente mayores = acumulado antes de la primera aparición del valor
    first = {v: cum[i] for i, v in reversed(list(enumerate(order)))}
    before = np.array([first[v] for v in values])
    return int((before < 0.8 * total).sum())


def measures(d: pd.DataFrame, names: list[str], prior: pd.DataFrame | None = None) -> dict:
    by_prov = d.groupby("ruc_proveedor")["total"].sum()
    by_ent = d.groupby("ruc_entidad")["total"].sum()
    total = d["total"].sum()
    ordinary = d.loc[d["gran_compra"] == 0, "total"].sum()
    over = d["ordinaria_sobre_umbral"] == 1
    out = {
        "Monto": total,
        "Órdenes": len(d),
        "Ticket promedio": total / len(d),
        "Ticket mediano": d["total"].median(),
        "Entidades compradoras": d["ruc_entidad"].nunique(),
        "Proveedores con ventas": d["ruc_proveedor"].nunique(),
        "Monto compra efectiva": d.loc[d["compra_efectiva"] == 1, "total"].sum(),
        "HHI": ((by_prov / total * 100) ** 2).sum(),
        "Participación top 3 proveedores": share_top(by_prov, 3),
        "Participación top 10 proveedores": share_top(by_prov, 10),
        "Proveedores para el 80 %": providers_for_80(by_prov),
        "Participación del líder": by_prov.max() / total,
        "Participación top 10 entidades": share_top(by_ent, 10),
        "Catálogos usados": d["catalogo_id"].nunique(),
        "Monto Gran Compra": d.loc[d["gran_compra"] == 1, "total"].sum(),
        "Monto compra ordinaria": ordinary,
        "% Gran Compra": d.loc[d["gran_compra"] == 1, "total"].sum() / total,
        "Órdenes ordinarias sobre el umbral": int(over.sum()),
        "Monto ordinario sobre el umbral": d.loc[over, "total"].sum(),
        "% ordinario sobre el umbral": d.loc[over, "total"].sum() / ordinary if ordinary else np.nan,
        "Monto con IGV exonerado": d.loc[d["igv_exonerado"] == 1, "total"].sum(),
        "Órdenes atípicas altas": int(d["atipico_alto"].sum()),
        "% del monto en atípicos altos": d.loc[d["atipico_alto"] == 1, "total"].sum() / total,
        "Órdenes que no son compra": int((d["compra_efectiva"] == 0).sum()),
        "Participación del último trimestre": d.loc[d["fecha"].dt.month >= 10, "total"].sum() / total,
        "Participación de diciembre": d.loc[d["fecha"].dt.month == 12, "total"].sum() / total,
        "Var. interanual": (total / prior["total"].sum() - 1) if prior is not None and len(prior) else np.nan,
        "Monto ordinario sobre el umbral (S/ millones)": d.loc[over, "total"].sum() / 1e6,
        "Órdenes en posibles compras partidas": int(d["posible_fraccionamiento"].sum()),
        "Monto en posibles compras partidas (S/ millones)": d.loc[d["posible_fraccionamiento"] == 1, "total"].sum() / 1e6,
        "Monto ene–set (S/ millones)": d.loc[d["fecha"].dt.month <= CUTOFF_MONTH, "total"].sum() / 1e6,
        "Proveedores con ventas ene–set": d.loc[d["fecha"].dt.month <= CUTOFF_MONTH, "ruc_proveedor"].nunique(),
    }
    return {k: out[k] for k in names}


def expected() -> pd.DataFrame:
    d = load()
    rows = [("global", "total", k, v) for k, v in measures(d, GLOBAL).items()]
    calendar_end = pd.Timestamp(f"{config.END[0]}-{config.END[1]:02d}-01") + pd.offsets.MonthEnd(0)
    for year, g in d.groupby(d["fecha"].dt.year):
        # DATEADD(-1 año) desplaza las fechas del calendario del año. El último año del calendario
        # termina en el corte (2026-09-30), así que se compara con enero–setiembre del año anterior.
        year_end = min(pd.Timestamp(f"{year}-12-31"), calendar_end)
        prior = d[(d["fecha"] >= f"{year - 1}-01-01") & (d["fecha"] <= year_end - pd.DateOffset(years=1))]
        rows += [("anio", str(year), k, v) for k, v in measures(g, BY_YEAR, prior).items()]
    for catalog, g in d.groupby("catalogo"):
        rows += [("catalogo", catalog, k, v) for k, v in measures(g, BY_CATALOG).items()]
    full = d[d["fecha"].dt.year <= LAST_FULL_YEAR]
    shares = full.groupby([full["fecha"].dt.year, full["fecha"].dt.month])["total"].sum()
    shares = shares / shares.groupby(level=0).transform("sum")
    for month, value in shares.groupby(level=1).mean().items():
        rows.append(("mes", str(month), "Participación promedio del mes", value))
    ordinary = d[(d["gran_compra"] == 0) & d["total"].between(80_000, 120_000, inclusive="left")]
    for band, value in ordinary.groupby((ordinary["total"] // 1000).astype(int)).size().items():
        rows.append(("tramo", str(band), "Órdenes en el tramo", value))
    return pd.DataFrame(rows, columns=["contexto", "clave", "medida", "python"])


# ---------------------------------------------------------------------------------------------
# DAX
# ---------------------------------------------------------------------------------------------

def dax_name(name: str) -> str:
    return "[" + name.replace("]", "]]") + "]"


def query() -> str:
    parts = []
    for m in GLOBAL:
        parts.append(f'ROW ( "contexto", "global", "clave", "total", "medida", "{m}", "valor", {dax_name(m)} )')
    for m in BY_YEAR:
        parts.append(f'SELECTCOLUMNS ( VALUES ( dim_fecha[anio] ), "contexto", "anio", "clave", FORMAT ( dim_fecha[anio], "0" ), '
                     f'"medida", "{m}", "valor", {dax_name(m)} )')
    for m in BY_CATALOG:
        parts.append(f'SELECTCOLUMNS ( VALUES ( dim_catalogo[catalogo] ), "contexto", "catalogo", "clave", dim_catalogo[catalogo], '
                     f'"medida", "{m}", "valor", {dax_name(m)} )')
    for m in BY_MONTH:
        parts.append(f'SELECTCOLUMNS ( VALUES ( dim_fecha[mes] ), "contexto", "mes", "clave", FORMAT ( dim_fecha[mes], "0" ), '
                     f'"medida", "{m}", "valor", {dax_name(m)} )')
    for m in BY_BAND:
        parts.append('SELECTCOLUMNS ( FILTER ( VALUES ( fact_orden[tramo_umbral_miles] ), '
                     'NOT ISBLANK ( fact_orden[tramo_umbral_miles] ) ), "contexto", "tramo", '
                     f'"clave", FORMAT ( fact_orden[tramo_umbral_miles], "0" ), "medida", "{m}", "valor", {dax_name(m)} )')
    return "EVALUATE\nUNION (\n    " + ",\n    ".join(parts) + "\n)\n"


def compare(dax_csv: Path) -> pd.DataFrame:
    dax = pd.read_csv(dax_csv, dtype=str)
    dax.columns = [c.strip("[]") for c in dax.columns]
    dax["dax"] = pd.to_numeric(dax["valor"].str.replace(",", ".", regex=False), errors="coerce")
    out = expected().merge(dax[["contexto", "clave", "medida", "dax"]], on=["contexto", "clave", "medida"], how="outer")
    # En DAX, una suma o un conteo sin filas devuelve BLANK; en Python, 0. Se tratan como iguales.
    dax_value = out["dax"].where(out["dax"].notna() | out["python"].ne(0), 0.0)
    out["diferencia_relativa"] = (dax_value - out["python"]).abs() / out["python"].abs().clip(lower=1e-9)
    both_blank = dax_value.isna() & out["python"].isna()
    match = dax_value.notna() & out["python"].notna() & (out["diferencia_relativa"] <= TOLERANCE)
    out["resultado"] = np.where(both_blank | match, "cumple", "falla")
    return out


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) >= 2 and sys.argv[1] == "consulta":
        QUERY_FILE.write_text(query(), encoding="utf-8")
        print(f"Consulta escrita en {QUERY_FILE.relative_to(ROOT)}")
        return 0
    if len(sys.argv) == 3 and sys.argv[1] == "comparar":
        result = compare(Path(sys.argv[2]))
        result.to_csv(OUT, index=False)
        failed = result[result["resultado"] != "cumple"]
        print(f"{len(result)} comparaciones; {len(failed)} fallan; diferencia relativa máxima "
              f"{result['diferencia_relativa'].max():.2e}")
        if len(failed):
            print(failed.to_string(index=False))
        return 1 if len(failed) else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
