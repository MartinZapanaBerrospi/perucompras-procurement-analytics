# Fase 5 — Análisis

> Estado: **cerrada** (2026-10-13).

Este documento responde las cinco preguntas de la [Fase 0](00_definicion.md) con cifras.

- **Reproducible.** Todo sale de [`src/analysis.py`](../src/analysis.py), que escribe una tabla de
  soporte por pregunta en [`reports/analisis/`](../reports/analisis/).
- **Igual al tablero.** Las cifras coinciden con las medidas DAX del tablero: una prueba automática
  ([`tests/test_analysis.py`](../tests/test_analysis.py)) lo comprueba catálogo por catálogo.

```bash
python -m src.analysis
```

**Regla para comparar años.** Los datos llegan hasta setiembre de 2026. Toda comparación que
incluye 2026 usa **enero–setiembre** de cada año. Comparar nueve meses contra doce haría parecer
que 2026 cae a la mitad.

## Resumen para gerencia

| # | Pregunta | Respuesta corta |
|---|---|---|
| P1 | ¿Cuánto se compra y en qué? | Unos **S/ 1 800 a 2 000 millones al año**, dos tercios en tecnología e impresión. El monto baja (−10,8 % de 2022 a 2025) y 2026 va **−21,2 %** frente a enero–setiembre de 2025. Hay menos órdenes, pero más grandes |
| P2 | ¿Dónde se depende de pocos proveedores? | **No en los catálogos que importan.** Los 7 más grandes (89 % del monto) tienen concentración baja. Pero **hay 35 % menos proveedores activos que en 2022** |
| P3 | ¿Quién compra? | **99 de 2 348 entidades (4 %) hacen la mitad del gasto.** EsSalud encabeza con S/ 288 millones |
| P4 | ¿Cuándo se compra? | **Un tercio del gasto anual se va de octubre a diciembre**; noviembre es el mes pico. Enero casi no existe (0,9 %) |
| P5′ | ¿Se usa la Gran Compra donde corresponde? | El 58 % del monto pasa por Gran Compra. Hay **tres señales de control**: 785 compras ordinarias sobre el umbral, un amontonamiento justo por debajo de S/ 100 000 y 854 casos de compras partidas el mismo día. Las tres **son menores en 2025 que en 2022** |

## P1. ¿Cuánto se compra, en qué y cómo cambia?

| Año | Monto (S/ millones) | Órdenes | Ticket mediano | Entidades | Proveedores |
|---|---|---|---|---|---|
| 2022 | 1 994,6 | 137 373 | S/ 1 941 | 1 902 | 2 097 |
| 2023 | 1 885,3 | 116 625 | S/ 3 040 | 1 887 | 2 170 |
| 2024 | 1 934,6 | 102 901 | S/ 3 073 | 1 828 | 2 317 |
| 2025 | 1 778,9 | 91 110 | S/ 3 015 | 1 836 | 1 693 |
| 2026 (ene–set) | 925,1 | 63 773 | S/ 2 685 | 1 750 | 1 275 |

**Enero–setiembre de cada año:** S/ 1 409 millones (2022), 1 157 (2023), 1 282 (2024), 1 174 (2025)
y **925 (2026)**. 2026 es el nivel más bajo de la serie, 21,2 % menos que el mismo periodo de
2025 ([`p1_enero_setiembre.csv`](../reports/analisis/p1_enero_setiembre.csv)).

**Menos órdenes, más grandes.** De 2022 a 2025 las órdenes caen 33,7 % y el monto solo 10,8 %. La
orden típica (mediana) sube de S/ 1 941 a S/ 3 015. El cambio ocurre de golpe en 2023: las
órdenes de menos de S/ 1 000 pasan del 33 % al 20 % del total y se mantienen ahí. Los datos no
dicen la causa; puede ser un cambio de reglas en los catálogos.

**En qué se gasta** ([`p1_rubros.csv`](../reports/analisis/p1_rubros.csv)). **Tecnología (37,8 %)**
e **Impresión y oficina (29,4 %)** suman dos tercios del monto. Le siguen Construcción y
electricidad (11,6 %) y Bienes diversos (7,1 %). Solo el catálogo de computadoras y escáneres
pesa el 36,8 % del periodo.

**Lectura para gerencia.** El monto anual es estable, pero 2026 viene claramente más bajo. Como
dos catálogos mueven la mitad del dinero, cualquier cambio en ellos mueve el total.

## P2. ¿En qué catálogos la venta depende de pocos proveedores?

El índice de concentración (HHI) suma las participaciones al cuadrado: va de casi 0 (muchos
proveedores pequeños) a 10 000 (un solo proveedor). Se lee **dentro de cada catálogo**, que es
donde compiten los proveedores ([`p2_catalogos.csv`](../reports/analisis/p2_catalogos.csv)).

**Los catálogos grandes son competitivos.** Los 7 catálogos con al menos 3 % del monto suman el
89 % del dinero y todos tienen concentración baja:

| Catálogo | Monto (S/ millones) | Proveedores | HHI | 3 mayores | Proveedores que hacen el 80 % |
|---|---|---|---|---|---|
| Computadoras y escáneres | 3 135,8 | 690 | 243 | 19,2 % | 73 |
| Impresoras y consumibles | 1 478,2 | 1 058 | 78 | 9,0 % | 198 |
| Útiles de escritorio y papeles | 1 030,0 | 905 | 172 | 15,9 % | 146 |
| Tuberías, pinturas y acabados | 839,7 | 637 | 179 | 16,6 % | 103 |
| Limpieza y aseo | 419,3 | 707 | 164 | 14,7 % | 103 |
| Bienes y herramientas diversos | 385,7 | 492 | 113 | 11,0 % | 100 |
| Llantas y neumáticos | 289,5 | 233 | 212 | 16,4 % | 50 |

**La concentración alta existe, pero donde casi no hay dinero.** 9 catálogos tienen concentración
moderada o alta, y juntos suman el 0,2 % del monto. Son catálogos chicos o de vida corta:
*Componentes fotovoltaicos* (14 proveedores, HHI 2 958), *Medidores eléctricos* (4 proveedores,
HHI 3 726), *Material de laboratorio clínico* (HHI 1 743).

**Lo que sí preocupa: hay menos proveedores vendiendo.** Comparando enero–setiembre
([`p2_catalogos_grandes_enero_setiembre.csv`](../reports/analisis/p2_catalogos_grandes_enero_setiembre.csv)):

| Proveedores activos | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|
| Todos los catálogos | 1 956 | 1 655 | 2 158 | 1 658 | **1 275** |
| Impresoras y consumibles | 658 | 481 | 558 | 403 | **321** |
| Útiles de escritorio y papeles | 580 | 426 | 521 | 381 | **311** |
| Computadoras y escáneres | 382 | 331 | 332 | 266 | **214** |

Son **35 % menos proveedores que en 2022**. En impresoras, la mitad. El HHI sigue bajo, pero sube
en *Útiles de escritorio* (de 139 a 480) y en *Llantas* (de 213 a 452). En *Computadoras*, el HHI
de 2026 (726) se explica por un proveedor con el 23 % del catálogo y por 8 órdenes muy grandes
que suman el 31 % del monto del año.

**Lectura para gerencia.** Hoy no hay dependencia de pocos proveedores en lo que importa, pero la
base de proveedores se está achicando. Si sigue así, la competencia dentro de los catálogos
grandes se va a resentir. Conviene vigilar el número de proveedores activos por catálogo, no solo
el HHI.

**Límite.** Menos proveedores activos no implica menos proveedores homologados: un proveedor puede
seguir en el catálogo y no recibir órdenes. Además, con menos órdenes es natural que vendan menos
proveedores.

## P3. ¿Qué entidades concentran el gasto?

([`p3_entidades_top30.csv`](../reports/analisis/p3_entidades_top30.csv))

- **El gasto está muy concentrado en pocas entidades.** 99 entidades (4,2 %) hacen la mitad del
  monto y 366 (15,6 %) hacen el 80 %. La entidad mediana gastó S/ 170 878 en todo 2025.
- **Las 10 mayores** compran el 14,4 % del total:

| Entidad | Monto (S/ millones) | Parte del total |
|---|---|---|
| Seguro Social de Salud (EsSalud) | 288,1 | 3,4 % |
| Ministerio Público | 138,4 | 1,6 % |
| Gobierno Regional Moquegua | 121,8 | 1,4 % |
| Poder Judicial | 114,4 | 1,3 % |
| SUNAT | 107,0 | 1,3 % |
| Gobierno Regional Cusco | 105,1 | 1,2 % |
| ONPE | 97,3 | 1,1 % |
| Gobierno Regional de Apurímac | 87,1 | 1,0 % |
| Plan MERISS Inka (Cusco) | 84,3 | 1,0 % |
| Policía Nacional del Perú | 82,3 | 1,0 % |

**Lectura para gerencia.** Para mejorar los catálogos, unas 100 entidades explican la mitad del
gasto: son las primeras a las que hay que escuchar. Para el jefe de logística de una entidad, el
tablero permite filtrar su RUC y ver su compra frente al total.

## P4. ¿Cómo se reparte la compra a lo largo del año?

Años completos 2022–2025 ([`p4_estacionalidad.csv`](../reports/analisis/p4_estacionalidad.csv)):

| | Ene | Feb | Mar | Abr | May | Jun | Jul | Ago | Set | Oct | Nov | Dic |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| % del año (promedio) | 0,9 | 4,5 | 9,0 | 9,2 | 9,0 | 7,5 | 8,1 | 8,3 | 9,5 | 11,0 | **12,5** | 10,4 |

- **El último trimestre concentra un tercio del gasto** (33,9 % en promedio; entre 29,4 % y
  38,6 %). Si el gasto fuera parejo, sería 25 %.
- **No hay un "diciembre de último minuto".** El pico es noviembre, y los últimos 10 días del año
  suman apenas 1,7 % del gasto anual. La carga de fin de año se reparte en todo el trimestre.
- **Enero casi no tiene compras** (0,9 %) y febrero muy pocas (4,5 %). Es el arranque del año
  fiscal, cuando los presupuestos todavía se están habilitando.

**Lectura para gerencia.** El trabajo de los proveedores y de soporte se concentra de octubre a
diciembre. Planificar compras desde marzo bajaría la presión del cierre de año.

## P5′. ¿Se usa la Gran Compra donde corresponde?

La **Gran Compra** es el procedimiento en el que el sistema invita a todos los proveedores del
catálogo y elige automáticamente la mejor oferta. Es **obligatoria desde S/ 100 000**
(Directiva N.° 006-2021-PERÚ COMPRAS). Por debajo, la entidad puede usar la compra ordinaria, en
la que elige el proveedor directamente.

**Cuánto pasa por Gran Compra** ([`p5_gran_compra_anual.csv`](../reports/analisis/p5_gran_compra_anual.csv)):
el 58,0 % del monto del periodo. Fue de 57,8 % en 2022, bajó a 54,4 % en 2023, subió a 60,5 % y
62,1 % en 2024 y 2025, y es de 53,0 % en enero–setiembre de 2026.

Los datos muestran **tres señales que merecen revisión**:

**1. Compras ordinarias por encima del umbral.** 785 órdenes, por S/ 121,4 millones: el 3,4 % del
monto de compra ordinaria. Se concentran en impresoras, llantas y limpieza.

**2. Un amontonamiento justo por debajo del umbral**
([`p5_umbral_histograma.csv`](../reports/analisis/p5_umbral_histograma.csv)). La cantidad de
compras ordinarias baja de forma suave a medida que el monto sube, hasta que llega al umbral:

| Monto de la compra ordinaria | Órdenes |
|---|---|
| S/ 90 000 – 98 999 (promedio por tramo de S/ 1 000) | 110 |
| **S/ 99 000 – 99 999** | **286** |
| S/ 100 000 – 100 999 | 20 |

Entre S/ 95 000 y S/ 99 999 hay 734 órdenes, cuando la tendencia de los tramos anteriores hacía
esperar unas 457: un **exceso de 277**. Es el patrón típico de compras que se ajustan para quedar
por debajo de un umbral.

**3. Posibles compras partidas** ([`p5_posible_fraccionamiento.csv`](../reports/analisis/p5_posible_fraccionamiento.csv)).
Hay **854 casos** en que la misma entidad hizo, el mismo día, al mismo proveedor y en el mismo
catálogo, dos o más compras ordinarias. Cada una estaba por debajo de S/ 100 000, pero juntas lo
superan. Suman 2 824 órdenes y S/ 124,3 millones. Los catálogos con más casos son impresoras
(201), útiles (180) y computadoras (147).

**Las tres señales son menores en 2025 que en 2022,** aunque no bajan todos los años (las compras sobre el umbral suben de 140 a 148 entre 2024 y 2025):

| | 2022 | 2023 | 2024 | 2025 | 2026 (ene–set) |
|---|---|---|---|---|---|
| Compras ordinarias sobre el umbral | 203 | 180 | 140 | 148 | 114 |
| Compras ordinarias de S/ 95 000 – 99 999 | 218 | 158 | 148 | 121 | 89 |
| (frente a S/ 90 000 – 94 999) | 145 | 115 | 112 | 92 | 79 |
| Casos de posibles compras partidas | 246 | 224 | 166 | 146 | 72 |

**Lectura para gerencia.** La Gran Compra se usa en la mayor parte del monto, y el
comportamiento cerca del umbral mejora año a año. Aun así, las órdenes justo por debajo de
S/ 100 000 y las compras partidas el mismo día son un buen punto de partida para el control: son
pocas, están identificadas y se pueden revisar una por una.

**Límites, sin rodeos.** Estas señales salen de reglas mecánicas aplicadas a datos públicos y
**no prueban ninguna irregularidad**:
- una compra ordinaria sobre el umbral puede tener una excepción válida que los datos no muestran;
- dos órdenes el mismo día pueden ser compras distintas: otro destino, otra área usuaria u otro
  requerimiento.

Por eso el proyecto muestra las cifras agregadas y deja el detalle disponible para quien deba
revisarlo.

## Límites generales del análisis

- **Solo bienes.** No incluye el catálogo de servicios (boletos aéreos), que Perú Compras ya no
  publica abiertamente.
- **Sin región ni tipo de gobierno.** Los archivos no traen la ubicación ni el nivel de gobierno
  de la entidad.
- **Sin precios unitarios.** Cada fila es una orden completa, así que no se puede comparar el
  precio de un mismo producto entre entidades.
- **Descriptivo, no causal.** El análisis describe qué pasó y cuánto. No estima por qué: por
  ejemplo, si la caída de 2026 se debe a recortes de presupuesto o a cambios en los catálogos.
