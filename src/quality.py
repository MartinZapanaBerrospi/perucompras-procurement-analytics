"""Fase 2 — Perfilado y calidad de los 57 archivos de órdenes de compra.

Lee los archivos registrados en el manifiesto, aplica las reglas de limpieza de campo de
src/parse_ordenes.py y mide la calidad en seis dimensiones: completitud, unicidad, validez,
consistencia, exactitud y oportunidad. Escribe en reports/calidad/:

    perfilado_columnas.csv   una fila por columna: vacíos, distintos, rango, valores frecuentes
    perfilado_mensual.csv    una fila por archivo: codificación, formato, filas, monto, corte
    reglas.csv               cada regla de calidad con filas y monto afectados, y su resultado
    atipicos.csv             órdenes marcadas como atípicas, con el motivo
    nombres_por_ruc.csv      RUC que aparecen con más de un nombre
    nombres_con_varios_ruc.csv  nombres de entidad que corresponden a más de un RUC
    acuerdos_marco.csv       cada texto de acuerdo marco y el catálogo estable que le toca

y reports/validaciones.csv (comparación con las cifras oficiales).

Termina con error si alguna regla bloqueante falla.

Uso:
    python -m src.quality
"""

import csv
import sys

import numpy as np
import pandas as pd

from src import config, validate
from src.parse_ordenes import (AMOUNT_COLUMNS, COLUMNS, DATE_COLUMNS, decode, normalize_text,
                               parse_amount, parse_date, read_raw, ruc_is_valid, split_framework,
                               strip_fields)

REQUIRED = ["ruc_proveedor", "proveedor", "ruc_entidad", "entidad", "tipo_procedimiento", "orden",
            "estado", "fecha_formalizacion", "total", "acuerdo_marco"]
NON_PURCHASE_STATES = {"ORDEN DE COMPRA NULA", "RESUELTA"}
SIAF_NOTE = "Actualizado automáticamente por la vinculación con el SIAF"


def is_empty(values: pd.Series) -> pd.Series:
    """Vacío = nulo, o texto en blanco. Sirve para columnas de texto, fecha o monto por igual."""
    if pd.api.types.is_string_dtype(values) or values.dtype == object:
        return values.isna() | values.astype("string").str.strip().eq("")
    return values.isna()


# ---------------------------------------------------------------------------------------------
# Lectura
# ---------------------------------------------------------------------------------------------

def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (órdenes tal como vienen, todo texto) y (una fila de metadatos por archivo)."""
    with config.MANIFEST.open(encoding="utf-8", newline="") as f:
        manifest = list(csv.DictReader(f))
    frames, files = [], []
    for row in manifest:
        path = config.ROOT / row["archivo"]
        content = path.read_bytes()
        text, encoding = decode(content)
        df = read_raw(path)
        df.insert(0, "periodo_archivo", row["periodo"])
        frames.append(df)
        files.append({
            "periodo": row["periodo"],
            "archivo_portal": row["archivo_portal"],
            "codificacion": encoding,
            "fin_de_linea": "CRLF" if b"\r\n" in content else "LF",
            "columnas": len(df.columns) - 1,
            "filas": len(df),
            "celdas_con_tabulador": int(df.drop(columns="periodo_archivo").apply(
                lambda s: s.str.contains("\t", regex=False)).to_numpy().sum()),
            "publicado_en": row["publicado_en"],
        })
    return pd.concat(frames, ignore_index=True), pd.DataFrame(files)


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    """Aplica las reglas de campo: espacios, fechas, montos y acuerdo marco."""
    df = strip_fields(raw)
    for col in DATE_COLUMNS:
        df[col] = parse_date(df[col])
    for col in AMOUNT_COLUMNS:
        df[col] = parse_amount(df[col])
    parts = df["acuerdo_marco"].map(split_framework)
    df["codigo_acuerdo"] = parts.str[0]
    df["clave_catalogo"] = parts.str[1].map(normalize_text)
    catalogs = pd.read_csv(config.CATALOGS)
    return df.merge(catalogs[["clave_normalizada", "catalogo", "rubro"]],
                    left_on="clave_catalogo", right_on="clave_normalizada", how="left").drop(
        columns="clave_normalizada")


# ---------------------------------------------------------------------------------------------
# Perfilado
# ---------------------------------------------------------------------------------------------

def profile_columns(raw: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    original = {v: k for k, v in COLUMNS.items()}
    rows = []
    for col in COLUMNS.values():
        r, c = raw[col], df[col]
        empty = is_empty(c)
        values = c[~empty]
        top = r.str.strip().value_counts().head(3)
        rows.append({
            "columna_origen": original[col],
            "columna": col,
            "tipo": "fecha" if col in DATE_COLUMNS else "monto" if col in AMOUNT_COLUMNS else "texto",
            "vacios": int(empty.sum()),
            "pct_vacios": round(100 * empty.mean(), 2),
            "distintos_origen": int(r.nunique()),
            "distintos_limpio": int(values.nunique()),
            "con_espacios_extremos": int((r != r.str.strip()).sum()),
            "minimo": values.min() if len(values) and col in DATE_COLUMNS + AMOUNT_COLUMNS else "",
            "maximo": values.max() if len(values) and col in DATE_COLUMNS + AMOUNT_COLUMNS else "",
            "longitud_min": int(r.str.strip().str.len().min()),
            "longitud_max": int(r.str.strip().str.len().max()),
            "valores_frecuentes": " | ".join(f"{k[:60]} ({v})" for k, v in top.items())
                                   if col not in AMOUNT_COLUMNS + DATE_COLUMNS else "",
        })
    return pd.DataFrame(rows)


def date_format(values: pd.Series) -> str:
    patterns = values.str.strip().str.replace(r"\d", "9", regex=True).value_counts()
    return " / ".join(patterns.index[:2])


def profile_months(raw: pd.DataFrame, df: pd.DataFrame, files: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("periodo_archivo")
    out = files.set_index("periodo").join(pd.DataFrame({
        "formato_fecha": raw.groupby("periodo_archivo")["fecha_formalizacion"].agg(date_format),
        "monto": g["total"].sum().round(2),
        "pct_gran_compra": (100 * g.apply(lambda x: x.loc[x["tipo_procedimiento"] == "Gran Compra", "total"].sum()
                                          / x["total"].sum(), include_groups=False)).round(2),
        "fecha_proceso": g["fecha_proceso"].max(),
        "pct_pagadas_al_corte": (100 * g["estado"].apply(lambda s: s.eq("PAGADA").mean())).round(2),
    }))
    month_end = pd.to_datetime(out.index) + pd.offsets.MonthEnd(0)
    out["dias_cierre_a_corte"] = (out["fecha_proceso"].dt.normalize() - month_end).dt.days
    published = pd.to_datetime(out["publicado_en"]).dt.tz_localize(None)
    out["dias_cierre_a_publicacion"] = (published.dt.normalize() - month_end).dt.days
    return out.reset_index().rename(columns={"index": "periodo"})


# ---------------------------------------------------------------------------------------------
# Reglas
# ---------------------------------------------------------------------------------------------

class Rules:
    """Acumula reglas con un formato único: qué se evaluó, cuántas filas fallan y cuánto dinero."""

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.rows = []

    def add(self, rule_id, dimension, rule, severity, fails, evaluated=None, amount=None, detail=""):
        """fails: máscara booleana sobre las órdenes, o un número cuando la regla no es por fila."""
        if isinstance(fails, pd.Series):
            n_fail = int(fails.sum())
            n_eval = len(fails) if evaluated is None else evaluated
            amount = float(self.df.loc[fails, "total"].sum()) if amount is None else amount
        else:
            n_fail, n_eval = int(fails), evaluated
        if n_fail == 0:
            result = "cumple"
        else:
            result = {"bloqueante": "falla", "alerta": "alerta", "info": "info"}[severity]
        self.rows.append({
            "id": rule_id, "dimension": dimension, "regla": rule, "severidad": severity,
            "evaluadas": n_eval, "fallan": n_fail,
            "pct_fallan": round(100 * n_fail / n_eval, 3) if n_eval else None,
            "monto_afectado": round(amount, 2) if amount is not None else None,
            "resultado": result, "detalle": detail,
        })

    def table(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows)


def run_rules(raw: pd.DataFrame, df: pd.DataFrame, months: pd.DataFrame,
              official: pd.DataFrame) -> pd.DataFrame:
    r = Rules(df)
    n = len(df)
    expected = {f"{y}-{m:02d}" for y, m in config.periods()}

    # Completitud
    r.add("C1", "Completitud", "Los 57 meses del periodo están presentes", "bloqueante",
          len(expected - set(months["periodo"])), evaluated=len(expected))
    r.add("C2", "Completitud", "Los 57 archivos traen las 19 columnas del diccionario", "bloqueante",
          int((months["columnas"] != len(COLUMNS)).sum()), evaluated=len(months))
    for col in REQUIRED:
        r.add("C3", "Completitud", f"Campo obligatorio sin vacíos: {col}", "bloqueante", is_empty(df[col]))
    for col in ["descripcion_cesion_derechos", "url_documento_estado", "descripcion_estado"]:
        r.add("C4", "Completitud", f"Columna con contenido: {col}", "info", is_empty(df[col]),
              detail="Columna mayormente vacía: se documenta y no se usa en el análisis")

    # Unicidad
    r.add("U1", "Unicidad", "Cada código de orden aparece una sola vez en los 57 meses", "bloqueante",
          df["orden"].duplicated(keep=False))
    r.add("U2", "Unicidad", "No hay filas idénticas", "bloqueante",
          raw.drop(columns="periodo_archivo").duplicated(keep=False))

    # Validez
    r.add("V1", "Validez", "RUC del proveedor: 11 dígitos y dígito verificador correcto", "bloqueante",
          ~df["ruc_proveedor"].map(ruc_is_valid))
    r.add("V2", "Validez", "RUC de la entidad: 11 dígitos y dígito verificador correcto", "bloqueante",
          ~df["ruc_entidad"].map(ruc_is_valid))
    r.add("V3", "Validez", "RUC de la entidad es de persona jurídica (empieza con 20)", "alerta",
          ~df["ruc_entidad"].str.startswith("20"))
    for col in DATE_COLUMNS:
        r.add("V4", "Validez", f"Fecha interpretable: {col}", "bloqueante", df[col].isna())
    for col in AMOUNT_COLUMNS:
        r.add("V5", "Validez", f"Monto numérico: {col}", "bloqueante", df[col].isna())
    r.add("V6", "Validez", "Total y subtotal mayores que cero; IGV no negativo", "bloqueante",
          (df["total"] <= 0) | (df["sub_total"] <= 0) | (df["igv"] < 0))
    r.add("V7", "Validez", "Tipo de procedimiento dentro del dominio (Compra ordinaria, Gran Compra)",
          "bloqueante", ~df["tipo_procedimiento"].isin(config.VALID_PROCEDURES))
    r.add("V8", "Validez", "Estado dentro del dominio de 5 estados conocidos", "bloqueante",
          ~df["estado"].isin(config.VALID_STATES))
    r.add("V9", "Validez", "Código de orden con el patrón OCAM-AAAA-N-N-N", "alerta",
          ~df["orden"].str.fullmatch(r"OCAM-\d{4}-\d+-\d+-\d+"))
    r.add("V10", "Validez", "Acuerdo marco asignado a un catálogo estable", "bloqueante",
          df["catalogo"].isna())

    # Consistencia
    r.add("K1", "Consistencia", "TOTAL = SUB_TOTAL + IGV (±S/ 0,01)", "bloqueante",
          (df["sub_total"] + df["igv"] - df["total"]).abs() > 0.011)
    ratio = df["igv"] / df["sub_total"]
    r.add("K2", "Consistencia", "IGV en cero (orden exonerada)", "info", df["igv"].eq(0),
          detail="Se concentra en entidades de la Amazonía (Ley 27037); no es un error")
    r.add("K3", "Consistencia", "IGV igual al 18 % del subtotal (±0,5 pp), sin contar las exoneradas",
          "alerta", df["igv"].gt(0) & (ratio - config.IGV_RATE).abs().gt(0.005),
          detail="Órdenes con parte de los bienes exonerados")
    r.add("K4", "Consistencia", "Fecha de formalización dentro del mes del archivo", "bloqueante",
          df["fecha_formalizacion"].dt.strftime("%Y-%m") != df["periodo_archivo"])
    r.add("K5", "Consistencia", "Último estado no anterior a la formalización ni posterior al corte",
          "bloqueante", (df["fecha_ultimo_estado"] < df["fecha_formalizacion"])
          | (df["fecha_ultimo_estado"] > df["fecha_proceso"]))
    for kind, ruc, name in [("proveedor", "ruc_proveedor", "proveedor"), ("entidad", "ruc_entidad", "entidad")]:
        multi = df.groupby(ruc)[name].transform("nunique") > 1
        r.add("K6", "Consistencia", f"Cada RUC de {kind} tiene un solo nombre", "alerta", multi,
              detail=f"{df.loc[multi, ruc].nunique()} RUC con más de un nombre; se usa el nombre más reciente")
    multi = df.groupby("entidad")["ruc_entidad"].transform("nunique") > 1
    r.add("K7", "Consistencia", "Cada nombre de entidad corresponde a un solo RUC", "alerta", multi,
          detail=f"{df.loc[multi, 'entidad'].nunique()} nombres compartidos por entidades distintas; "
                 "la identidad es el RUC, nunca el nombre")
    r.add("K8", "Consistencia", "Compra ordinaria por debajo del umbral de Gran Compra (S/ 100 000)",
          "alerta", df["tipo_procedimiento"].eq("Compra ordinaria") & df["total"].ge(config.GRAN_COMPRA_THRESHOLD),
          detail="La Gran Compra es obligatoria desde S/ 100 000; puede haber excepciones que los datos no muestran")
    paid = df["estado"].eq("PAGADA")
    r.add("K9", "Consistencia", "Las órdenes pagadas fueron actualizadas por el SIAF", "info",
          paid & df["descripcion_estado"].ne(SIAF_NOTE), evaluated=int(paid.sum()),
          detail="El resto se marcó pagada sin la nota automática del SIAF")

    # Exactitud
    for row in official.itertuples():
        r.add("E1" if row.medida == "monto_soles" else "E2", "Exactitud",
              f"{row.concepto} {row.anio}: {row.medida} igual a la cifra oficial (±1 %)",
              "bloqueante" if row.medida == "monto_soles" else "alerta",
              int(row.resultado != "cumple"), evaluated=1,
              detail=f"oficial {row.oficial:,.2f}; calculado {row.calculado:,.2f}; diferencia {row.diferencia_pct} %")

    # Oportunidad
    late = months["dias_cierre_a_corte"] > 3
    r.add("O1", "Oportunidad", "El estado de las órdenes se fotografía a más tardar 3 días después del cierre",
          "alerta", int(late.sum()), evaluated=len(months),
          detail="Meses con corte tardío: " + ", ".join(months.loc[late, "periodo"]))
    slow = months["dias_cierre_a_publicacion"] > 7
    r.add("O2", "Oportunidad", "El archivo se publica a más tardar 7 días después del cierre del mes", "alerta",
          int(slow.sum()), evaluated=len(months),
          detail="Fecha de la última modificación en el portal; los lotes de 2024 reemplazaron archivos previos")
    comparable = months[months["dias_cierre_a_corte"] <= 3]
    median_paid = comparable["pct_pagadas_al_corte"].median()
    gap = comparable["pct_pagadas_al_corte"] < median_paid / 3
    r.add("O3", "Oportunidad", "El porcentaje de órdenes pagadas al corte no cae a menos de un tercio de la mediana",
          "alerta", int(gap.sum()), evaluated=len(comparable),
          detail=f"Mediana {median_paid:.1f} %; meses afectados: " + ", ".join(comparable.loc[gap, "periodo"]))
    return r.table()


# ---------------------------------------------------------------------------------------------
# Atípicos, nombres y acuerdos marco
# ---------------------------------------------------------------------------------------------

def outliers(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    log_total = np.log10(df["total"])
    q1, q3 = log_total.quantile([0.25, 0.75])
    iqr = q3 - q1
    low, high = 10 ** (q1 - config.OUTLIER_IQR_FACTOR * iqr), 10 ** (q3 + config.OUTLIER_IQR_FACTOR * iqr)
    reason = pd.Series("", index=df.index)
    reason[df["total"] > high] = "monto_muy_alto"
    reason[df["total"] < low] = "monto_muy_bajo"
    reason[df["estado"].isin(NON_PURCHASE_STATES)] = "estado_no_compra"
    flagged = df[reason != ""].assign(motivo=reason[reason != ""])
    cols = ["motivo", "orden", "periodo_archivo", "entidad", "proveedor", "catalogo", "tipo_procedimiento",
            "estado", "total"]
    thresholds = {"umbral_bajo": round(low, 2), "umbral_alto": round(high, 2)}
    return flagged[cols].sort_values(["motivo", "total"], ascending=[True, False]), thresholds


def spelling_key(name: str) -> str:
    """Nombre sin tildes, signos ni espacios: dos variantes con la misma clave solo difieren en la
    escritura ('S.A.C.' frente a 'SAC', 'PERÚ' frente a 'PERU')."""
    return "".join(ch for ch in normalize_text(name) if ch.isalnum())


def names_by_ruc(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for kind, ruc, name in [("proveedor", "ruc_proveedor", "proveedor"), ("entidad", "ruc_entidad", "entidad")]:
        g = df.sort_values("fecha_formalizacion").groupby(ruc)
        variants = g[name].agg(lambda s: list(dict.fromkeys(s)))
        multi = variants[variants.str.len() > 1]
        for key, names in multi.items():
            same_spelling = len({spelling_key(n) for n in names}) == 1
            rows.append({"tipo": kind, "ruc": key, "nombres": len(names),
                         "variacion": "solo_escritura" if same_spelling else "nombre_distinto",
                         "nombre_mas_reciente": names[-1], "variantes": " | ".join(names)})
    return pd.DataFrame(rows)


def names_with_many_rucs(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("entidad").agg(rucs=("ruc_entidad", "nunique"), lista=("ruc_entidad", lambda s: " | ".join(sorted(set(s)))),
                                   ordenes=("orden", "size"))
    return g[g["rucs"] > 1].sort_values("rucs", ascending=False).reset_index()


def frameworks(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(["acuerdo_marco", "codigo_acuerdo", "clave_catalogo"], dropna=False).agg(
        catalogo=("catalogo", "first"), rubro=("rubro", "first"),
        desde=("periodo_archivo", "min"), hasta=("periodo_archivo", "max"),
        ordenes=("orden", "size"), monto=("total", "sum"))
    return g.reset_index().sort_values(["catalogo", "desde"])


# ---------------------------------------------------------------------------------------------

def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    config.QUALITY.mkdir(parents=True, exist_ok=True)

    raw, files = load()
    df = clean(raw)
    months = profile_months(raw, df, files)
    official = validate.compare(df)
    rules = run_rules(raw, df, months, official)
    flagged, thresholds = outliers(df)

    profile_columns(raw, df).to_csv(config.QUALITY / "perfilado_columnas.csv", index=False)
    months.to_csv(config.QUALITY / "perfilado_mensual.csv", index=False)
    rules.to_csv(config.QUALITY / "reglas.csv", index=False)
    flagged.to_csv(config.QUALITY / "atipicos.csv", index=False)
    names_by_ruc(df).to_csv(config.QUALITY / "nombres_por_ruc.csv", index=False)
    names_with_many_rucs(df).to_csv(config.QUALITY / "nombres_con_varios_ruc.csv", index=False)
    frameworks(df).to_csv(config.QUALITY / "acuerdos_marco.csv", index=False)
    official.to_csv(config.REPORTS / "validaciones.csv", index=False)

    print(f"Órdenes: {len(df):,} en {len(months)} archivos; monto S/ {df['total'].sum() / 1e6:,.1f} millones")
    print(rules.groupby(["dimension", "resultado"]).size().unstack(fill_value=0).to_string())
    print(f"Atípicos: {flagged['motivo'].value_counts().to_dict()} (umbrales {thresholds})")
    failed = rules[rules["resultado"] == "falla"]
    for row in failed.itertuples():
        print(f"  ✗ {row.id} {row.regla}: {row.fallan} de {row.evaluadas}")
    return 1 if len(failed) else 0


if __name__ == "__main__":
    sys.exit(main())
