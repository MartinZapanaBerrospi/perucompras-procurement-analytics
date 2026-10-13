"""Pruebas del modelo de Power BI que no necesitan Power BI Desktop."""

import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import build_model  # noqa: E402
import validate_measures  # noqa: E402

DEFINITION = ROOT / "powerbi" / "perucompras.SemanticModel" / "definition"
# Palabras que DAX no admite como nombre de variable (el error de la Fase 4 fue 'top').
RESERVED = {"top", "var", "return", "true", "false", "not", "and", "or", "in", "order", "by", "asc", "desc",
            "define", "evaluate", "measure", "column", "table", "datatable", "start", "at", "skip", "dense"}


def test_las_variables_dax_no_usan_palabras_reservadas():
    for _, name, expr, _, _ in build_model.MEASURES:
        for var in re.findall(r"\bVAR\s+(\w+)", expr):
            assert var.lower() not in RESERVED, f"{name}: VAR {var}"


def test_las_medidas_validadas_existen_en_el_modelo():
    names = {m[1] for m in build_model.MEASURES}
    for group in (validate_measures.GLOBAL, validate_measures.BY_YEAR, validate_measures.BY_CATALOG):
        assert set(group) <= names


def test_el_tmdl_versionado_es_el_que_produce_el_generador(tmp_path, monkeypatch):
    monkeypatch.setattr(build_model, "MODEL", tmp_path / "modelo")
    build_model.main()
    for generated in (tmp_path / "modelo" / "definition").rglob("*.tmdl"):
        versioned = DEFINITION / generated.relative_to(tmp_path / "modelo" / "definition")
        if generated.name == "expressions.tmdl":
            continue  # contiene la ruta local de data/curated
        assert versioned.read_text(encoding="utf-8") == generated.read_text(encoding="utf-8"), versioned.name


def test_todas_las_medidas_coinciden_con_python():
    result = pd.read_csv(ROOT / "reports" / "validacion_medidas.csv")
    expected = (len(validate_measures.GLOBAL) + 5 * len(validate_measures.BY_YEAR)
                + 29 * len(validate_measures.BY_CATALOG))
    assert len(result) == expected
    assert (result["resultado"] == "cumple").all()


def test_cada_columna_del_csv_esta_en_el_modelo():
    for name, spec in build_model.TABLES.items():
        header = (ROOT / "data" / "curated" / f"{name}.csv").open(encoding="utf-8").readline().strip().split(",")
        assert [c[0] for c in spec["columns"]] == header, name
