# Fase 2 — Calidad de los datos

> Estado: **cerrada** (2026-10-13). La P5 se reemplazó por la P5′
> ([sección 9](#9-qué-pasa-con-la-pregunta-p5)).

## 1. Resumen

Se revisaron las **511 782 órdenes** de los 57 archivos con **59 reglas de calidad** en seis
dimensiones. Ninguna regla bloqueante falla.

- **Los datos son exactos.** Reconstruyen las cifras oficiales de Perú Compras de 2022 a 2025
  con una diferencia máxima de 0,87 %, y de solo 0,001 % en 2022.
- **Los datos son íntegros.** No hay órdenes repetidas, todos los RUC tienen un dígito
  verificador válido y en el 100 % de las órdenes `TOTAL = SUB_TOTAL + IGV`.
- **El formato no es uniforme.** Hay 18 problemas documentados. Los críticos son tres: un mes
  con un tabulador al inicio de 182 376 celdas, un mes con fechas en otro formato y un acuerdo
  marco que desde junio de 2024 viene sin código.
- **Dos hallazgos cambian el análisis:**
  - El mismo nombre de entidad puede ser varias entidades. "Municipalidad Distrital de
    Miraflores" son tres RUC distintos. La identidad de una entidad es su RUC, nunca su nombre.
  - El estado "Pagada" tiene un quiebre de siete meses, de noviembre de 2024 a mayo de 2025, que
    no refleja la realidad. Ver la [sección 9](#9-qué-pasa-con-la-pregunta-p5).

## 2. Cómo se mide

```bash
python -m src.quality     # perfila, aplica las reglas y compara con las cifras oficiales
```

Las reglas de limpieza viven en [`src/parse_ordenes.py`](../src/parse_ordenes.py) y las de calidad
en [`src/quality.py`](../src/quality.py). La Fase 3 reutiliza las mismas funciones, así que lo
que se midió aquí es exactamente lo que se transforma después. Resultados en
[`reports/calidad/`](../reports/calidad/):

| Archivo | Qué contiene |
|---|---|
| [`perfilado_columnas.csv`](../reports/calidad/perfilado_columnas.csv) | Una fila por columna: vacíos, valores distintos antes y después de limpiar, rango y valores frecuentes |
| [`perfilado_mensual.csv`](../reports/calidad/perfilado_mensual.csv) | Una fila por archivo: codificación, fin de línea, celdas con tabulador, formato de fecha, monto, corte y publicación |
| [`reglas.csv`](../reports/calidad/reglas.csv) | Las 59 reglas, con filas y monto afectados y su resultado |
| [`atipicos.csv`](../reports/calidad/atipicos.csv) | Las 485 órdenes marcadas, con el motivo |
| [`nombres_por_ruc.csv`](../reports/calidad/nombres_por_ruc.csv) | RUC con más de un nombre, separando la variante de escritura del cambio real |
| [`nombres_con_varios_ruc.csv`](../reports/calidad/nombres_con_varios_ruc.csv) | Nombres de entidad que comparten varias entidades |
| [`acuerdos_marco.csv`](../reports/calidad/acuerdos_marco.csv) | Cada texto de acuerdo marco y el catálogo estable que le toca |
| [`../validaciones.csv`](../reports/validaciones.csv) | Comparación con las cifras oficiales |

Cada regla tiene una **severidad**:
- **Bloqueante:** si falla, el pipeline se detiene.
- **Alerta:** se documenta y se marca en los datos.
- **Informativa:** describe la fuente sin juzgarla.

## 3. Perfilado

**Por columna.** Ninguna columna obligatoria tiene vacíos. El perfilado muestra cuánto ensucia el
formato: antes de limpiar hay 4 850 RUC de proveedor distintos y después 3 569. El tabulador
de marzo de 2024 convierte cada valor en uno "nuevo".

| Columna | Distintos antes | Distintos después | Vacíos |
|---|---|---|---|
| `ruc_proveedor` | 4 850 | 3 569 | 0 |
| `ruc_entidad` | 3 378 | 2 348 | 0 |
| `estado` | 7 | 5 | 0 |
| `tipo_procedimiento` | 4 | 2 | 0 |
| `acuerdo_marco` | 95 | 72 | 0 |
| `descripcion_estado` | 8 | 6 | 81,5 % |
| `url_documento_estado` | 3 144 | 3 143 | 99,4 % |
| `descripcion_cesion_derechos` | 2 | 1 | 100 % |

**Por archivo.** 55 de los 57 archivos tienen el mismo formato. Los dos distintos son los que
obligan a escribir reglas:

| Mes | Codificación | Fin de línea | Celdas con tabulador | Formato de fecha |
|---|---|---|---|---|
| 55 meses | Windows-1252 | LF | 0 | `AAAA-MM-DD hh:mm:ss` |
| 2024-03 | **UTF-8** | **CRLF** | **182 376** | `AAAA-MM-DD hh:mm:ss` |
| 2024-06 | Windows-1252 | **CRLF** | 0 | **`D/MM/AAAA hh:mm`** |

## 4. Las seis dimensiones

| Dimensión | Pregunta | Reglas | Resultado |
|---|---|---|---|
| **Completitud** | ¿Está todo lo que debería estar? | 15 | 57 de 57 meses, 19 de 19 columnas, 0 vacíos en los 10 campos obligatorios. 3 columnas casi vacías (informativo) |
| **Unicidad** | ¿Algo se cuenta dos veces? | 2 | 0 órdenes repetidas en todo el periodo; 0 filas idénticas |
| **Validez** | ¿Cada valor tiene la forma correcta? | 14 | 100 % de los RUC con dígito verificador válido, fechas y montos interpretables, estados y procedimientos dentro de su dominio, 100 % de los acuerdos marco con catálogo |
| **Consistencia** | ¿Los campos concuerdan entre sí? | 10 | `TOTAL = SUB_TOTAL + IGV` en el 100 %; fechas en orden lógico. 5 alertas: IGV parcial, nombres, umbral de Gran Compra |
| **Exactitud** | ¿Coincide con la cifra oficial? | 15 | 15 de 15 comparaciones dentro de ±1 % ([sección 7](#7-exactitud-validación-contra-las-cifras-oficiales)) |
| **Oportunidad** | ¿Los datos llegan a tiempo y son comparables en el tiempo? | 3 | 3 alertas: corte tardío en 6 meses, publicación por lotes hasta 2026, quiebre del estado "Pagada" |

El detalle de las 59 reglas está en [`reglas.csv`](../reports/calidad/reglas.csv).

**Cómo se valida un RUC.** Los 11 dígitos no bastan: el último es un dígito verificador. Se
calcula con los diez primeros, multiplicados por los pesos 5, 4, 3, 2, 7, 6, 5, 4, 3, 2 (módulo 11).
Así un RUC mal digitado no pasa por válido. Los 3 569 RUC de proveedor y los 2 348 de entidad lo
cumplen.

## 5. Catálogo de problemas

| # | Problema | Ejemplo real | Afecta | Decisión |
|---|---|---|---|---|
| 1 | **La codificación cambia** | 2024-03 viene en UTF-8; el resto, en Windows-1252 | 1 archivo | Corregir: se prueba UTF-8 y, si falla, Windows-1252 |
| 2 | **Tabuladores y espacios en los extremos** | `\tACEPTADA`; `PROVEEDOR` con espacios al final | 182 376 celdas (2024-03) + 5 570 acuerdos marco | Corregir: se quitan los extremos y se colapsan los espacios repetidos |
| 3 | **El diccionario oficial no coincide con los archivos** | Dice `DOCUMENTO_ESTADO` y fechas `DD/MM/YYYY`; los archivos traen `DOCUMENTO_ESTADO_OCAM` y `AAAA-MM-DD` | 1 columna, 56 archivos | Documentar: el diccionario del proyecto ([sección 8](#8-diccionario-de-datos)) describe los archivos reales |
| 4 | **Otro formato de fecha en 2024-06** | `3/06/2024 23:57`, sin segundos | 7 880 órdenes | Corregir: se lee como día/mes; la prueba usa un día de un dígito para que no se confunda con el mes |
| 5 | **Archivos republicados** | `ReportePCBienes202302_0.csv` | 4 meses | Resuelto en la Fase 1: se usa la versión vigente |
| 6 | **El acuerdo marco pierde su código y varía su escritura** | Hasta 2024-05: `EXT-CE-2021-1 BATERIAS, PILAS…`; desde 2024-07: `BATERÍAS, PILAS…` | 95 textos | Corregir: se separan código y nombre, se normaliza el nombre (sin tildes ni espacios dobles) y se asigna con [`catalogos.csv`](../data/reference/catalogos.csv): 95 textos → 30 nombres → **29 catálogos** en **10 rubros** |
| 7 | **Catálogos que se reemplazan con otro nombre** | *Calzado* (hasta 2024-12) → *Calzado y botas* (desde 2025-02) | 3 pares | Decidir caso por caso: *Calzado* se une porque es el mismo catálogo renovado. *Bienes y herramientas…* → *Accesorios domésticos…* y *Alimentos…* → *Cereales…* se mantienen separados porque cambian de alcance |
| 8 | **Un RUC con varios nombres** | 20266352337: *Softys Perú S.A.C.* y *Productos Tissue del Perú S.A.C.* | 23 proveedores; 928 de las 2 348 entidades | Corregir: la dimensión usa el nombre más reciente. Solo 45 son variantes de escritura; 906 son cambios reales de nombre |
| 9 | **Un nombre con varios RUC** | *Municipalidad Distrital de Miraflores* = 3 RUC; *Gerencia Regional de Transportes y Comunicaciones* = 3 | 30 nombres, 7 262 órdenes | Corregir: la identidad es el RUC. En el tablero, los nombres repetidos llevan el RUC al lado |
| 10 | **El estado es una foto al corte del archivo** | 2022-01 se fotografió 101 días después de cerrar el mes; desde 2022-05, 1 día después | 6 meses con corte tardío | Documentar: el estado no es comparable en esos meses |
| 11 | **Quiebre del estado "Pagada"** | Órdenes pagadas al corte: 14,8 % de mediana; 2,9 % en 2024-11 y 0,4 % en 2025-01. Los eneros también bajan (2,0 % a 3,6 %), pero eso es estacional: empieza el año fiscal | 7 meses seguidos (2024-11 a 2025-05) | Descartar como indicador; ver la [sección 9](#9-qué-pasa-con-la-pregunta-p5) |
| 12 | **IGV en cero o parcial** | Órdenes del Gobierno Regional de Ucayali sin IGV | 19 217 órdenes (S/ 243,4 millones) en cero; 394 con IGV parcial | Mantener y marcar. Se concentran en entidades de Ucayali, Loreto y San Martín, cubiertas por la exoneración de IGV de la Amazonía (Ley 27037). No es un error |
| 13 | **Montos ínfimos** | S/ 0,05 a una universidad por computadoras | 26 órdenes, S/ 35 en total | Mantener y marcar como atípico: no alteran ningún total |
| 14 | **Montos muy altos** | S/ 44,6 millones en computadoras para el Gobierno Regional La Libertad | 119 órdenes, **S/ 1 007 millones (11,8 % del monto)** | Mantener y marcar: son compras reales, todas por Gran Compra. Pesan tanto que el análisis las debe mostrar aparte |
| 15 | **Estados que no son compra** | *Orden de compra nula*, *Resuelta* | 340 órdenes, S/ 7,3 millones | Mantener y marcar: la cifra oficial las incluye. El tablero permite excluirlas |
| 16 | **Columnas vacías** | `descripcion_cesion_derechos` vacía en el 100 % | 3 columnas | Excluir del modelo; se mantienen en staging |
| 17 | **Compras ordinarias por encima del umbral** | Compra ordinaria de S/ 744 195 en limpieza (UGEL Cusco) | 785 órdenes, S/ 121,4 millones | Mantener y marcar. Desde S/ 100 000 la Gran Compra es obligatoria (Directiva N.° 006-2021-PERÚ COMPRAS), pero puede haber excepciones que los datos no muestran. Es una alerta de control, no una acusación |
| 18 | **Publicación por lotes** | 2025-10 a 2026-02 se publicaron juntos el 2026-03-19 | 45 de 57 meses con más de 7 días de rezago | Documentar: desde 2026-03 se publica entre 1 y 4 días después del cierre |

## 6. Atípicos

Un monto se considera atípico cuando cae fuera de Q1 − 3·RIC o Q3 + 3·RIC, calculados sobre el
logaritmo del monto. El logaritmo se usa porque los montos van de céntimos a decenas de millones,
y en escala lineal casi todo sería atípico. Umbrales resultantes: **menos de S/ 2,53** o **más de
S/ 3 444 382**.

| Motivo | Órdenes | Monto | Lectura |
|---|---|---|---|
| Monto muy alto | 119 | S/ 1 007,1 millones | 99 son de computadoras, todas por Gran Compra. Son las compras que más mueven el total |
| Monto muy bajo | 26 | S/ 35 | Probablemente ajustes o errores de registro; no alteran ningún total |
| Estado que no es compra | 340 | S/ 7,3 millones | 12 nulas y 328 resueltas |

Ninguna orden se borra: cada una lleva su marca y el análisis decide qué mostrar.

## 7. Exactitud: validación contra las cifras oficiales

Las cifras oficiales salen de los boletines estadísticos de 2022 y 2023 y de las Infocifras de
2024 y 2025, guardados en [`docs/fuentes/`](fuentes/) y transcritos en
[`cifras_oficiales.csv`](../data/reference/cifras_oficiales.csv). Se compara el monto de bienes
por año y por tipo de procedimiento, con todos los estados, porque así los cuenta Perú Compras.

| Año | Concepto | Oficial (S/ millones) | Calculado (S/ millones) | Diferencia |
|---|---|---|---|---|
| 2022 | Bienes | 1 994,66 | 1 994,65 | −0,001 % |
| 2022 | Gran Compra | 1 152,53 | 1 152,53 | 0,000 % |
| 2022 | Compra ordinaria | 842,13 | 842,12 | −0,001 % |
| 2023 | Bienes | 1 885,99 | 1 885,32 | −0,036 % |
| 2023 | Gran Compra | 1 026,43 | 1 026,37 | −0,006 % |
| 2023 | Compra ordinaria | 859,56 | 858,95 | −0,071 % |
| 2024 | Bienes | 1 939,34 | 1 934,56 | −0,246 % |
| 2024 | Gran Compra | 1 172,99 | 1 170,36 | −0,224 % |
| 2024 | Compra ordinaria | 766,35 | 764,21 | −0,280 % |
| 2025 | Bienes | 1 792,44 | 1 778,89 | −0,756 % |
| 2025 | Gran Compra | 1 113,17 | 1 105,56 | −0,684 % |
| 2025 | Compra ordinaria | 679,27 | 673,33 | −0,874 % |

En 2023 también se compara el número de órdenes: 116 625 calculadas frente a 116 697 oficiales
(−0,06 %).

**Por qué la diferencia crece en los años recientes.** Siempre es negativa: los archivos tienen un
poco menos que el boletín. La explicación más probable es el momento del corte. Cada archivo es
una foto tomada el día 1 del mes siguiente, y el boletín se elabora semanas después, cuando ya se
registraron órdenes tardías. Es una hipótesis: no se puede verificar orden por orden porque el
boletín solo publica totales.

## 8. Diccionario de datos

Diccionario de los archivos reales, contrastado con el
[diccionario oficial](fuentes/diccionario_datos_bienes.pdf).

| Columna de origen | Nombre en el proyecto | Tipo | Qué es | Observación | ¿Al modelo? |
|---|---|---|---|---|---|
| `FECHA_PROCESO` | `fecha_proceso` | fecha | Momento en que se generó el archivo: la foto del estado | Problemas 4 y 10 | Sí, como corte |
| `RUC_PROVEEDOR` | `ruc_proveedor` | texto (11) | RUC del proveedor | Dígito verificador válido en el 100 % | Sí |
| `PROVEEDOR` | `proveedor` | texto | Razón social del proveedor | Problema 8 | Sí, nombre más reciente |
| `RUC_ENTIDAD` | `ruc_entidad` | texto (11) | RUC de la entidad que compra | Siempre empieza con 20 | Sí |
| `ENTIDAD` | `entidad` | texto | Nombre de la entidad | Problemas 8 y 9 | Sí, nombre más reciente |
| `TIPO_PROCEDIMIENTO` | `tipo_procedimiento` | texto | *Compra ordinaria* o *Gran Compra* | Problema 17 | Sí |
| `ORDEN_ELECTRÓNICA` | `orden` | texto | Código único de la orden (`OCAM-…`) | Único en todo el periodo | Sí, clave |
| `ORDEN_ELECTRÓNICA_GENERADA` | `url_orden` | URL | PDF de la orden | — | Sí, para consultar el detalle |
| `ESTADO_ORDEN_ELECTRÓNICA` | `estado` | texto | Estado al momento del corte | Problemas 10, 11 y 15 | Sí |
| `DOCUMENTO_ESTADO_OCAM` | `url_documento_estado` | URL | Sustento del cambio de estado | 99,4 % vacío; el diccionario lo llama `DOCUMENTO_ESTADO` | No |
| `FECHA_FORMALIZACIÓN` | `fecha_formalizacion` | fecha | Aceptación de la orden: la fecha de la compra | Define el mes del archivo | Sí, fecha principal |
| `FECHA_ÚLTIMO_ESTADO` | `fecha_ultimo_estado` | fecha | Último cambio de estado | Siempre entre la formalización y el corte | Sí |
| `SUB_TOTAL` | `sub_total` | soles | Monto sin IGV, **incluye el costo de envío** | — | Sí |
| `IGV` | `igv` | soles | Impuesto General a las Ventas | Problema 12 | Sí |
| `TOTAL` | `total` | soles | Monto de la orden con IGV | `= SUB_TOTAL + IGV` en el 100 % | Sí, monto principal |
| `ORDEN_DIGITALIZADA` | `url_orden_digitalizada` | URL | Orden firmada por la entidad | — | No |
| `DESCRIPCIÓN_ESTADO` | `descripcion_estado` | texto | Motivo del estado | 81,5 % vacío; el 97 % de las pagadas dice "Actualizado automáticamente por la vinculación con el SIAF" | No; solo para la sección 9 |
| `DESCRIPCIÓN_CESIÓN_DERECHOS` | `descripcion_cesion_derechos` | texto | Cesión de derechos de cobro | 100 % vacío | No |
| `ACUERDO_MARCO` | `acuerdo_marco` | texto | Acuerdo marco y catálogo | Problemas 6 y 7 | Sí, como `catalogo` y `rubro` |

## 9. Qué pasa con la pregunta P5

La Fase 0 dejó condicionada la P5: *¿qué parte de las órdenes figura pagada al mes siguiente?* La
respuesta de la Fase 2 es **descartarla como indicador de gestión**, por tres razones:

1. **Mide una ventana muy corta.** Desde mayo de 2022 el corte se hace un día después de
   cerrar el mes. "Pagada" significa pagada dentro del mismo mes de la compra, y la mediana es
   apenas 14,8 % de las órdenes.
2. **Depende de un enlace automático que falló.** El 97 % de las órdenes pagadas fue marcada por
   la vinculación con el SIAF, el sistema de pagos del Estado. Entre noviembre de 2024 y mayo de
   2025 el porcentaje cae a entre 0,4 % y 3,2 %, y en junio de 2025 vuelve al 16 %. Los pagos no
   se frenaron siete meses: lo que se interrumpió fue la actualización del estado.
3. **Un indicador con un quiebre así llevaría a gerencia a conclusiones falsas.** Un mes "malo"
   no se distinguiría de un mes sin actualización.

**Reemplazo aprobado el 2026-10-13:**
**P5′ — ¿Se usa la Gran Compra donde corresponde?** La Gran Compra es obligatoria desde
S/ 100 000 y hace competir automáticamente a todos los proveedores del catálogo. Los datos
permiten medir dos cosas:
- qué parte del monto de cada catálogo pasa por Gran Compra (en 2025, el 62 %);
- cuántas compras ordinarias superan el umbral: 785 órdenes y S/ 121,4 millones en el periodo,
  sobre todo en impresoras, llantas y limpieza (problema 17).

Es una pregunta de control interno que los datos responden sin ambigüedad.

## 10. Lo que pasa a la Fase 3

- Las reglas de campo (problemas 1, 2, 4 y 6) se aplican con las mismas funciones de
  `src/parse_ordenes.py`.
- **Dimensiones por RUC:**
  - nombre más reciente para entidades y proveedores (problema 8);
  - el RUC al lado del nombre cuando un nombre se repite (problema 9).
- **Columnas de marca en el hecho**, no filtros:
  - `es_atipico` y su motivo (13, 14 y 15);
  - `igv_exonerado` (12);
  - `compra_ordinaria_sobre_umbral` (17).
- **Columnas fuera del modelo:** las tres casi vacías y la URL de la orden digitalizada (16).
- **Linaje:** filas y monto en cada paso, para demostrar que nada se pierde entre raw y curated.
