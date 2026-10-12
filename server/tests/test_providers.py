"""
Tests del registro de proveedores de IA y de la resolucion de claves.

Contexto: validate_api_key() solo miraba longitud y una regex, sin llamar nunca a
la API. Eso producia dos fallos quevede-: una clave pegada con comillas se rechazaba
como 'formato invalido', y una clave incorrecta pasaba el filtro para fallar mas tarde
durante el analisis con un mensaje confuso.
"""
import os
import sys

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_providers.db")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.engine import providers


class FakeConfig:
    """Sustituto de UserConfig con las claves ya cifradas."""
    def __init__(self, **keys):
        for k, v in keys.items():
            setattr(self, f"{k}_key", v)


class TestNormalizeKey:
    def test_quita_comillas(self):
        assert providers.normalize_key('"AIzaSyABC"') == "AIzaSyABC"
        assert providers.normalize_key("'sk-abc'") == "sk-abc"

    def test_quita_espacios_y_saltos(self):
        assert providers.normalize_key("  sk-abc\n") == "sk-abc"

    def test_vacia_o_none(self):
        assert providers.normalize_key("") == ""
        assert providers.normalize_key(None) == ""

    def test_no_toca_una_clave_sana(self):
        key = "AIzaSyD-1a2B3c4D5e6F7g8H9i0J"
        assert providers.normalize_key(key) == key


class TestDetectProvider:
    @pytest.mark.parametrize("key,expected", [
        ("AIzaSyD-1a2B3c4D5e6F7g8H9i0J-kLmNoPq", "gemini"),
        ("gsk_abc123DEF456ghi789", "groq"),
        ("sk-ant-api03-AbCdEfGhIjKlMnOpQrSt", "anthropic"),
        ("sk-or-v1-0123456789abcdef", "openrouter"),
        ("sk-proj-abc123def456", "openai"),
    ])
    def test_detecta_por_prefijo(self, key, expected):
        assert providers.detect_provider(key) == expected

    def test_no_concluyente_devuelve_none(self):
        assert providers.detect_provider("clave_generica_sin_prefijo") is None
        assert providers.detect_provider("") is None

    def test_prefijo_largo_gana_al_corto(self):
        # sk-proj- debe resolverse a OpenAI, no a DeepSeek (ambos empiezan por sk-)
        assert providers.detect_provider("sk-proj-xyz") == "openai"


class TestVerifyKey:
    def test_vacia(self):
        ok, msg = providers.verify_key("gemini", "")
        assert ok is False and "vac" in msg.lower()

    def test_corta_dice_cuanto_falta(self):
        ok, msg = providers.verify_key("gemini", "AIza")
        assert ok is False
        assert "32" in msg

    def test_comillas_se_limpian_antes_de_validar(self):
        """Una clave correcta pegada con comillas no debe decir 'caracteres invalidos'."""
        ok, msg = providers.verify_key("gemini", '"AIzaSyD-1a2B3c4D5e6F7g8H9i0J-kLmNoPqRsTuVwXyZ"')
        assert "comillas" not in (msg or "")
        assert "caracteres no validos" not in (msg or "")

    def test_caracteres_no_permitidos(self):
        ok, msg = providers.verify_key("gemini", "AIza con espacios y,comas; aqui")
        assert ok is False
        # Sin tildes en la asercion: el mensaje va en espanol para el usuario final
        assert "caracteres" in msg.lower()

    def test_proveedor_desconocido_no_revienta(self):
        ok, _ = providers.verify_key("proveedor_inventado", "clave_corta")
        assert ok is False


class TestResolveKeys:
    def test_usa_la_clave_que_viene_si_es_usable(self):
        key = "sk-proj-abc123def456ghi789jkl012"
        api, mistral, err = providers.resolve_keys("openai", key, None, None)
        assert api == key and err is None

    def test_recupera_de_la_bd_si_viene_enmascarada(self):
        key = "sk-proj-abc123def456ghi789jkl012"
        from src.utils.security import cipher_suite
        cfg = FakeConfig(openai=cipher_suite.encrypt(key.encode()).decode())
        api, _, err = providers.resolve_keys("openai", "sk-p...7890", None, cfg)
        assert api == key, "debe ignorar la mascara y usar la clave guardada"
        assert err is None

    def test_error_util_si_no_hay_ninguna_clave(self):
        api, _, err = providers.resolve_keys("anthropic", "", None, None)
        assert api == ""
        assert err is not None and "anthropic" in err.lower()

    def test_mistral_usa_su_propio_campo(self):
        from src.utils.security import cipher_suite
        key = "0123456789abcdef0123456789abcdef"
        cfg = FakeConfig(mistral=cipher_suite.encrypt(key.encode()).decode())
        api, mistral, err = providers.resolve_keys("mistral", "", None, cfg)
        assert mistral == key and err is None

    def test_hybrid_no_falla_si_falta_una(self):
        """hybrid usa dos claves: el helper no debe quejarse de la que falta."""
        _, _, err = providers.resolve_keys("hybrid", "", "", None)
        assert err is None


class TestCatalog:
    def test_no_expone_secretos(self):
        items = providers.catalog()
        assert items
        for item in items:
            assert set(item) == {"id", "label", "console", "free_tier", "min_len", "prefixes"}

    def test_incluye_los_proveedores_del_mercado(self):
        ids = {p["id"] for p in providers.catalog()}
        assert {"gemini", "openai", "anthropic", "deepseek", "groq", "mistral", "openrouter"} <= ids

    def test_todos_tienen_url_de_consola(self):
        for p in providers.catalog():
            assert p["console"].startswith("https://")