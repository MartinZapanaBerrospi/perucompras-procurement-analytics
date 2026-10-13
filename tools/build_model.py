"""Genera el modelo semántico de Power BI (TMDL) a partir de data/curated.

Escribe powerbi/perucompras.SemanticModel/: tablas con su consulta de Power Query, relaciones y
medidas DAX. Los identificadores (lineageTag) se derivan del nombre de cada objeto, así que
regenerar el modelo produce exactamente los mismos archivos.

Las medidas están documentadas en docs/04_modelado.md y validadas contra Python en
tools/validate_measures.py.

Uso:
    python tools/build_model.py
"""

import re
import shutil
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import config  # noqa: E402

NAME = "perucompras"
CUTOFF_MONTH = config.END[1]                                    # último mes con datos (9 = setiembre)
LAST_FULL_YEAR = config.END[0] if config.END[1] == 12 else config.END[0] - 1
MONTHS_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "setiembre",
             "octubre", "noviembre", "diciembre"]
MODEL = ROOT / "powerbi" / f"{NAME}.SemanticModel"
NS = uuid.UUID("6f1c2a52-3b7e-4f1a-9c53-2c9a1b0e7d11")


def tag(*parts: str) -> str:
    return str(uuid.uuid5(NS, "/".join(parts)))


# ---------------------------------------------------------------------------------------------
# Tablas: (columna, tipo TMDL, tipo M, opciones)
# ---------------------------------------------------------------------------------------------

M_TYPES = {"string": "type text", "int64": "Int64.Type", "double": "type number", "dateTime": "type date"}

TABLES = {
    "dim_fecha": {
        "description": "Calendario de 2022-01-01 a 2026-09-30, en español.",
        "data_category": "Time",
        "columns": [
            ("fecha", "dateTime", {"key": True, "format": "dd/mm/yyyy"}),
            ("anio", "int64", {"format": "0", "description": "Año"}),
            ("trimestre", "string", {}),
            ("mes", "int64", {"hidden": True}),
            ("mes_nombre", "string", {"sort_by": "mes"}),
            ("anio_mes", "string", {}),
            ("mes_inicio", "dateTime", {"format": "mmm yyyy", "description": "Primer día del mes"}),
            ("dia_semana", "string", {"sort_by": "dia_semana_num"}),
            ("dia_semana_num", "int64", {"hidden": True}),
            ("es_fin_de_semana", "int64", {"hidden": True}),
        ],
    },
    "dim_entidad": {
        "description": "Entidad pública que compra, identificada por su RUC. Nombre más reciente; "
                       "entidad_unica agrega el RUC cuando dos entidades comparten nombre.",
        "columns": [
            ("ruc_entidad", "string", {"key": True}),
            ("entidad", "string", {}),
            ("entidad_unica", "string", {"description": "Nombre para mostrar; único en todo el modelo"}),
            ("nombres_historicos", "int64", {"hidden": True}),
            ("primera_orden", "dateTime", {"format": "dd/mm/yyyy"}),
            ("ultima_orden", "dateTime", {"format": "dd/mm/yyyy"}),
        ],
    },
    "dim_proveedor": {
        "description": "Proveedor homologado en los Catálogos Electrónicos, identificado por su RUC.",
        "columns": [
            ("ruc_proveedor", "string", {"key": True}),
            ("proveedor", "string", {}),
            ("proveedor_unico", "string", {"description": "Nombre para mostrar; único en todo el modelo"}),
            ("tipo_persona", "string", {}),
            ("nombres_historicos", "int64", {"hidden": True}),
            ("primera_orden", "dateTime", {"format": "dd/mm/yyyy"}),
            ("ultima_orden", "dateTime", {"format": "dd/mm/yyyy"}),
        ],
    },
    "dim_catalogo": {
        "description": "Catálogo electrónico estable (29) y su rubro (10). Ver data/reference/catalogos.csv.",
        "columns": [
            ("catalogo_id", "int64", {"key": True, "hidden": True}),
            ("catalogo", "string", {}),
            ("rubro", "string", {}),
            ("vigente_desde", "string", {}),
            ("vigente_hasta", "string", {}),
            ("con_compras_al_corte", "int64", {"hidden": True}),
        ],
    },
    "dim_estado": {
        "description": "Estado de la orden al corte del archivo. compra_efectiva = 0 para nulas y resueltas.",
        "columns": [
            ("estado_id", "string", {"key": True, "hidden": True}),
            ("estado", "string", {}),
            ("compra_efectiva", "int64", {}),
        ],
    },
    "fact_orden": {
        "description": "Una fila por orden de compra de bienes formalizada (2022-01 a 2026-09).",
        "columns": [
            ("orden", "string", {"key": True}),
            ("fecha", "dateTime", {"hidden": True, "format": "dd/mm/yyyy"}),
            ("ruc_entidad", "string", {"hidden": True}),
            ("ruc_proveedor", "string", {"hidden": True}),
            ("catalogo_id", "int64", {"hidden": True}),
            ("estado_id", "string", {"hidden": True}),
            ("gran_compra", "int64", {"description": "1 = Gran Compra; 0 = Compra ordinaria"}),
            ("igv", "double", {"hidden": True, "format": "#,##0.00"}),
            ("total", "double", {"hidden": True, "format": "#,##0.00"}),
            ("igv_exonerado", "int64", {"hidden": True}),
            ("igv_parcial", "int64", {"hidden": True}),
            ("atipico_alto", "int64", {"hidden": True}),
            ("atipico_bajo", "int64", {"hidden": True}),
            ("ordinaria_sobre_umbral", "int64", {"hidden": True}),
            ("posible_fraccionamiento", "int64", {"hidden": True}),
            ("tramo_umbral_miles", "int64", {
                "expression": "IF (\n    fact_orden[gran_compra] = 0 && fact_orden[total] >= 80000 && fact_orden[total] < 120000,\n"
                              "    INT ( fact_orden[total] / 1000 )\n)",
                "description": "Compras ordinarias de S/ 80 000 a 119 999, en tramos de S/ 1 000 (80 = S/ 80 000–80 999). "
                               "Sirve para ver el comportamiento alrededor del umbral de la Gran Compra.",
                "format": "0"}),
        ],
    },
}

RELATIONSHIPS = [
    ("fact_orden", "fecha", "dim_fecha", "fecha"),
    ("fact_orden", "ruc_entidad", "dim_entidad", "ruc_entidad"),
    ("fact_orden", "ruc_proveedor", "dim_proveedor", "ruc_proveedor"),
    ("fact_orden", "catalogo_id", "dim_catalogo", "catalogo_id"),
    ("fact_orden", "estado_id", "dim_estado", "estado_id"),
]

# ---------------------------------------------------------------------------------------------
# Medidas: (carpeta, nombre, expresión DAX, formato, descripción)
# ---------------------------------------------------------------------------------------------

MEASURES = [
    # 1. Compras (P1)
    ("1. Compras", "Monto", "SUM ( fact_orden[total] )", "#,##0",
     "Monto de las órdenes con IGV, en soles. Incluye todos los estados, como la cifra oficial."),
    ("1. Compras", "Monto (S/ millones)", "DIVIDE ( [Monto], 1e6 )", "#,##0.0", "Monto en millones de soles."),
    ("1. Compras", "Órdenes", "COUNTROWS ( fact_orden )", "#,##0", "Número de órdenes de compra."),
    ("1. Compras", "Ticket promedio", "DIVIDE ( [Monto], [Órdenes] )", "#,##0", "Monto promedio por orden, en soles."),
    ("1. Compras", "Ticket mediano", "MEDIAN ( fact_orden[total] )", "#,##0",
     "Monto de la orden típica: la mitad de las órdenes cuesta menos. Menos sensible a las compras enormes que el promedio."),
    ("1. Compras", "Entidades compradoras", "DISTINCTCOUNT ( fact_orden[ruc_entidad] )", "#,##0",
     "Entidades (RUC) con al menos una orden."),
    ("1. Compras", "Proveedores con ventas", "DISTINCTCOUNT ( fact_orden[ruc_proveedor] )", "#,##0",
     "Proveedores (RUC) con al menos una orden."),
    ("1. Compras", "Monto compra efectiva", "CALCULATE ( [Monto], dim_estado[compra_efectiva] = 1 )", "#,##0",
     "Monto sin órdenes nulas ni resueltas."),
    ("1. Compras", "Monto mismo periodo año anterior",
     "CALCULATE ( [Monto], DATEADD ( dim_fecha[fecha], -1, YEAR ) )", "#,##0",
     "Monto de las mismas fechas un año antes. En 2026 compara enero–setiembre con enero–setiembre de 2025."),
    ("1. Compras", "Var. interanual",
     "VAR antes = [Monto mismo periodo año anterior]\nRETURN\n"
     "    IF ( HASONEVALUE ( dim_fecha[anio] ) && NOT ISBLANK ( antes ), DIVIDE ( [Monto] - antes, antes ) )",
     "+0.0%;-0.0%;0.0%",
     "Variación del monto frente a las mismas fechas del año anterior. Solo con un año elegido: sobre varios años no tiene sentido."),
    ("1. Compras", "Monto ene–set (S/ millones)",
     f"CALCULATE ( [Monto (S/ millones)], dim_fecha[mes] <= {CUTOFF_MONTH} )", "#,##0.0",
     f"Monto de enero a {MONTHS_ES[CUTOFF_MONTH - 1]} de cada año: compara los años completos con el último, "
     "que llega hasta el corte."),
    ("1. Compras", "Proveedores con ventas ene–set",
     f"CALCULATE ( [Proveedores con ventas], dim_fecha[mes] <= {CUTOFF_MONTH} )", "#,##0",
     f"Proveedores con al menos una orden entre enero y {MONTHS_ES[CUTOFF_MONTH - 1]}, para comparar años."),
    ("1. Compras", "Participación en el monto",
     "DIVIDE ( [Monto], CALCULATE ( [Monto], ALLSELECTED () ) )", "0.0%",
     "Parte del monto total de lo que está seleccionado."),

    # 2. Concentración (P2)
    ("2. Concentración", "Participación del proveedor",
     "DIVIDE ( [Monto], CALCULATE ( [Monto], REMOVEFILTERS ( dim_proveedor ) ) )", "0.0%",
     "Parte del monto que se lleva el proveedor dentro del contexto (catálogo, periodo)."),
    ("2. Concentración", "HHI",
     "VAR total = [Monto]\nRETURN\n    SUMX (\n        VALUES ( fact_orden[ruc_proveedor] ),\n        VAR p = DIVIDE ( CALCULATE ( [Monto] ), total ) * 100\n        RETURN p * p\n    )",
     "#,##0", "Índice Herfindahl-Hirschman: suma de las participaciones al cuadrado (0 a 10 000). Leerlo por catálogo."),
    ("2. Concentración", "Nivel de concentración",
     "VAR h = [HHI]\nRETURN\n    SWITCH ( TRUE (), ISBLANK ( h ), BLANK (), h < 1500, \"Baja\", h < 2500, \"Moderada\", \"Alta\" )",
     None, "Lectura del HHI: menos de 1 500 baja, 1 500 a 2 500 moderada, más de 2 500 alta."),
    ("2. Concentración", "Participación top 3 proveedores",
     "VAR mayores = TOPN ( 3, VALUES ( fact_orden[ruc_proveedor] ), CALCULATE ( [Monto] ), DESC )\nRETURN\n    DIVIDE ( CALCULATE ( [Monto], mayores ), [Monto] )",
     "0.0%", "Parte del monto que se llevan los 3 mayores proveedores del contexto."),
    ("2. Concentración", "Participación top 10 proveedores",
     "VAR mayores = TOPN ( 10, VALUES ( fact_orden[ruc_proveedor] ), CALCULATE ( [Monto] ), DESC )\nRETURN\n    DIVIDE ( CALCULATE ( [Monto], mayores ), [Monto] )",
     "0.0%", "Parte del monto que se llevan los 10 mayores proveedores del contexto."),
    ("2. Concentración", "Proveedores para el 80 %",
     "VAR t = ADDCOLUMNS ( VALUES ( fact_orden[ruc_proveedor] ), \"@m\", CALCULATE ( [Monto] ) )\n"
     "VAR total = SUMX ( t, [@m] )\n"
     "VAR conAcumulado =\n    ADDCOLUMNS ( t, \"@antes\", VAR m = [@m] RETURN SUMX ( FILTER ( t, [@m] > m ), [@m] ) )\n"
     "RETURN\n    COUNTROWS ( FILTER ( conAcumulado, [@antes] < 0.8 * total ) )",
     "#,##0", "Menor número de proveedores que, ordenados de mayor a menor, acumulan el 80 % del monto."),
    ("2. Concentración", "Proveedor líder",
     "VAR t = ADDCOLUMNS ( VALUES ( dim_proveedor[proveedor_unico] ), \"@m\", CALCULATE ( [Monto] ) )\n"
     "RETURN\n    MAXX ( TOPN ( 1, t, [@m], DESC ), dim_proveedor[proveedor_unico] )",
     None, "Proveedor con mayor monto en el contexto."),
    ("2. Concentración", "Participación del líder",
     "VAR t = ADDCOLUMNS ( VALUES ( fact_orden[ruc_proveedor] ), \"@m\", CALCULATE ( [Monto] ) )\n"
     "RETURN\n    DIVIDE ( MAXX ( t, [@m] ), [Monto] )",
     "0.0%", "Parte del monto que se lleva el mayor proveedor del contexto."),

    # 3. Entidades (P3)
    ("3. Entidades", "Participación de la entidad",
     "DIVIDE ( [Monto], CALCULATE ( [Monto], REMOVEFILTERS ( dim_entidad ) ) )", "0.0%",
     "Parte del monto que compró la entidad dentro del contexto."),
    ("3. Entidades", "Participación top 10 entidades",
     "VAR mayores = TOPN ( 10, VALUES ( fact_orden[ruc_entidad] ), CALCULATE ( [Monto] ), DESC )\nRETURN\n    DIVIDE ( CALCULATE ( [Monto], mayores ), [Monto] )",
     "0.0%", "Parte del monto que compran las 10 mayores entidades del contexto."),
    ("3. Entidades", "Catálogos usados",
     "DISTINCTCOUNT ( fact_orden[catalogo_id] )", "#,##0", "Número de catálogos con compras en el contexto."),

    # 4. Calendario (P4)
    ("4. Calendario", "Participación del mes en el año",
     "DIVIDE ( [Monto], CALCULATE ( [Monto], ALLEXCEPT ( dim_fecha, dim_fecha[anio] ) ) )", "0.0%",
     "Parte del monto del año que se compró en el mes. Solo tiene sentido en años completos (2022 a 2025)."),
    ("4. Calendario", "Participación promedio del mes",
     f"AVERAGEX (\n    FILTER ( VALUES ( dim_fecha[anio] ), dim_fecha[anio] <= {LAST_FULL_YEAR} ),\n"
     "    [Participación del mes en el año]\n)",
     "0.0%", f"Promedio, entre 2022 y {LAST_FULL_YEAR}, de la parte del monto anual que se compra en el mes."),
    ("4. Calendario", "Participación del mes (años completos)",
     f"IF ( MAX ( dim_fecha[anio] ) <= {LAST_FULL_YEAR}, [Participación del mes en el año] )", "0.0%",
     f"Igual que Participación del mes en el año, pero en blanco para {LAST_FULL_YEAR + 1}, que aún no termina."),
    ("4. Calendario", "Participación del último trimestre",
     "DIVIDE (\n    CALCULATE ( [Monto], dim_fecha[trimestre] = \"T4\" ),\n    CALCULATE ( [Monto], ALLEXCEPT ( dim_fecha, dim_fecha[anio] ) )\n)",
     "0.0%", "Parte del monto del año comprada de octubre a diciembre. Solo años completos."),
    ("4. Calendario", "Participación de diciembre",
     "DIVIDE (\n    CALCULATE ( [Monto], dim_fecha[mes] = 12 ),\n    CALCULATE ( [Monto], ALLEXCEPT ( dim_fecha, dim_fecha[anio] ) )\n)",
     "0.0%", "Parte del monto del año comprada en diciembre. Solo años completos."),

    # 5. Gran Compra (P5′)
    ("5. Gran Compra", "Monto Gran Compra", "CALCULATE ( [Monto], fact_orden[gran_compra] = 1 )", "#,##0",
     "Monto por el procedimiento de Gran Compra."),
    ("5. Gran Compra", "Monto compra ordinaria", "CALCULATE ( [Monto], fact_orden[gran_compra] = 0 )", "#,##0",
     "Monto por compra ordinaria."),
    ("5. Gran Compra", "% Gran Compra", "DIVIDE ( [Monto Gran Compra], [Monto] )", "0.0%",
     "Parte del monto que pasa por Gran Compra."),
    ("5. Gran Compra", "Órdenes ordinarias sobre el umbral",
     "CALCULATE ( [Órdenes], fact_orden[ordinaria_sobre_umbral] = 1 )", "#,##0",
     "Compras ordinarias de S/ 100 000 o más, el monto desde el cual la Gran Compra es obligatoria."),
    ("5. Gran Compra", "Monto ordinario sobre el umbral",
     "CALCULATE ( [Monto], fact_orden[ordinaria_sobre_umbral] = 1 )", "#,##0",
     "Monto de las compras ordinarias de S/ 100 000 o más."),
    ("5. Gran Compra", "Monto ordinario sobre el umbral (S/ millones)",
     "DIVIDE ( [Monto ordinario sobre el umbral], 1e6 )", "#,##0.0",
     "Monto ordinario sobre el umbral, en millones de soles."),
    ("5. Gran Compra", "Órdenes en posibles compras partidas",
     "CALCULATE ( [Órdenes], fact_orden[posible_fraccionamiento] = 1 )", "#,##0",
     "Compras ordinarias que, con otras de la misma entidad, proveedor, catálogo y día, superan juntas S/ 100 000 "
     "aunque cada una esté por debajo. Es una señal para revisar, no una prueba de fraccionamiento."),
    ("5. Gran Compra", "Monto en posibles compras partidas (S/ millones)",
     "DIVIDE ( CALCULATE ( [Monto], fact_orden[posible_fraccionamiento] = 1 ), 1e6 )", "#,##0.0",
     "Monto de las órdenes en posibles compras partidas, en millones de soles."),
    ("5. Gran Compra", "Órdenes en el tramo",
     "IF ( NOT ISBLANK ( SELECTEDVALUE ( fact_orden[tramo_umbral_miles] ) ), [Órdenes] )", "#,##0",
     "Órdenes del tramo de S/ 1 000; en blanco fuera de los tramos, para que el histograma no muestre el resto de órdenes."),
    ("5. Gran Compra", "% ordinario sobre el umbral",
     "DIVIDE ( [Monto ordinario sobre el umbral], [Monto compra ordinaria] )", "0.0%",
     "Parte del monto de compra ordinaria que supera el umbral de la Gran Compra."),

    # 6. Calidad de datos (marcas de la Fase 2)
    ("6. Calidad de datos", "Monto con IGV exonerado",
     "CALCULATE ( [Monto], fact_orden[igv_exonerado] = 1 )", "#,##0", "Monto de las órdenes sin IGV (Amazonía)."),
    ("6. Calidad de datos", "Órdenes atípicas altas",
     "CALCULATE ( [Órdenes], fact_orden[atipico_alto] = 1 )", "#,##0",
     "Órdenes de más de S/ 3,44 millones: reales, pero pesan mucho en el total."),
    ("6. Calidad de datos", "% del monto en atípicos altos",
     "DIVIDE ( CALCULATE ( [Monto], fact_orden[atipico_alto] = 1 ), [Monto] )", "0.0%",
     "Parte del monto que explican las órdenes atípicas altas."),
    ("6. Calidad de datos", "Órdenes que no son compra",
     "CALCULATE ( [Órdenes], dim_estado[compra_efectiva] = 0 )", "#,##0", "Órdenes nulas o resueltas."),

    # 7. Textos para el tablero
    ("7. Textos", "Corte de datos",
     "VAR f = CALCULATE ( MAX ( fact_orden[fecha] ), REMOVEFILTERS () )\nRETURN\n"
     "    \"Órdenes formalizadas hasta el \" & DAY ( f ) & \" de \" & LOWER ( FORMAT ( f, \"mmmm\", \"es-PE\" ) ) & \" de \" & YEAR ( f )",
     None, "Fecha de la última orden en los datos."),
    ("7. Textos", "Fuente",
     "\"Fuente: Perú Compras, órdenes de compra de los Catálogos Electrónicos (datosabiertos.gob.pe). Elaboración propia.\"",
     None, "Pie de fuente para cada página."),
]


# ---------------------------------------------------------------------------------------------
# Escritura
# ---------------------------------------------------------------------------------------------

def indent(text: str, tabs: int) -> str:
    return "\n".join("\t" * tabs + line if line else "" for line in text.splitlines())


def quote(name: str) -> str:
    """Nombres con espacios, tildes o signos van entre comillas simples en TMDL."""
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        return name
    return "'" + name.replace("'", "''") + "'"


def table_tmdl(name: str, spec: dict) -> str:
    out = [f"/// {spec['description']}", f"table {name}", f"\tlineageTag: {tag('table', name)}"]
    if spec.get("data_category"):
        out.append(f"\tdataCategory: {spec['data_category']}")
    out.append("")
    m_types = []
    for col, dtype, opts in spec["columns"]:
        if opts.get("description"):
            out.append(f"\t/// {opts['description']}")
        if opts.get("expression"):            # columna calculada en DAX
            out.append(f"\tcolumn {col} =")
            out.append(indent(opts["expression"], 3))
        else:
            out.append(f"\tcolumn {col}")
        out.append(f"\t\tdataType: {dtype}")
        if opts.get("key"):
            out.append("\t\tisKey")
        if opts.get("hidden"):
            out.append("\t\tisHidden")
        if opts.get("format"):
            out.append(f"\t\tformatString: {opts['format']}")
        out.append(f"\t\tlineageTag: {tag('column', name, col)}")
        out.append("\t\tsummarizeBy: none")
        if not opts.get("expression"):
            out.append(f"\t\tsourceColumn: {col}")
        if opts.get("sort_by"):
            out.append(f"\t\tsortByColumn: {opts['sort_by']}")
        out.append("")
        out.append("\t\tannotation SummarizationSetBy = Automatic")
        out.append("")
        if not opts.get("expression"):
            m_types.append(f'{{"{col}", {M_TYPES[dtype]}}}')
    m = (
        "let\n"
        f'    Origen = Csv.Document(File.Contents(RutaDatos & "{name}.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),\n'
        "    Encabezados = Table.PromoteHeaders(Origen, [PromoteAllScalars=true]),\n"
        f'    Tipos = Table.TransformColumnTypes(Encabezados, {{{", ".join(m_types)}}}, "en-US")\n'
        "in\n"
        "    Tipos"
    )
    out.append(f"\tpartition {name} = m")
    out.append("\t\tmode: import")
    out.append("\t\tsource =")
    out.append(indent(m, 4))
    out.append("")
    out.append("\tannotation PBI_ResultType = Table")
    out.append("")
    return "\n".join(out)


def measures_tmdl() -> str:
    out = ["table _Medidas", f"\tlineageTag: {tag('table', '_Medidas')}", ""]
    for folder, name, expr, fmt, desc in MEASURES:
        out.append(f"\t/// {desc}")
        if "\n" in expr:
            out.append(f"\tmeasure {quote(name)} =")
            out.append(indent(expr, 3))
        else:
            out.append(f"\tmeasure {quote(name)} = {expr}")
        if fmt:
            out.append(f"\t\tformatString: {fmt}")
        out.append(f"\t\tdisplayFolder: {folder}")
        out.append(f"\t\tlineageTag: {tag('measure', name)}")
        out.append("")
    out += ["\tcolumn Columna", "\t\tdataType: string", "\t\tisHidden",
            f"\t\tlineageTag: {tag('column', '_Medidas', 'Columna')}", "\t\tsummarizeBy: none",
            "\t\tisNameInferred", "\t\tsourceColumn: [Columna]", "",
            "\t\tannotation SummarizationSetBy = Automatic", "",
            "\tpartition _Medidas = calculated", "\t\tmode: import",
            '\t\tsource = ROW ( "Columna", BLANK () )', ""]
    return "\n".join(out)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    definition = MODEL / "definition"
    if definition.exists():
        shutil.rmtree(definition)
    names = list(TABLES)

    write(MODEL / ".platform", (
        '{\n  "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",\n'
        f'  "metadata": {{\n    "type": "SemanticModel",\n    "displayName": "{NAME}"\n  }},\n'
        f'  "config": {{\n    "version": "2.0",\n    "logicalId": "{tag("logical", "model")}"\n  }}\n}}\n'))
    write(MODEL / "definition.pbism", (
        '{\n  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",\n'
        '  "version": "4.2",\n  "settings": {}\n}\n'))
    write(definition / "database.tmdl", "database\n\tcompatibilityLevel: 1606\n\n")
    query_order = ", ".join(f'"{n}"' for n in ["RutaDatos", *names])
    write(definition / "model.tmdl", (
        "model Model\n\tculture: es-PE\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n"
        "\tdiscourageImplicitMeasures\n\tsourceQueryCulture: en-US\n\tdataAccessOptions\n"
        "\t\tlegacyRedirects\n\t\treturnErrorValuesAsNull\n\n"
        "annotation __PBI_TimeIntelligenceEnabled = 0\n\n"
        f"annotation PBI_QueryOrder = [{query_order}]\n\n"
        'annotation PBI_ProTooling = ["DevMode"]\n\n'
        + "".join(f"ref table {n}\n" for n in [*names, "_Medidas"]) + "\n"))
    curated = str(config.CURATED).replace("/", "\\") + "\\"
    write(definition / "expressions.tmdl", (
        "/// Carpeta data/curated del repositorio, con barra final. Cámbiala al clonar el proyecto en otra ruta.\n"
        f'expression RutaDatos = "{curated}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]\n'
        f"\tlineageTag: {tag('expression', 'RutaDatos')}\n\n\tannotation PBI_ResultType = Text\n\n"))
    write(definition / "relationships.tmdl", "".join(
        f"relationship {tag('relationship', f, fc)}\n\tfromColumn: {f}.{fc}\n\ttoColumn: {t}.{tc}\n\n"
        for f, fc, t, tc in RELATIONSHIPS))
    for name, spec in TABLES.items():
        write(definition / "tables" / f"{name}.tmdl", table_tmdl(name, spec))
    write(definition / "tables" / "_Medidas.tmdl", measures_tmdl())
    print(f"Modelo: {len(TABLES)} tablas, {len(RELATIONSHIPS)} relaciones, {len(MEASURES)} medidas -> "
          f"{MODEL}")


if __name__ == "__main__":
    main()
