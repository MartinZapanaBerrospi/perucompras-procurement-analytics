"""Fase 3 — Transforma las órdenes: raw → staging → modelo en estrella (data/curated).

    raw       57 CSV tal como los publica el portal (data/raw/ordenes)
    staging   una sola tabla limpia y tipada, con todas las columnas (data/staging/ordenes.parquet)
    curated   hechos y dimensiones que lee Power BI (data/curated/*.csv)

Ninguna orden se excluye: lo que la Fase 2 marcó como atípico o fuera de regla queda como columna
de marca en el hecho. El linaje (filas y monto en cada paso) se escribe en reports/linaje.csv y
el script falla si algún paso pierde o duplica una orden o un sol.

Uso:
    python -m src.transform
"""

import sys

import pandas as pd

from src import config
from src.parse_ordenes import clean, load_orders, outlier_thresholds

MONTHS_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "setiembre",
             "octubre", "noviembre", "diciembre"]
DAYS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
STATES = [  # (id, estado, ¿es compra efectiva?)
    ("A", "ACEPTADA", 1),
    ("E", "ACEPTADA C/ENTREGA PENDIENTE", 1),
    ("P", "PAGADA", 1),
    ("R", "RESUELTA", 0),
    ("N", "ORDEN DE COMPRA NULA", 0),
]
PERSON_TYPE = {"10": "Persona natural", "20": "Persona jurídica"}


# ---------------------------------------------------------------------------------------------
# Dimensiones
# ---------------------------------------------------------------------------------------------

def latest_names(df: pd.DataFrame, key: str, name: str) -> pd.DataFrame:
    """Problema 8: una fila por RUC con su nombre más reciente y cuántos nombres tuvo."""
    ordered = df.sort_values(["fecha_formalizacion", "orden"])
    g = ordered.groupby(key)
    return pd.DataFrame({
        name: g[name].last(),
        "nombres_historicos": g[name].nunique(),
        "primera_orden": g["fecha_formalizacion"].min().dt.date,
        "ultima_orden": g["fecha_formalizacion"].max().dt.date,
    }).reset_index()


def unique_label(dim: pd.DataFrame, key: str, name: str) -> pd.Series:
    """Problema 9: si dos RUC comparten nombre, el nombre lleva el RUC al lado para distinguirlos."""
    shared = dim[name].duplicated(keep=False)
    return dim[name].where(~shared, dim[name] + " (RUC " + dim[key] + ")")


def dim_entidad(df: pd.DataFrame) -> pd.DataFrame:
    dim = latest_names(df, "ruc_entidad", "entidad")
    dim["entidad_unica"] = unique_label(dim, "ruc_entidad", "entidad")
    return dim[["ruc_entidad", "entidad", "entidad_unica", "nombres_historicos", "primera_orden", "ultima_orden"]]


def dim_proveedor(df: pd.DataFrame) -> pd.DataFrame:
    dim = latest_names(df, "ruc_proveedor", "proveedor")
    dim["proveedor_unico"] = unique_label(dim, "ruc_proveedor", "proveedor")
    dim["tipo_persona"] = dim["ruc_proveedor"].str[:2].map(PERSON_TYPE).fillna("Otro")
    return dim[["ruc_proveedor", "proveedor", "proveedor_unico", "tipo_persona", "nombres_historicos",
                "primera_orden", "ultima_orden"]]


def dim_catalogo(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(["catalogo", "rubro"])
    dim = g.agg(vigente_desde=("periodo_archivo", "min"), vigente_hasta=("periodo_archivo", "max")).reset_index()
    dim = dim.sort_values(["rubro", "catalogo"]).reset_index(drop=True)
    dim.insert(0, "catalogo_id", range(1, len(dim) + 1))
    last = df["periodo_archivo"].max()
    dim["con_compras_al_corte"] = (dim["vigente_hasta"] == last).astype(int)
    return dim


def dim_estado() -> pd.DataFrame:
    return pd.DataFrame(STATES, columns=["estado_id", "estado", "compra_efectiva"])


def dim_fecha() -> pd.DataFrame:
    y0, m0 = config.START
    y1, m1 = config.END
    days = pd.date_range(f"{y0}-{m0:02d}-01", pd.Timestamp(f"{y1}-{m1:02d}-01") + pd.offsets.MonthEnd(0))
    return pd.DataFrame({
        "fecha": days.date,
        "anio": days.year,
        "trimestre": "T" + days.quarter.astype(str),
        "mes": days.month,
        "mes_nombre": [MONTHS_ES[m - 1] for m in days.month],
        "anio_mes": days.strftime("%Y-%m"),
        "mes_inicio": days.to_period("M").to_timestamp().date,   # primer día del mes: eje mensual continuo
        "dia_semana": [DAYS_ES[d] for d in days.dayofweek],
        "dia_semana_num": days.dayofweek + 1,     # 1 = lunes; ordena dia_semana en Power BI
        "es_fin_de_semana": (days.dayofweek >= 5).astype(int),
    })


# ---------------------------------------------------------------------------------------------
# Hecho
# ---------------------------------------------------------------------------------------------

def possible_split(fact: pd.DataFrame) -> pd.Series:
    """P5′: la orden pertenece a un grupo de 2 o más compras ordinarias de la misma entidad, al mismo
    proveedor, en el mismo catálogo y el mismo día, cada una bajo el umbral de la Gran Compra pero
    que juntas lo superan. Es una señal para revisar, no una prueba de fraccionamiento."""
    threshold = config.GRAN_COMPRA_THRESHOLD
    ordinary = fact["gran_compra"].eq(0)
    keys = [fact["ruc_entidad"], fact["ruc_proveedor"], fact["catalogo_id"], fact["fecha"]]
    total = fact["total"].where(ordinary)
    group_size = total.groupby(keys).transform("count")
    group_sum = total.groupby(keys).transform("sum")
    group_max = total.groupby(keys).transform("max")
    return ordinary & group_size.ge(2) & group_sum.ge(threshold) & group_max.lt(threshold)


def fact_orden(df: pd.DataFrame, catalogs: pd.DataFrame) -> pd.DataFrame:
    low, high = outlier_thresholds(df["total"])
    state_id = {name: sid for sid, name, _ in STATES}
    catalog_id = catalogs.set_index("catalogo")["catalogo_id"]
    igv_rate = df["igv"] / df["sub_total"]
    fact = pd.DataFrame({
        "orden": df["orden"],
        "fecha": df["fecha_formalizacion"].dt.date,
        "ruc_entidad": df["ruc_entidad"],
        "ruc_proveedor": df["ruc_proveedor"],
        "catalogo_id": df["catalogo"].map(catalog_id),
        "estado_id": df["estado"].map(state_id),
        "gran_compra": df["tipo_procedimiento"].eq("Gran Compra").astype(int),
        "igv": df["igv"].round(2),
        "total": df["total"].round(2),
        # Marcas de la Fase 2: no excluyen nada, permiten filtrar y explicar
        "igv_exonerado": df["igv"].eq(0).astype(int),
        "igv_parcial": (df["igv"].gt(0) & (igv_rate - config.IGV_RATE).abs().gt(0.005)).astype(int),
        "atipico_alto": df["total"].gt(high).astype(int),
        "atipico_bajo": df["total"].lt(low).astype(int),
        "ordinaria_sobre_umbral": (df["tipo_procedimiento"].eq("Compra ordinaria")
                                   & df["total"].ge(config.GRAN_COMPRA_THRESHOLD)).astype(int),
    })
    fact["posible_fraccionamiento"] = possible_split(fact).astype(int)
    return fact.sort_values(["fecha", "orden"]).reset_index(drop=True)


# ---------------------------------------------------------------------------------------------
# Linaje e integridad
# ---------------------------------------------------------------------------------------------

def check_integrity(tables: dict) -> list[str]:
    """Claves únicas, claves foráneas completas y sin nulos en el hecho."""
    fact = tables["fact_orden"]
    problems = []
    for name, key in [("fact_orden", "orden"), ("dim_entidad", "ruc_entidad"), ("dim_proveedor", "ruc_proveedor"),
                      ("dim_catalogo", "catalogo_id"), ("dim_estado", "estado_id"), ("dim_fecha", "fecha")]:
        if tables[name][key].duplicated().any():
            problems.append(f"{name}: clave {key} repetida")
    for fk, dim, key in [("ruc_entidad", "dim_entidad", "ruc_entidad"), ("ruc_proveedor", "dim_proveedor", "ruc_proveedor"),
                         ("catalogo_id", "dim_catalogo", "catalogo_id"), ("estado_id", "dim_estado", "estado_id"),
                         ("fecha", "dim_fecha", "fecha")]:
        orphans = ~fact[fk].isin(tables[dim][key])
        if orphans.any():
            problems.append(f"fact_orden.{fk}: {int(orphans.sum())} filas sin {dim}")
    nulls = fact.isna().sum()
    for col, n in nulls[nulls > 0].items():
        problems.append(f"fact_orden.{col}: {n} nulos")
    for name in ("dim_entidad", "dim_proveedor"):
        label = "entidad_unica" if name == "dim_entidad" else "proveedor_unico"
        if tables[name][label].duplicated().any():
            problems.append(f"{name}: {label} repetido")
    return problems


def lineage(raw: pd.DataFrame, staging: pd.DataFrame, fact: pd.DataFrame, states: pd.DataFrame) -> pd.DataFrame:
    raw_total = pd.to_numeric(raw["total"].str.strip(), errors="coerce").sum()
    effective = fact["estado_id"].map(states.set_index("estado_id")["compra_efectiva"]).eq(1)
    rows = [
        ("1. raw", "57 CSV del portal, todo como texto", len(raw), raw["orden"].str.strip().nunique(),
         raw_total, len(raw.columns) - 1, "Tal como se publican"),
        ("2. staging", "Una tabla limpia y tipada", len(staging), staging["orden"].nunique(),
         staging["total"].sum(), len(staging.columns) - 1, "Reglas de campo: 0 filas excluidas"),
        ("3. curated", "fact_orden", len(fact), fact["orden"].nunique(), fact["total"].sum(),
         len(fact.columns), "Mismas filas; columnas sin uso fuera, marcas agregadas"),
        ("3a. marca", "Compra efectiva (sin nulas ni resueltas)", int(effective.sum()), int(effective.sum()),
         fact.loc[effective, "total"].sum(), None, "Subconjunto, no exclusión"),
        ("3b. marca", "Atípicos de monto alto", int(fact["atipico_alto"].sum()), int(fact["atipico_alto"].sum()),
         fact.loc[fact["atipico_alto"] == 1, "total"].sum(), None, "Subconjunto, no exclusión"),
        ("3c. marca", "Compras ordinarias sobre el umbral", int(fact["ordinaria_sobre_umbral"].sum()),
         int(fact["ordinaria_sobre_umbral"].sum()),
         fact.loc[fact["ordinaria_sobre_umbral"] == 1, "total"].sum(), None, "Subconjunto, no exclusión"),
        ("3d. marca", "Posibles compras partidas", int(fact["posible_fraccionamiento"].sum()),
         int(fact["posible_fraccionamiento"].sum()),
         fact.loc[fact["posible_fraccionamiento"] == 1, "total"].sum(), None, "Subconjunto, no exclusión"),
    ]
    out = pd.DataFrame(rows, columns=["paso", "descripcion", "filas", "ordenes_unicas", "monto", "columnas", "nota"])
    out["monto"] = out["monto"].round(2)
    return out


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    raw = load_orders()
    staging = clean(raw)
    config.STAGING.mkdir(parents=True, exist_ok=True)
    staging.to_parquet(config.STAGING / "ordenes.parquet", index=False)

    catalogs = dim_catalogo(staging)
    tables = {
        "fact_orden": fact_orden(staging, catalogs),
        "dim_entidad": dim_entidad(staging),
        "dim_proveedor": dim_proveedor(staging),
        "dim_catalogo": catalogs,
        "dim_estado": dim_estado(),
        "dim_fecha": dim_fecha(),
    }

    problems = check_integrity(tables)
    trail = lineage(raw, staging, tables["fact_orden"], tables["dim_estado"])
    base = trail.iloc[0]
    for row in trail.iloc[1:3].itertuples():
        if row.filas != base.filas or abs(row.monto - base.monto) > 0.05:
            problems.append(f"Linaje: {row.paso} tiene {row.filas} filas y S/ {row.monto:,.2f}; "
                            f"raw tiene {base.filas} y S/ {base.monto:,.2f}")
    for p in problems:
        print(f"  ✗ {p}")
    if problems:
        return 1

    config.CURATED.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        table.to_csv(config.CURATED / f"{name}.csv", index=False, lineterminator="\n")
    config.REPORTS.mkdir(parents=True, exist_ok=True)
    trail.to_csv(config.REPORTS / "linaje.csv", index=False)

    print(trail[["paso", "filas", "monto"]].to_string(index=False))
    for name, table in tables.items():
        size = (config.CURATED / f"{name}.csv").stat().st_size / 1e6
        print(f"  {name}: {len(table):,} filas, {size:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
