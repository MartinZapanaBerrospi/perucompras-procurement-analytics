"""Pruebas de la Fase 1: registro idempotente y verificación de los archivos del portal."""

import zipfile

import pytest

from src import config, extract


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """Copia mínima de la estructura de carpetas del proyecto, en un directorio temporal."""
    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.setattr(config, "DOWNLOADS", tmp_path / "data/raw/descarga")
    monkeypatch.setattr(config, "ORDERS", tmp_path / "data/raw/ordenes")
    monkeypatch.setattr(config, "MANIFEST", tmp_path / "data/raw/manifest.csv")
    monkeypatch.setattr(config, "START", (2023, 1))
    monkeypatch.setattr(config, "END", (2023, 2))
    config.DOWNLOADS.mkdir(parents=True)
    return tmp_path


def make_zip(folder, files):
    with zipfile.ZipFile(folder / "conjunto.zip", "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)


INVENTORY = {
    "ReportePCBienes202301.csv": {"bytes": "4", "publicado_en": "2024-07-17T14:18:10Z"},
    "ReportePCBienes202302_0.csv": {"bytes": "4", "publicado_en": "2024-07-17T14:18:10Z"},
}


def run(inventory=INVENTORY):
    manifest = extract.load_manifest()
    chosen = extract.pick_per_period(extract.sources(), inventory)
    counts = extract.register(chosen, inventory, manifest)
    extract.save_manifest(manifest)
    return manifest, counts


@pytest.mark.parametrize("name, period", [
    ("ReportePCBienes202201.csv", "2022-01"),
    ("ReportePCBienes202302_0.csv", "2023-02"),
    ("carpeta/ReportePCBienes202609.csv", "2026-09"),
    ("Diccionario_Datos_Bienes.pdf", None),
    ("ReportePCServicios202501.csv", None),
])
def test_period_of(name, period):
    assert extract.period_of(name) == period


def test_registra_todos_los_meses_sin_alterar_bytes(repo):
    make_zip(config.DOWNLOADS, {"ReportePCBienes202301.csv": b"a;b\n", "ReportePCBienes202302_0.csv": b"c;d\n"})
    manifest, counts = run()
    assert counts["nuevo"] == 2
    assert (config.ORDERS / "ordenes_2023-02.csv").read_bytes() == b"c;d\n"
    assert manifest["2023-02"]["archivo_portal"] == "ReportePCBienes202302_0.csv"
    assert extract.missing_periods(manifest) == []
    assert extract.verify(manifest) == []


def test_segunda_ejecucion_no_cambia_nada(repo):
    make_zip(config.DOWNLOADS, {"ReportePCBienes202301.csv": b"a;b\n", "ReportePCBienes202302_0.csv": b"c;d\n"})
    run()
    before = config.MANIFEST.read_text(encoding="utf-8")
    _, counts = run()
    assert counts == {"nuevo": 0, "sin_cambios": 2, "actualizado": 0, "distinto_al_inventario": 0}
    assert config.MANIFEST.read_text(encoding="utf-8") == before


def test_prefiere_la_version_que_lista_el_portal(repo):
    make_zip(config.DOWNLOADS, {"ReportePCBienes202302.csv": b"viejo\n", "ReportePCBienes202302_0.csv": b"c;d\n"})
    manifest, _ = run()
    assert manifest["2023-02"]["archivo_portal"] == "ReportePCBienes202302_0.csv"


def test_marca_el_archivo_que_no_coincide_con_el_inventario(repo):
    make_zip(config.DOWNLOADS, {"ReportePCBienes202301.csv": b"distinto\n"})
    manifest, counts = run()
    assert manifest["2023-01"]["estado"] == "distinto_al_inventario"
    assert counts["distinto_al_inventario"] == 1
    assert extract.missing_periods(manifest) == ["2023-02"]


def test_verificar_detecta_un_archivo_modificado(repo):
    make_zip(config.DOWNLOADS, {"ReportePCBienes202301.csv": b"a;b\n", "ReportePCBienes202302_0.csv": b"c;d\n"})
    manifest, _ = run()
    (config.ORDERS / "ordenes_2023-01.csv").write_bytes(b"editado a mano\n")
    assert extract.verify(manifest) == [
        "2023-01: el contenido de data/raw/ordenes/ordenes_2023-01.csv no coincide con el manifiesto"
    ]


def test_el_inventario_versionado_cubre_todo_el_periodo():
    """El inventario del portal tiene un CSV por cada mes del periodo de análisis."""
    periods = {extract.period_of(n) for n in extract.load_inventory()} - {None}
    expected = {f"{y}-{m:02d}" for y, m in config.periods()}
    assert periods == expected
