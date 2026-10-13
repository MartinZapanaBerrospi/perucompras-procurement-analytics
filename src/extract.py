"""Fase 1 — Registra los archivos de órdenes de compra bajados del portal de datos abiertos.

El portal (datosabiertos.gob.pe) responde 418 a los clientes que no son navegadores, y este
proyecto no intenta evadirlo. Por eso la descarga se hace en el navegador, una sola vez: el zip
con todo el conjunto (ver config.ZIP_URL) se deja en data/raw/descarga/. Este script:

1. Extrae cada CSV mensual a data/raw/ordenes/ordenes_AAAA-MM.csv, sin modificar un solo byte.
2. Compara cada archivo con el inventario del portal (data/reference/inventario_portal.csv).
3. Registra en data/raw/manifest.csv su URL, fecha de publicación, tamaño y hash SHA-256.
4. Falla si falta algún mes del periodo de análisis.

Es idempotente: un archivo que no cambió no se vuelve a escribir ni altera el manifiesto.

Uso:
    python -m src.extract              # procesa el zip (o los CSV sueltos) de data/raw/descarga/
    python -m src.extract --verificar  # solo comprueba data/raw/ordenes contra el manifiesto
"""

import argparse
import csv
import hashlib
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from src import config

MANIFEST_FIELDS = [
    "periodo", "archivo_portal", "url", "publicado_en", "archivo", "bytes", "sha256",
    "origen", "estado", "registrado_en",
]
NAME_RE = re.compile(rf"^{config.FILE_PREFIX}(\d{{4}})(\d{{2}})(?:_\d+)?\.csv$", re.IGNORECASE)


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_inventory() -> dict:
    """archivo_portal -> {bytes, publicado_en}, tal como lo listaba el portal."""
    with config.PORTAL_INVENTORY.open(encoding="utf-8", newline="") as f:
        return {r["archivo_portal"]: r for r in csv.DictReader(f)}


def load_manifest() -> dict:
    if not config.MANIFEST.exists():
        return {}
    with config.MANIFEST.open(encoding="utf-8", newline="") as f:
        return {r["periodo"]: r for r in csv.DictReader(f)}


def save_manifest(rows: dict) -> None:
    config.MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with config.MANIFEST.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows[p] for p in sorted(rows))


def period_of(name: str) -> str | None:
    match = NAME_RE.match(Path(name).name)
    return f"{match.group(1)}-{match.group(2)}" if match else None


def sources() -> list[tuple[str, bytes, str]]:
    """(nombre en el portal, contenido, origen) de cada CSV mensual que haya en data/raw/descarga."""
    found = []
    for path in sorted(config.DOWNLOADS.glob("*")):
        if path.suffix.lower() == ".zip":
            with zipfile.ZipFile(path) as zf:
                for member in zf.namelist():
                    if period_of(member):
                        found.append((Path(member).name, zf.read(member), path.name))
        elif period_of(path.name):
            found.append((path.name, path.read_bytes(), path.name))
    return found


def pick_per_period(found: list, inventory: dict) -> dict:
    """Un archivo por mes. Si el portal tuvo dos versiones (p. ej. 202302 y 202302_0), gana la que
    figura en el inventario."""
    chosen = {}
    for name, content, origin in found:
        period = period_of(name)
        current = chosen.get(period)
        if current is None or (name in inventory and current[0] not in inventory):
            chosen[period] = (name, content, origin)
    return chosen


def register(chosen: dict, inventory: dict, manifest: dict) -> dict:
    counts = {"nuevo": 0, "sin_cambios": 0, "actualizado": 0, "distinto_al_inventario": 0}
    config.ORDERS.mkdir(parents=True, exist_ok=True)
    for period, (name, content, origin) in sorted(chosen.items()):
        target = config.ORDERS / f"ordenes_{period}.csv"
        digest = sha256(content)
        previous = manifest.get(period)

        if previous and previous["sha256"] == digest and target.exists():
            counts["sin_cambios"] += 1
            continue

        target.write_bytes(content)
        listed = inventory.get(name, {})
        state = "ok" if listed.get("bytes") == str(len(content)) else "distinto_al_inventario"
        counts["actualizado" if previous else "nuevo"] += 1
        if state != "ok":
            counts["distinto_al_inventario"] += 1
            print(f"  ! {name}: {len(content)} bytes; el inventario dice {listed.get('bytes', 'nada')}")

        manifest[period] = {
            "periodo": period,
            "archivo_portal": name,
            "url": config.FILE_URL.format(name=name),
            "publicado_en": listed.get("publicado_en", ""),
            "archivo": target.relative_to(config.ROOT).as_posix(),
            "bytes": len(content),
            "sha256": digest,
            "origen": origin,
            "estado": state,
            "registrado_en": now(),
        }
    return counts


def missing_periods(manifest: dict) -> list[str]:
    return [f"{y}-{m:02d}" for y, m in config.periods() if f"{y}-{m:02d}" not in manifest]


def verify(manifest: dict) -> list[str]:
    """Archivos de data/raw/ordenes que faltan o cuyo hash ya no coincide con el manifiesto."""
    problems = []
    for period, row in sorted(manifest.items()):
        path = config.ROOT / row["archivo"]
        if not path.exists():
            problems.append(f"{period}: falta {row['archivo']}")
        elif sha256(path.read_bytes()) != row["sha256"]:
            problems.append(f"{period}: el contenido de {row['archivo']} no coincide con el manifiesto")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--verificar", action="store_true",
                        help="solo comprueba data/raw/ordenes contra el manifiesto")
    args = parser.parse_args()

    manifest = load_manifest()

    if not args.verificar:
        found = sources()
        if not found:
            print(f"No hay archivos en {config.DOWNLOADS.relative_to(config.ROOT)}.")
            print(f"Descarga el zip del conjunto desde el navegador:\n  {config.ZIP_URL}")
            print(f"(página del conjunto: {config.DATASET_URL})")
            return 1
        inventory = load_inventory()
        chosen = pick_per_period(found, inventory)
        counts = register(chosen, inventory, manifest)
        save_manifest(manifest)
        print(f"Órdenes: {counts['nuevo']} nuevos, {counts['actualizado']} actualizados, "
              f"{counts['sin_cambios']} sin cambios, {counts['distinto_al_inventario']} distintos al inventario")
        print(f"Manifiesto: {config.MANIFEST.relative_to(config.ROOT)} ({len(manifest)} meses)")

    problems = verify(manifest)
    missing = missing_periods(manifest)
    for p in problems:
        print(f"  ✗ {p}")
    for period in missing:
        print(f"  ✗ {period}: no está en el manifiesto")
    if problems or missing:
        return 1
    print(f"Verificación: {len(manifest)} meses completos y con el hash esperado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
