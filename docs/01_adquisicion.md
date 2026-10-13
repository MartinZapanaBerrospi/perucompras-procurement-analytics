# Fase 1 — Adquisición

> Estado: **cerrada** (2026-10-13).

## Qué se descarga

| Fuente | Qué | Cantidad | Destino |
|---|---|---|---|
| Perú Compras, vía la Plataforma Nacional de Datos Abiertos | Órdenes de compra de bienes de los Catálogos Electrónicos, un CSV por mes de formalización (2022-01 a 2026-09) | 57 archivos, 262 MB (32 MB comprimidos) | `data/raw/ordenes/ordenes_{AAAA-MM}.csv` |
| Perú Compras | Diccionario de datos oficial | 1 PDF | [`docs/fuentes/diccionario_datos_bienes.pdf`](fuentes/diccionario_datos_bienes.pdf) |
| Perú Compras, vía gob.pe | Infocifras de Catálogos Electrónicos de cierre de 2024 y 2025, para validar | 2 PDF | [`docs/fuentes/`](fuentes/) |

## Por qué la descarga se hace en el navegador

El portal responde **418** a cualquier cliente que no sea un navegador (curl, `requests`,
`urllib`). Es un control deliberado y **no se intenta evadirlo**: no se cambian cabeceras ni se
simula un navegador.

La salida es una descarga única y trazable. El portal arma al momento un zip con todos los
recursos del conjunto, que se baja una vez desde el navegador. A partir de ahí todo es
automático y verificable.

## Cómo se ejecuta

1. Abrir en el navegador el zip del conjunto:
   `https://www.datosabiertos.gob.pe/node/9587/dataset/download`
   (también es el botón de descarga de la
   [página del conjunto](https://www.datosabiertos.gob.pe/dataset/%C3%B3rdenes-de-compra-realizadas-trav%C3%A9s-de-los-cat%C3%A1logos-electr%C3%B3nicos-central-de-compras)).
2. Dejar el zip en `data/raw/descarga/`. Sirve cualquier nombre. También sirven CSV sueltos
   bajados uno por uno.
3. Ejecutar:

```bash
python -m src.extract              # extrae, compara con el inventario y registra en el manifiesto
python -m src.extract --verificar  # solo comprueba que data/raw/ordenes no cambió
```

El script:

- **Extrae cada CSV sin modificar un solo byte** y le da un nombre uniforme
  (`ordenes_2023-02.csv` en lugar de `ReportePCBienes202302_0.csv`). La limpieza es trabajo de
  la Fase 3; aquí el dato se guarda tal como lo publica la fuente.
- **Compara cada archivo con el inventario del portal**
  ([`data/reference/inventario_portal.csv`](../data/reference/inventario_portal.csv)): el nombre,
  el tamaño y la fecha de publicación que el portal listaba el 2026-10-13. Si Perú Compras
  reemplaza un archivo, el tamaño deja de coincidir y el registro queda marcado
  `distinto_al_inventario`.
- **Falla si falta un mes** del periodo definido en `src/config.py`.
- **Es idempotente.** Ejecutarlo dos veces deja el manifiesto idéntico, byte por byte. Un
  archivo cuyo hash no cambió no se reescribe.

## Manifiesto

`data/raw/manifest.csv` es el único archivo de `data/raw` que se versiona. Tiene una fila por mes:

| Campo | Para qué sirve |
|---|---|
| `periodo`, `archivo_portal`, `url` | Trazabilidad hasta el archivo oficial, con su nombre original |
| `publicado_en` | Fecha de la última modificación del archivo en el portal |
| `archivo` | Dónde quedó en el proyecto |
| `bytes`, `sha256` | Detectar cualquier cambio posterior: un solo byte distinto cambia el hash |
| `origen` | De qué zip o archivo salió |
| `estado` | `ok` o `distinto_al_inventario` |
| `registrado_en` | Fecha y hora UTC del registro |

El zip usado se guardó como `perucompras_catalogos_bienes_2026-10-13.zip` (32 161 695 bytes,
SHA-256 `a4f0e6ee…ae86ac6`). Contiene los 57 CSV y el diccionario.

## Resultado

- **57 de 57 meses** registrados, todos con estado `ok`: el tamaño de cada archivo coincide con
  lo que lista el portal.
- **261,7 MB** de datos sin comprimir.
- **11 pruebas automáticas** del registro ([`tests/test_extract.py`](../tests/test_extract.py)).
  Cubren el reconocimiento de nombres, la idempotencia, la preferencia por la versión que lista
  el portal, la marca de archivos alterados y que el inventario cubra todo el periodo.

## Lo que la adquisición ya reveló

1. **El portal publicó por lotes hasta marzo de 2026.** 29 archivos (2022-01 a 2024-05) tienen
   la misma fecha de modificación, 2024-07-17. Cinco meses (2025-10 a 2026-02) aparecieron
   juntos el 2026-03-19, con hasta cinco meses de retraso. Desde marzo de 2026 cada mes se
   publica entre 1 y 4 días después de cerrar. Para un tablero de gestión, esto define el corte:
   los datos llegan hasta el último mes cerrado.
2. **La fecha de publicación no es la fecha de los datos.** La columna `FECHA_PROCESO` de cada
   archivo dice cuándo se generó la información (el día 1 del mes siguiente, desde mayo de 2022).
   Un archivo puede haberse subido al portal mucho después. El estado de cada orden es una foto
   tomada en `FECHA_PROCESO`, no en la fecha de publicación.
3. **El diccionario oficial no coincide del todo con los archivos.**
   - Dice que las fechas vienen como `DD/MM/YYYY hh:mm:ss`, pero 56 de los 57 archivos usan
     `AAAA-MM-DD hh:mm:ss`. Solo junio de 2024 sigue el diccionario.
   - Llama `DOCUMENTO_ESTADO` a la columna que en los archivos es `DOCUMENTO_ESTADO_OCAM`.
   - Define `FECHA_FORMALIZACIÓN` como "fecha de aceptación de la orden" y aclara que
     `SUB_TOTAL` ya incluye el costo de envío.

   Las tres cosas pasan al catálogo de problemas de la [Fase 2](02_calidad.md).
4. **Cuatro meses fueron reemplazados en el portal** (sufijo `_0`). El zip trae solo la versión
   vigente, que es la que se registra.
