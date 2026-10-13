"""Páginas y visuales del informe de Power BI (PBIR), escritos por tools/build_report.py.

Lienzo de 1280 × 720 con márgenes de 24 px. Las cifras de los textos salen de
reports/analisis/cifras_clave.csv (Fase 5): el tablero no repite números escritos a mano.
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEY = {r["cifra"]: r["valor"] for r in csv.DictReader(
    (ROOT / "reports" / "analisis" / "cifras_clave.csv").open(encoding="utf-8"))}

INK, MUTED, PANEL = "#1b1f24", "#4a5058", "#ffffff"
ACCENT = "#1f5f99"


# ---------------------------------------------------------------------------------------------
# Formato de cifras en español del Perú
# ---------------------------------------------------------------------------------------------

def num(value, decimals: int = 0) -> str:
    """1234567.8 -> '1 234 568' ; con decimales usa coma: 2,5."""
    text = f"{float(value):,.{decimals}f}"
    return text.replace(",", " ").replace(".", ",")


def pct(value, decimals: int = 1) -> str:
    return f"{num(float(value) * 100, decimals)} %"


def millions(value, decimals: int = 1) -> str:
    return f"S/ {num(float(value) / 1e6, decimals)} millones"


def k(name: str) -> str:
    return KEY[name]


def proper(name: str) -> str:
    """'SEGURO SOCIAL DE SALUD' -> 'Seguro Social de Salud' (artículos y preposiciones en minúscula)."""
    small = {"de", "del", "la", "las", "el", "los", "y", "e", "en", "para", "por", "a"}
    words = name.lower().split()
    return " ".join(w if i and w in small else w.capitalize() for i, w in enumerate(words))


# ---------------------------------------------------------------------------------------------
# Piezas PBIR
# ---------------------------------------------------------------------------------------------

def lit(value: str) -> dict:
    return {"expr": {"Literal": {"Value": value}}}


def text(value: str) -> dict:
    return lit("'" + value.replace("'", "''") + "'")


def color(hex_code: str) -> dict:
    return {"solid": {"color": lit(f"'{hex_code}'")}}


def measure(name: str, display: str | None = None) -> dict:
    p = {"field": {"Measure": {"Expression": {"SourceRef": {"Entity": "_Medidas"}}, "Property": name}},
         "queryRef": f"_Medidas.{name}", "nativeQueryRef": name}
    if display:
        p["displayName"] = display
    return p


def column(entity: str, prop: str, display: str | None = None, active: bool = False) -> dict:
    p = {"field": {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
         "queryRef": f"{entity}.{prop}", "nativeQueryRef": prop}
    if display:
        p["displayName"] = display
    if active:
        p["active"] = True
    return p


def sort_by(projection: dict, direction: str = "Descending") -> dict:
    return {"sort": [{"field": projection["field"], "direction": direction}]}


def container(title: str | None = None, background: bool = True) -> dict:
    objects = {
        "background": [{"properties": {"show": lit("true" if background else "false"),
                                       **({"color": color(PANEL), "transparency": lit("0D")} if background else {})}}],
        "border": [{"properties": {"show": lit("false")}}],
        "dropShadow": [{"properties": {"show": lit("false")}}],
        "subTitle": [{"properties": {"show": lit("false")}}],
        "title": [{"properties": {"show": lit("false")}}],
    }
    if title:
        objects["title"] = [{"properties": {
            "show": lit("true"), "text": text(title), "fontSize": lit("11D"),
            "fontColor": color(INK), "bold": lit("false"), "fontFamily": text("Segoe UI Semibold")}}]
    return objects


def position(x, y, w, h) -> dict:
    return {"x": x, "y": y, "z": 0, "height": h, "width": w, "tabOrder": 0}


def visual(name: str, pos: dict, body: dict) -> dict:
    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.12.0/schema.json",
        "name": name, "position": pos, "visual": body,
    }


def textbox(name, x, y, w, h, paragraphs, background=False) -> dict:
    """paragraphs: lista de (texto, tamaño en pt, color, negrita)."""
    paras = []
    for content, size, hex_code, bold in paragraphs:
        paras.append({"textRuns": [{"value": content, "textStyle": {
            "fontFamily": "Segoe UI Semibold" if bold else "Segoe UI", "fontSize": f"{size}pt", "color": hex_code}}]})
    return visual(name, position(x, y, w, h), {
        "visualType": "textbox",
        "objects": {"general": [{"properties": {"paragraphs": paras}}]},
        "visualContainerObjects": container(background=background),
    })


def title(page_title: str, answer: str, width: int = 1016) -> dict:
    """Título (la pregunta) y subtítulo (la respuesta). Deja libre la esquina derecha para el segmentador."""
    return textbox("titulo", 24, 8, width, 72, [(page_title, 18, INK, True), (answer, 11, MUTED, False)])


def footer() -> dict:
    return textbox("fuente", 24, 690, 1232, 24, [(
        "Fuente: Perú Compras, órdenes de compra de bienes de los Catálogos Electrónicos "
        "(datosabiertos.gob.pe), enero 2022 – setiembre 2026. Montos con IGV. Elaboración propia.", 8, MUTED, False)])


def reading(name, x, y, w, h, heading, bullets, extra_heading=None, extra=None) -> dict:
    paras = [(heading, 11, INK, True)] + [("• " + b, 10, INK, False) for b in bullets]
    if extra_heading:
        paras += [(extra_heading, 11, INK, True)] + [("• " + b, 10, INK, False) for b in extra]
    return textbox(name, x, y, w, h, paras, background=True)


def card(name, x, y, w, h, measure_name, label) -> dict:
    return visual(name, position(x, y, w, h), {
        "visualType": "card",
        "query": {"queryState": {"Values": {"projections": [measure(measure_name)]}}},
        "objects": {
            "labels": [{"properties": {"fontSize": lit("22D"), "color": color(ACCENT),
                                       "fontFamily": text("Segoe UI Semibold"), "labelDisplayUnits": lit("1D")}}],
            "categoryLabels": [{"properties": {"show": lit("false")}}],
        },
        "visualContainerObjects": {**container(), "title": [{"properties": {
            "show": lit("true"), "text": text(label), "fontSize": lit("10D"), "fontColor": color(MUTED),
            "bold": lit("false"), "fontFamily": text("Segoe UI")}}]},
    })


def axis_objects(categorical: bool = False, labels: bool = False, legend: bool = False) -> dict:
    objects = {
        "categoryAxis": [{"properties": {"showAxisTitle": lit("false"), "gridlineShow": lit("false"),
                                         "labelColor": color(MUTED), "fontSize": lit("9D"),
                                         **({"axisType": text("Categorical")} if categorical else {})}}],
        # labelDisplayUnits 1 = sin abreviar: "3 135,8" y no "3,1 mil" (los montos ya están en millones)
        "valueAxis": [{"properties": {"showAxisTitle": lit("false"), "gridlineColor": color("#e9ecef"),
                                      "labelColor": color(MUTED), "fontSize": lit("9D"),
                                      "labelDisplayUnits": lit("1D")}}],
        "legend": [{"properties": {"show": lit("true" if legend else "false"), "position": text("Top"),
                                   "fontSize": lit("9D"), "labelColor": color(MUTED)}}],
    }
    if labels:
        objects["labels"] = [{"properties": {"show": lit("true"), "fontSize": lit("9D"), "color": color(INK),
                                             "labelDisplayUnits": lit("1D")}}]
    return objects


def chart(name, kind, x, y, w, h, chart_title, category, values, series=None, sort=None,
          categorical=False, labels=False, legend=False) -> dict:
    state = {"Category": {"projections": [category]}, "Y": {"projections": values}}
    if series:
        state["Series"] = {"projections": [series]}
    query = {"queryState": state}
    if sort:
        query["sortDefinition"] = sort
    return visual(name, position(x, y, w, h), {
        "visualType": kind, "query": query,
        "objects": axis_objects(categorical, labels, legend),
        "visualContainerObjects": container(chart_title),
    })


def table(name, x, y, w, h, table_title, projections, sort=None, widths=None) -> dict:
    """widths: ancho en píxeles de cada columna, en el orden de projections. Deben sumar menos que w."""
    query = {"queryState": {"Values": {"projections": projections}}}
    if sort:
        query["sortDefinition"] = sort
    objects = {
        "columnHeaders": [{"properties": {"fontSize": lit("9D"), "fontColor": color(INK), "wordWrap": lit("true")}}],
        "values": [{"properties": {"fontSize": lit("9D"), "wordWrap": lit("false")}}],
        "total": [{"properties": {"totals": lit("false")}}],
    }
    if widths:
        assert len(widths) == len(projections) and sum(widths) <= w - 40, name
        objects["columnWidth"] = [{"properties": {"value": lit(f"{width}D")}, "selector": {"metadata": p["queryRef"]}}
                                  for p, width in zip(projections, widths)]
    return visual(name, position(x, y, w, h), {
        "visualType": "tableEx", "query": query, "objects": objects,
        "visualContainerObjects": container(table_title),
    })


def slicer(name, x, y, w, h, entity, prop, header, order_prop=None) -> dict:
    query = {"queryState": {"Values": {"projections": [column(entity, prop, active=True)]}}}
    if order_prop:
        query["sortDefinition"] = sort_by(column(entity, order_prop), "Ascending")
    return visual(name, position(x, y, w, h), {
        "visualType": "slicer", "query": query,
        "objects": {
            "data": [{"properties": {"mode": text("Dropdown")}}],
            "selection": [{"properties": {"strictSingleSelect": lit("false"), "singleSelect": lit("false")}}],
            "header": [{"properties": {"show": lit("true"), "text": text(header)}}],
        },
        "visualContainerObjects": container(background=False),
    })


def year_slicer(x=1056) -> dict:
    return slicer("segmentador_anio", x, 12, 200, 64, "dim_fecha", "anio", "Año (vacío = todos)")


# ---------------------------------------------------------------------------------------------
# Páginas
# ---------------------------------------------------------------------------------------------

MONTO_M = measure("Monto (S/ millones)", "Monto (S/ millones)")

p1 = {"name": "p1_resumen", "displayName": "1. Resumen", "visuals": [
    title("Compras del Estado por Catálogos Electrónicos",
          "Resumen ejecutivo · órdenes de compra de bienes, enero 2022 – setiembre 2026"),
    year_slicer(),
    card("kpi_monto", 24, 88, 232, 92, "Monto (S/ millones)", "Monto comprado (S/ millones)"),
    card("kpi_ordenes", 274, 88, 232, 92, "Órdenes", "Órdenes de compra"),
    card("kpi_entidades", 524, 88, 232, 92, "Entidades compradoras", "Entidades que compraron"),
    card("kpi_proveedores", 774, 88, 232, 92, "Proveedores con ventas", "Proveedores que vendieron"),
    card("kpi_gran_compra", 1024, 88, 232, 92, "% Gran Compra", "Monto por Gran Compra"),
    chart("linea_mensual", "lineChart", 24, 196, 808, 300, "Monto mensual (S/ millones)",
          column("dim_fecha", "mes_inicio", "Mes", active=True), [MONTO_M]),
    chart("barras_rubro", "clusteredBarChart", 848, 196, 408, 300, "Monto por rubro (S/ millones)",
          column("dim_catalogo", "rubro", "Rubro", active=True), [MONTO_M], sort=sort_by(MONTO_M), labels=True),
    reading("lectura", 24, 512, 1232, 170, "Qué está pasando", [
        f"Se compran {millions(k('monto_2025'), 0)} al año (2025) y el monto viene bajando: "
        f"{pct(k('var_monto_2022_2025'))} desde 2022, y enero–setiembre de 2026 va {pct(k('var_ene_set_2026'))} "
        f"frente al mismo periodo de 2025.",
        f"{k('rubros_top2')} suman {pct(k('participacion_rubros_top2'), 0)} del monto. "
        f"Hay menos órdenes ({pct(k('var_ordenes_2022_2025'), 0)} entre 2022 y 2025), pero más grandes.",
        f"La competencia es amplia en los catálogos grandes, pero hay {pct(-float(k('var_proveedores_ene_set_2022_2026')), 0)} "
        "menos proveedores activos que en 2022.",
    ], "Qué conviene hacer", [
        "Vigilar el número de proveedores activos en los catálogos grandes, no solo su concentración.",
        f"Revisar las {num(k('ordinarias_95_100k_observadas'))} compras ordinarias de S/ 95 000 a S/ 99 999 y los "
        f"{num(k('grupos_posible_fraccionamiento'))} casos de posibles compras partidas (página 6).",
    ]),
    footer(),
]}

p2 = {"name": "p2_catalogos", "displayName": "2. Catálogos", "visuals": [
    title("¿En qué se compra y cómo cambia?",
          f"Dos rubros concentran {pct(k('participacion_rubros_top2'), 0)} del monto; las órdenes son menos y más grandes"),
    year_slicer(),
    chart("columnas_ene_set", "clusteredColumnChart", 24, 88, 400, 260, "Monto enero–setiembre (S/ millones)",
          column("dim_fecha", "anio", "Año", active=True), [measure("Monto ene–set (S/ millones)", "Monto ene–set")],
          categorical=True, labels=True),
    chart("columnas_ordenes", "clusteredColumnChart", 440, 88, 400, 260, "Órdenes por año (2026: enero–setiembre)",
          column("dim_fecha", "anio", "Año", active=True), [measure("Órdenes")], categorical=True, labels=True),
    chart("columnas_ticket", "clusteredColumnChart", 856, 88, 400, 260, "Ticket mediano por orden (S/)",
          column("dim_fecha", "anio", "Año", active=True), [measure("Ticket mediano")], categorical=True, labels=True),
    table("tabla_catalogos", 24, 364, 1232, 318, "Catálogos", [
        column("dim_catalogo", "rubro", "Rubro"),
        column("dim_catalogo", "catalogo", "Catálogo"),
        MONTO_M,
        measure("Participación en el monto", "% del monto"),
        measure("Órdenes"),
        measure("Ticket mediano", "Ticket mediano (S/)"),
        measure("Var. interanual", "Var. vs año anterior (elija un año)"),
    ], sort=sort_by(MONTO_M), widths=[220, 330, 140, 110, 110, 140, 140]),
    footer(),
]}

p3 = {"name": "p3_concentracion", "displayName": "3. Concentración", "visuals": [
    title("¿En qué catálogos la venta depende de pocos proveedores?",
          f"En ninguno de los grandes: los {k('catalogos_grandes')} que suman {pct(k('participacion_catalogos_grandes'), 0)} "
          f"del monto tienen concentración baja. Pero hay {pct(-float(k('var_proveedores_ene_set_2022_2026')), 0)} menos "
          "proveedores activos que en 2022"),
    year_slicer(),
    table("tabla_concentracion", 24, 88, 840, 490, "Concentración por catálogo", [
        column("dim_catalogo", "catalogo", "Catálogo"),
        MONTO_M,
        measure("Proveedores con ventas", "Proveedores"),
        measure("HHI"),
        measure("Nivel de concentración", "Concentración"),
        measure("Participación top 3 proveedores", "3 mayores"),
        measure("Proveedores para el 80 %", "Hacen el 80 %"),
        measure("Proveedor líder"),
    ], sort=sort_by(MONTO_M), widths=[185, 80, 85, 50, 90, 65, 70, 170]),
    chart("columnas_proveedores", "clusteredColumnChart", 880, 88, 376, 250, "Proveedores activos, enero–setiembre",
          column("dim_fecha", "anio", "Año", active=True), [measure("Proveedores con ventas ene–set", "Proveedores")],
          categorical=True, labels=True),
    textbox("como_leer", 880, 354, 376, 224, [
        ("Cómo leer el HHI", 11, INK, True),
        ("Suma de las participaciones de los proveedores al cuadrado: va de casi 0 (muchos proveedores "
         "pequeños) a 10 000 (uno solo).", 10, INK, False),
        ("Menos de 1 500: baja · 1 500 a 2 500: moderada · más de 2 500: alta.", 10, INK, False),
        ("Se lee dentro de cada catálogo, que es donde compiten los proveedores. Sobre todo el mercado "
         "daría casi 0 y no diría nada.", 10, MUTED, False),
    ], background=True),
    reading("lectura", 24, 594, 1232, 88, "Lectura", [
        f"La concentración alta existe solo en {k('catalogos_concentrados')} catálogos chicos, que suman "
        f"{pct(k('participacion_catalogos_concentrados'))} del monto. En impresoras, los proveedores activos bajaron de "
        f"{num(k('proveedores_impresoras_2022'))} a {num(k('proveedores_impresoras_2026'))} (enero–setiembre).",
    ]),
    footer(),
]}

p4 = {"name": "p4_entidades", "displayName": "4. Entidades", "visuals": [
    title("¿Qué entidades concentran el gasto?",
          f"{num(k('entidades_para_50'))} de {num(k('entidades'))} entidades ({pct(k('pct_entidades_para_50'), 0)}) "
          "hacen la mitad del gasto. Elija una fila para ver en qué compra", width=800),
    slicer("segmentador_catalogo", 840, 12, 200, 64, "dim_catalogo", "catalogo", "Catálogo (vacío = todos)"),
    year_slicer(),
    card("kpi_entidades", 24, 88, 260, 92, "Entidades compradoras", "Entidades que compraron"),
    card("kpi_top10", 300, 88, 260, 92, "Participación top 10 entidades", "Parte de las 10 mayores"),
    card("kpi_monto", 576, 88, 268, 92, "Monto (S/ millones)", "Monto (S/ millones)"),
    table("tabla_entidades", 24, 196, 820, 486, "Entidades por monto", [
        column("dim_entidad", "entidad_unica", "Entidad"),
        column("dim_entidad", "ruc_entidad", "RUC"),
        MONTO_M,
        measure("Participación de la entidad", "% del monto"),
        measure("Órdenes"),
        measure("Catálogos usados", "Catálogos"),
    ], sort=sort_by(MONTO_M), widths=[320, 100, 105, 85, 70, 85]),
    chart("barras_rubro", "clusteredBarChart", 860, 88, 396, 400, "En qué compra la selección (S/ millones)",
          column("dim_catalogo", "rubro", "Rubro", active=True), [MONTO_M], sort=sort_by(MONTO_M), labels=True),
    reading("lectura", 860, 504, 396, 178, "Lectura", [
        f"{proper(k('entidad_lider'))} encabeza con {millions(k('monto_entidad_lider'))} "
        f"({pct(k('participacion_entidad_lider'))} del total).",
        f"La entidad mediana compró {('S/ ' + num(k('gasto_anual_mediano_entidad_2025')))} en todo 2025.",
        "Las entidades que comparten nombre llevan su RUC al lado.",
    ]),
    footer(),
]}

p5 = {"name": "p5_calendario", "displayName": "5. Calendario", "visuals": [
    title("¿Cómo se reparte la compra a lo largo del año?",
          f"Un tercio del gasto anual ({pct(k('participacion_t4_prom'), 0)}) se va de octubre a diciembre; "
          f"enero casi no tiene compras ({pct(k('participacion_enero'))})"),
    chart("columnas_mes", "clusteredColumnChart", 24, 88, 808, 300, "Parte del monto anual por mes (promedio 2022–2025)",
          column("dim_fecha", "mes_nombre", "Mes", active=True), [measure("Participación promedio del mes", "% del año")],
          labels=True),
    chart("lineas_anio", "lineChart", 848, 88, 408, 300, "Parte del monto anual por mes, cada año",
          column("dim_fecha", "mes_nombre", "Mes", active=True), [measure("Participación del mes (años completos)", "% del año")],
          series=column("dim_fecha", "anio", "Año"), legend=True),
    table("tabla_cierre", 24, 404, 600, 278, "Peso del cierre de año", [
        column("dim_fecha", "anio", "Año"),
        MONTO_M,
        measure("Participación del último trimestre", "Octubre–diciembre"),
        measure("Participación de diciembre", "Diciembre"),
    ], sort=sort_by(column("dim_fecha", "anio"), "Ascending"), widths=[80, 150, 150, 120]),
    reading("lectura", 640, 404, 616, 278, "Lectura", [
        f"Si el gasto fuera parejo, octubre–diciembre sería 25 %. Fue entre {pct(k('participacion_t4_min'), 0)} "
        f"y {pct(k('participacion_t4_max'), 0)} cada año.",
        f"El pico es noviembre ({pct(k('participacion_mes_pico'))}). No hay un diciembre de último minuto: los "
        f"últimos 10 días del año suman {pct(k('participacion_ultimos_10_dias_prom'))} del gasto.",
        f"Enero ({pct(k('participacion_enero'))}) y febrero ({pct(k('participacion_febrero'))}) son el arranque del "
        "año fiscal, con presupuestos todavía por habilitar.",
        "2026 queda fuera de los gráficos y de las columnas de cierre porque aún no termina.",
    ]),
    footer(),
]}

p6 = {"name": "p6_gran_compra", "displayName": "6. Gran Compra", "visuals": [
    title("¿Se usa la Gran Compra donde corresponde?",
          f"{pct(k('pct_gran_compra_total'), 0)} del monto pasa por Gran Compra (obligatoria desde S/ 100 000). "
          "Tres señales para revisar, las tres menores en 2025 que en 2022"),
    year_slicer(),
    card("kpi_gran_compra", 24, 88, 296, 92, "% Gran Compra", "Monto por Gran Compra"),
    card("kpi_sobre_umbral", 336, 88, 296, 92, "Órdenes ordinarias sobre el umbral", "Compras ordinarias de S/ 100 000 o más"),
    card("kpi_monto_umbral", 648, 88, 296, 92, "Monto ordinario sobre el umbral (S/ millones)",
         "Su monto (S/ millones)"),
    card("kpi_partidas", 960, 88, 296, 92, "Órdenes en posibles compras partidas", "Órdenes en posibles compras partidas"),
    chart("histograma_umbral", "clusteredColumnChart", 24, 196, 616, 300,
          "Compras ordinarias por monto (tramos de S/ 1 000, en miles de soles)",
          column("fact_orden", "tramo_umbral_miles", "Tramo (miles de S/)", active=True),
          [measure("Órdenes en el tramo", "Órdenes")]),
    chart("columnas_senales", "clusteredColumnChart", 656, 196, 600, 300, "Señales por año (2026: enero–setiembre)",
          column("dim_fecha", "anio", "Año", active=True),
          [measure("Órdenes ordinarias sobre el umbral", "Ordinarias sobre el umbral"),
           measure("Órdenes en posibles compras partidas", "En posibles compras partidas")],
          categorical=True, labels=True, legend=True),
    reading("lectura", 24, 512, 1232, 170, "Lectura", [
        f"Amontonamiento bajo el umbral: entre S/ 99 000 y S/ 99 999 hay {num(k('ordinarias_99_100k'))} compras "
        f"ordinarias, frente a unas {num(k('promedio_tramos_vecinos_90_99k'))} por tramo entre S/ 90 000 y S/ 98 999, y solo "
        f"{num(k('ordinarias_100_101k'))} entre S/ 100 000 y S/ 100 999.",
        f"Posibles compras partidas: {num(k('grupos_posible_fraccionamiento'))} casos en que la misma entidad hizo el mismo día, "
        "al mismo proveedor y en el mismo catálogo, dos o más compras ordinarias que juntas superan S/ 100 000 "
        f"({num(k('ordenes_posible_fraccionamiento'))} órdenes, {millions(k('monto_posible_fraccionamiento'))}).",
        "Son señales de reglas mecánicas sobre datos públicos y no prueban irregularidades: puede haber "
        "excepciones o compras distintas el mismo día. Sirven para priorizar la revisión.",
    ]),
    footer(),
]}

p7 = {"name": "p7_notas", "displayName": "7. Notas", "visuals": [
    title("Notas", "Definiciones, fuentes, validaciones y límites"),
    textbox("definiciones", 24, 88, 400, 594, [
        ("Definiciones", 11, INK, True),
        ("Monto: total de la orden con IGV, en soles. Incluye todos los estados, como la cifra oficial de "
         "Perú Compras.", 9, INK, False),
        ("Orden: una orden de compra de bienes formalizada en los Catálogos Electrónicos.", 9, INK, False),
        ("Ticket mediano: monto de la orden típica; la mitad de las órdenes cuesta menos.", 9, INK, False),
        ("HHI: suma de las participaciones de los proveedores al cuadrado, de 0 a 10 000, dentro de cada "
         "catálogo.", 9, INK, False),
        ("Gran Compra: procedimiento que invita a todos los proveedores del catálogo y elige automáticamente "
         "la mejor oferta. Obligatorio desde S/ 100 000 (Directiva N.° 006-2021-PERÚ COMPRAS).", 9, INK, False),
        ("Compra ordinaria sobre el umbral: compra ordinaria de S/ 100 000 o más.", 9, INK, False),
        ("Posible compra partida: dos o más compras ordinarias de la misma entidad, al mismo proveedor, en el "
         "mismo catálogo y el mismo día, cada una bajo S/ 100 000, que juntas lo superan.", 9, INK, False),
        ("Comparaciones con 2026: enero–setiembre de cada año.", 9, INK, False),
    ], background=True),
    textbox("fuentes", 440, 88, 400, 594, [
        ("Fuentes y validación", 11, INK, True),
        ("Datos: 57 archivos mensuales de órdenes de compra de bienes de Perú Compras, en la Plataforma "
         "Nacional de Datos Abiertos (datosabiertos.gob.pe).", 9, INK, False),
        ("Validación: el monto anual de bienes coincide con los boletines e Infocifras oficiales de Perú "
         "Compras de 2022 a 2025, por año y por tipo de procedimiento, con una diferencia máxima de 0,87 %.", 9, INK, False),
        ("Calidad: 59 reglas en seis dimensiones; ninguna regla bloqueante falla. 511 782 órdenes, sin "
         "repetidas; todos los RUC con dígito verificador válido.", 9, INK, False),
        ("Cada medida del tablero se comparó con el mismo cálculo en Python: cero diferencias.", 9, INK, False),
        ("Detalle, código y documentación de cada fase: github.com/MartinZapanaBerrospi/"
         "perucompras-procurement-analytics", 9, ACCENT, False),
    ], background=True),
    textbox("limites", 856, 88, 400, 594, [
        ("Límites", 11, INK, True),
        ("Solo bienes: el catálogo de servicios (boletos aéreos) ya no se publica abiertamente.", 9, INK, False),
        ("Sin región ni nivel de gobierno: los archivos no los traen.", 9, INK, False),
        ("Sin precios unitarios: cada fila es una orden completa, sin el detalle de productos.", 9, INK, False),
        ("Proveedores activos no es lo mismo que proveedores homologados: un proveedor puede estar en el "
         "catálogo y no recibir órdenes.", 9, INK, False),
        ("Las señales de la página 6 no prueban irregularidades.", 9, INK, False),
        ("El estado de pago de las órdenes no se usa: tuvo un quiebre entre noviembre de 2024 y mayo de 2025 "
         "por la actualización automática desde el SIAF.", 9, INK, False),
        ("Análisis descriptivo: dice qué pasó y cuánto, no por qué.", 9, INK, False),
    ], background=True),
    footer(),
]}

PAGES = [p1, p2, p3, p4, p5, p6, p7]
