# Perú Compras Procurement Analytics

[![CI](https://github.com/MartinZapanaBerrospi/perucompras-procurement-analytics/actions/workflows/ci.yml/badge.svg)](https://github.com/MartinZapanaBerrospi/perucompras-procurement-analytics/actions/workflows/ci.yml)
[![Datos: Perú Compras](https://img.shields.io/badge/Datos-Per%C3%BA%20Compras-C8102E)](https://www.datosabiertos.gob.pe/dataset/%C3%B3rdenes-de-compra-realizadas-trav%C3%A9s-de-los-cat%C3%A1logos-electr%C3%B3nicos-central-de-compras)
[![Power BI](https://img.shields.io/badge/Power%20BI-PBIP%20%2B%20TMDL-F2C811?logo=powerbi&logoColor=black)](powerbi/)
[![Python](https://img.shields.io/badge/Python-pandas-3776AB?logo=python&logoColor=white)](src/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Análisis de las **compras del Estado peruano por Catálogos Electrónicos de Acuerdos Marco**, de
enero de 2022 a setiembre de 2026: S/ 8 519 millones en 511 782 órdenes de compra de bienes. Se
hizo de punta a punta con **datos abiertos reales** de Perú Compras, desde 57 archivos mensuales
hasta un tablero de Power BI para gerencia.

**[Ver el tablero en Power BI →](https://app.powerbi.com/view?r=eyJrIjoiZjYzMGVmYjAtNWMwNS00Y2RkLTliM2UtZjk5ZmJkNmRmMWYzIiwidCI6IjFlYmE0NDNmLTIzZTUtNDUzNC05MGQxLTA5NzZhYWJlODZhYyIsImMiOjR9)**

![Página 1 del tablero: resumen ejecutivo de las compras por Catálogos Electrónicos](docs/img/01_resumen.png)

## La pregunta

¿Cuánto y en qué compra el Estado por Catálogos Electrónicos, qué tan concentrada está la venta
en cada catálogo, quién compra, en qué momento del año, y si se usa la Gran Compra donde
corresponde?

**Para quién es el tablero.** Para la gerencia que administra los acuerdos marco y prepara el
reporte de gestión. El jefe de logística de una entidad puede filtrar su RUC y ver su compra
frente al resto.

## Hallazgos

Datos hasta el 30 de setiembre de 2026. Las comparaciones con 2026 usan enero–setiembre de cada
año.

1. **Un mercado de unos S/ 1 800 a 2 000 millones al año, concentrado en dos rubros.**
   - Tecnología (37,8 %) e Impresión y oficina (29,4 %) suman dos tercios del monto.
   - Solo el catálogo de computadoras y escáneres pesa el 36,8 %.
2. **Las compras bajan, con menos órdenes pero más grandes.**
   - El monto cae 10,8 % de 2022 a 2025.
   - Enero–setiembre de 2026 suma S/ 925 millones: 21,2 % menos que el mismo periodo de 2025 y el
     nivel más bajo de la serie.
   - Las órdenes bajan 33,7 % entre 2022 y 2025, mientras la orden típica sube de S/ 1 941 a
     S/ 3 015.
3. **La competencia es amplia, pero la base de proveedores se achica.**
   - Los 7 catálogos más grandes (89 % del monto) tienen concentración baja: su índice HHI no pasa
     de 243.
   - La concentración alta solo aparece en 9 catálogos chicos, que suman el 0,2 % del monto.
   - Hay **35 % menos proveedores activos** que en 2022 (1 956 → 1 275). En impresoras, la mitad
     (658 → 321).
4. **El 4 % de las entidades hace la mitad del gasto.** 99 de 2 348 entidades concentran el 50 %
   del monto. EsSalud encabeza con S/ 288 millones (3,4 %).
5. **Un tercio del gasto anual se va de octubre a diciembre.** Es el 33,9 % en promedio; si el
   gasto fuera parejo, sería 25 %. El pico es noviembre (12,5 %). No hay un "diciembre de último
   minuto": los últimos 10 días del año suman 1,7 %. Enero casi no tiene compras (0,9 %).
6. **El 58 % del monto pasa por Gran Compra, y hay tres señales para revisar:**
   - 785 compras ordinarias de S/ 100 000 o más (S/ 121 millones), cuando desde ese monto la Gran
     Compra es obligatoria;
   - un amontonamiento justo debajo del umbral: entre S/ 99 000 y S/ 99 999 hay 286 compras
     ordinarias, frente a unas 110 en cada tramo vecino y 20 justo encima;
   - 854 casos de posibles compras partidas el mismo día (S/ 124 millones).

   Las tres señales **son menores en 2025 que en 2022** (por ejemplo, las posibles compras partidas
   bajan de 246 a 146 casos). **No prueban irregularidades**: salen de reglas mecánicas y sirven
   para priorizar la revisión.

## El tablero

**[Abrir el tablero publicado en Power BI](https://app.powerbi.com/view?r=eyJrIjoiZjYzMGVmYjAtNWMwNS00Y2RkLTliM2UtZjk5ZmJkNmRmMWYzIiwidCI6IjFlYmE0NDNmLTIzZTUtNDUzNC05MGQxLTA5NzZhYWJlODZhYyIsImMiOjR9)**: se navega en el navegador, sin instalar
nada. Las 7 páginas:

| | |
|---|---|
| ![Catálogos](docs/img/02_catalogos.png) **2. Catálogos.** Monto, órdenes y ticket mediano por año; los 29 catálogos. | ![Concentración](docs/img/03_concentracion.png) **3. Concentración.** HHI, 3 mayores y proveedores para el 80 % por catálogo; proveedores activos por año. |
| ![Entidades](docs/img/04_entidades.png) **4. Entidades.** Las 2 348 entidades por monto; al elegir una, en qué compra. | ![Calendario](docs/img/05_calendario.png) **5. Calendario.** Parte del gasto anual por mes y peso del cierre de año. |
| ![Gran Compra](docs/img/06_gran_compra.png) **6. Gran Compra.** Compras ordinarias alrededor de S/ 100 000 y señales por año. | ![Notas](docs/img/07_notas.png) **7. Notas.** Definiciones, fuentes, validación y límites. |

Para abrirlo en Power BI Desktop, ver [powerbi/README.md](powerbi/README.md).

## Glosario

- **Catálogo Electrónico de Acuerdo Marco:** tienda virtual del Estado. La entidad compra bienes
  estandarizados a proveedores ya homologados por Perú Compras, sin hacer un proceso de selección.
- **Compra ordinaria:** la entidad elige el proveedor directamente.
- **Gran Compra:** el sistema invita a todos los proveedores del catálogo y elige automáticamente
  la mejor oferta. Es obligatoria desde S/ 100 000 (Directiva N.° 006-2021-PERÚ COMPRAS).
- **HHI (índice Herfindahl-Hirschman):** suma de las participaciones de los proveedores al cuadrado.
  Va de casi 0 (muchos proveedores pequeños) a 10 000 (uno solo). Bajo 1 500 se considera
  concentración baja.
- **Ticket mediano:** monto de la orden típica; la mitad de las órdenes cuesta menos.
- **Posible compra partida:** dos o más compras ordinarias de la misma entidad, al mismo proveedor,
  en el mismo catálogo y el mismo día. Cada una está debajo de S/ 100 000, pero juntas lo superan.

## Cómo se construyó

Cada fase tiene su documento, con lo que se hizo, lo que se encontró y lo que se decidió:

| Fase | Qué se hizo | Documento |
|---|---|---|
| 0. Definición | Pregunta, usuario, KPIs, alcance y lectura completa de los 57 archivos antes de comprometer nada | [00_definicion.md](docs/00_definicion.md) |
| 1. Adquisición | Registro idempotente de los 57 meses con manifiesto SHA-256; descarga en navegador porque el portal bloquea scripts | [01_adquisicion.md](docs/01_adquisicion.md) |
| 2. Calidad | Perfilado de 19 columnas, 59 reglas en seis dimensiones, 18 problemas con su decisión, atípicos, diccionario de datos | [02_calidad.md](docs/02_calidad.md) |
| 3. Transformación | raw → staging (Parquet) → modelo en estrella; linaje de filas y montos; integridad referencial | [03_transformacion.md](docs/03_transformacion.md) |
| 4. Modelado | PBIP con TMDL generado por script: 5 relaciones y 45 medidas DAX validadas contra Python | [04_modelado.md](docs/04_modelado.md) |
| 5. Análisis | Respuestas cuantificadas a las cinco preguntas, con tablas de soporte | [05_analisis.md](docs/05_analisis.md) |
| 6. Tablero | 7 páginas y 56 visuales generados por script, revisados página por página | [powerbi/README.md](powerbi/README.md) |
| 7. Hallazgos | Conclusiones de arriba | este README |
| 8. Automatización | 65 pruebas y validación contra cifras oficiales en GitHub Actions | [.github/workflows/ci.yml](.github/workflows/ci.yml) |
| 9. Publicación | Tablero publicado en la web de Power BI y enlazado en el portafolio | [enlace](https://app.powerbi.com/view?r=eyJrIjoiZjYzMGVmYjAtNWMwNS00Y2RkLTliM2UtZjk5ZmJkNmRmMWYzIiwidCI6IjFlYmE0NDNmLTIzZTUtNDUzNC05MGQxLTA5NzZhYWJlODZhYyIsImMiOjR9) |

**Lo que valida el resultado:**
- **Contra las cifras oficiales.** El monto de bienes coincide con los boletines e Infocifras de
  Perú Compras de **2022 a 2025**, por año y por tipo de procedimiento, con una diferencia máxima
  de 0,87 %. En 2022 la diferencia es de 0,001 %.
- **Entre el tablero y Python.** Cada medida DAX se comparó con el mismo cálculo en Python:
  **363 comparaciones, cero diferencias**.
- **Sin pérdidas en el camino.** El linaje demuestra que de los archivos originales al tablero no
  se pierde ni se duplica una orden ni un sol.

## Cómo reproducirlo

El portal de datos abiertos bloquea las descargas por script, y el proyecto no lo evade. El zip
del conjunto se baja una vez desde el navegador
(`https://www.datosabiertos.gob.pe/node/9587/dataset/download`) y se deja en `data/raw/descarga/`.
Después todo es automático:

```bash
pip install -r requirements.txt
python -m src.extract         # registra los 57 meses y verifica su hash
python -m src.quality         # perfilado y 59 reglas de calidad
python -m src.transform       # raw → staging → data/curated, con linaje
python -m src.validate        # compara con las cifras oficiales; falla si no cuadra
python -m src.analysis        # tablas de soporte del análisis
python tools/build_model.py   # modelo de Power BI (TMDL)
python tools/build_report.py  # informe de Power BI (PBIR)
pytest -q
```

Para ver solo el tablero no hace falta ejecutar nada: `data/curated/` viene en el repositorio.

## Estructura

```
├── src/
│   ├── config.py           # Periodo, rutas, reglas de negocio y tolerancias
│   ├── extract.py          # Fase 1: registro y verificación del manifiesto
│   ├── parse_ordenes.py    # Lectura y reglas de limpieza (las usan las Fases 2 y 3)
│   ├── quality.py          # Fase 2: perfilado y reglas de calidad
│   ├── transform.py        # Fase 3: modelo en estrella, marcas y linaje
│   ├── validate.py         # Comparación con las cifras oficiales
│   └── analysis.py         # Fase 5
├── tools/                  # Generadores del modelo y del informe, validación de medidas, capturas
├── data/
│   ├── raw/manifest.csv    # Trazabilidad de cada archivo (los archivos no se versionan)
│   ├── reference/          # Catálogos estables, cifras oficiales, inventario del portal
│   └── curated/            # Lo que lee Power BI
├── powerbi/                # Proyecto PBIP (TMDL + PBIR)
├── reports/                # Calidad, linaje, validaciones y análisis
├── tests/                  # 65 pruebas, con recortes de los archivos reales más difíciles
└── docs/                   # Un documento por fase, fuentes oficiales y capturas
```

## Limitaciones

- **Solo bienes.** El catálogo de servicios (boletos aéreos) ya no se publica abiertamente.
- **Sin región ni nivel de gobierno.** Los archivos no traen la ubicación ni el tipo de la
  entidad.
- **Sin precios unitarios.** Cada fila es una orden completa, así que no se puede comparar el precio
  de un mismo producto.
- **Proveedores activos no es lo mismo que proveedores homologados.** Un proveedor puede estar en
  el catálogo y no recibir órdenes.
- **El estado de pago no se usa.** Tuvo un quiebre de siete meses (noviembre de 2024 a mayo de
  2025) por la actualización automática desde el SIAF.
- **Las señales de control no prueban irregularidades.** Una compra ordinaria sobre el umbral puede
  tener una excepción válida, y dos órdenes el mismo día pueden ser compras distintas.
- **Análisis descriptivo.** Dice qué pasó y cuánto, no por qué.

## Fuentes y licencia

Datos: [Plataforma Nacional de Datos Abiertos, órdenes de compra de los Catálogos Electrónicos](https://www.datosabiertos.gob.pe/dataset/%C3%B3rdenes-de-compra-realizadas-trav%C3%A9s-de-los-cat%C3%A1logos-electr%C3%B3nicos-central-de-compras),
publicadas por la Central de Compras Públicas – Perú Compras. Validación con los
[boletines e Infocifras de Perú Compras](https://www.gob.pe/institucion/perucompras/colecciones/689-boletines-peru-compras),
guardados en [`docs/fuentes/`](docs/fuentes/). Son información pública. Código bajo licencia
[MIT](LICENSE).
