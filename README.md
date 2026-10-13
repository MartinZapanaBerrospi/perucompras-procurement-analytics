# Perú Compras Procurement Analytics

> **En construcción.** El proyecto avanza por fases; este README se completa con los hallazgos y
> el enlace al tablero al terminar.

Análisis de las **compras del Estado peruano por Catálogos Electrónicos de Acuerdos Marco** entre
enero de 2022 y setiembre de 2026: S/ 8 519 millones en 511 782 órdenes de compra de bienes,
con **datos abiertos reales** de Perú Compras, hasta un tablero de Power BI para gerencia.

## La pregunta

¿Cuánto y en qué compra el Estado por Catálogos Electrónicos, qué tan concentrada está la venta
en cada catálogo, quién compra y en qué momento del año?

## Avance

| Fase | Estado | Documento |
|---|---|---|
| 0. Definición | Cerrada | [00_definicion.md](docs/00_definicion.md) |
| 1. Adquisición | Cerrada | [01_adquisicion.md](docs/01_adquisicion.md) |
| 2. Calidad | Cerrada | [02_calidad.md](docs/02_calidad.md) |
| 3. Transformación | Cerrada | [03_transformacion.md](docs/03_transformacion.md) |
| 4. Modelado | Cerrada | [04_modelado.md](docs/04_modelado.md) |
| 5. Análisis | Cerrada | [05_analisis.md](docs/05_analisis.md) |
| 6. Tablero | Cerrada | [powerbi/README.md](powerbi/README.md) |
| 7. Hallazgos | En curso | — |
| 8. Automatización | Pendiente | — |
| 9. Publicación | Pendiente | — |

**Lo que valida el resultado.** Los datos reconstruyen las cifras oficiales de Perú Compras de
2022 a 2025, por año y por tipo de procedimiento, con una diferencia máxima de 0,87 %. En 2022 la
diferencia es de 0,001 %. La calidad se mide con 59 reglas en seis dimensiones; el detalle está en
la [Fase 2](docs/02_calidad.md).

## Fuentes y licencia

Datos: [Plataforma Nacional de Datos Abiertos, órdenes de compra de los Catálogos Electrónicos](https://www.datosabiertos.gob.pe/dataset/%C3%B3rdenes-de-compra-realizadas-trav%C3%A9s-de-los-cat%C3%A1logos-electr%C3%B3nicos-central-de-compras)
y [Infocifras de Perú Compras](https://www.gob.pe/institucion/perucompras/colecciones/689-boletines-peru-compras).
Código bajo licencia [MIT](LICENSE).
