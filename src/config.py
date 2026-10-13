"""Parámetros del proyecto: periodo, fuente y rutas."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
DOWNLOADS = RAW / "descarga"      # aquí se deja el zip bajado desde el portal
ORDERS = RAW / "ordenes"          # un CSV por mes, con nombre normalizado
STAGING = DATA / "staging"
CURATED = DATA / "curated"
REFERENCE = DATA / "reference"
MANIFEST = RAW / "manifest.csv"
PORTAL_INVENTORY = REFERENCE / "inventario_portal.csv"

# Periodo de análisis (inclusive). Perú Compras publica cada mes alrededor del día 1 del siguiente.
START = (2022, 1)
END = (2026, 9)

DATASET_URL = (
    "https://www.datosabiertos.gob.pe/dataset/"
    "%C3%B3rdenes-de-compra-realizadas-trav%C3%A9s-de-los-cat%C3%A1logos-electr%C3%B3nicos-central-de-compras"
)
# Zip con todos los recursos del conjunto, que el portal arma al momento
ZIP_URL = "https://www.datosabiertos.gob.pe/node/9587/dataset/download"
FILE_URL = "https://www.datosabiertos.gob.pe/sites/default/files/{name}"
FILE_PREFIX = "ReportePCBienes"


def periods():
    """Lista de (año, mes) del periodo de análisis."""
    y, m = START
    out = []
    while (y, m) <= END:
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out
