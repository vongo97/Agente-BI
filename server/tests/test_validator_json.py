"""
Regresión P-53: el Validator devuelve JSON válido, pero algunos modelos meten
BOM o espacios de ancho cero después de '{'. json.loads falla en char 1, el
feedback se pierde y el Executor reintenta a ciegas.
"""
import os
import sys

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_validator_json.db")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.engine.bi_analyst import safe_parse_validator_json


class TestValidatorJson:
    def test_json_normal(self):
        out = safe_parse_validator_json(
            '{"status": "success", "reason": "ok", "feedback": "nada"}'
        )
        assert out["status"] == "success"
        assert out["reason"] == "ok"

    def test_json_con_espacio_ancho_cero(self):
        out = safe_parse_validator_json(
            '{\u200b\n  "status": "error", "reason": "qcut", "feedback": "usa codes"}'
        )
        assert out["status"] == "error"
        assert out["feedback"] == "usa codes"

    def test_json_con_bom(self):
        out = safe_parse_validator_json(
            '\ufeff{"status": "success", "reason": "ok", "feedback": "nada"}'
        )
        assert out["status"] == "success"

    def test_json_en_bloque_markdown(self):
        out = safe_parse_validator_json(
            '```json\n{"status": "error", "reason": "rename", "feedback": "quita rename"}\n```'
        )
        assert out["status"] == "error"
        assert out["feedback"] == "quita rename"
