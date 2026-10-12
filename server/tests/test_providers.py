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


class TestNvidia:
    """NVIDIA tiene el catalogo de modelos PUBLICO (GET /models responde 200 sin
    clave), asi que validar por listado daria 'valida' para cualquier basura.
    Ademas retiran modelos sin avisar: eso responde 410 Gone."""

    def test_detecta_prefijo_nvapi(self):
        assert providers.detect_provider("nvapi-" + "a" * 60) == "nvidia"

    def test_se_valida_con_chat_no_con_modelos(self):
        meta = providers.get_meta("nvidia")
        assert meta["verify"] == "chat"

    def test_es_gratuito(self):
        assert providers.get_meta("nvidia")["free_tier"] is True

    def test_chat_de_validacion_no_gasta_tokens(self, monkeypatch):
        capturado = {}

        class Resp:
            status_code = 200

            def json(self):
                return {"choices": [{"message": {"content": "h"}}]}

        def fake_post(url, headers=None, json=None, timeout=None):
            capturado["url"] = url
            capturado["json"] = json
            return Resp()

        monkeypatch.setattr(providers.requests, "post", fake_post)
        ok, _ = providers.verify_key("nvidia", "nvapi-" + "a" * 60)
        assert ok is True
        assert capturado["json"]["max_tokens"] == 1, "la validacion debe costar 0 tokens"

    def test_chat_rechaza_clave_invalida(self, monkeypatch):
        class Resp:
            status_code = 401
            text = "invalid api key"

        monkeypatch.setattr(providers.requests, "post", lambda *a, **k: Resp())
        ok, msg = providers.verify_key("nvidia", "nvapi-" + "a" * 60)
        assert ok is False and msg

    def test_sin_red_no_bloquea_al_usuario(self, monkeypatch):
        def boom(*a, **k):
            raise providers.requests.RequestException("sin red")

        monkeypatch.setattr(providers.requests, "post", boom)
        ok, _ = providers.verify_key("nvidia", "nvapi-" + "a" * 60)
        assert ok is True

    def test_tiene_modelos_de_reserva(self):
        """Regresión: 'meta/llama-3.3-70b-instruct' dio 410 Gone (retirado del
        catalogo). El proveedor debe traer alternativas para no quedarse muerto."""
        meta = providers.get_meta("nvidia")
        assert meta["model_fallbacks"], "NVIDIA necesita modelos de reserva"
        assert meta["model"] not in meta["model_fallbacks"]


class TestModeloRetirado:
    def test_410_cambia_al_siguiente_modelo(self, monkeypatch):
        """Si el modelo principal devuelve 410, se prueba el siguiente."""
        vistos = []

        class Resp410:
            status_code = 410

        class Resp200:
            status_code = 200

            def raise_for_status(self):
                return None

            def json(self):
                return {"choices": [{"message": {"content": "hola"}}]}

        def fake_post(url, headers=None, json=None, timeout=None):
            vistos.append(json["model"])
            return Resp410() if len(vistos) == 1 else Resp200()

        monkeypatch.setattr(providers.requests, "post", fake_post)
        texto = providers.chat("nvidia", "nvapi-" + "a" * 60, "hola")
        assert texto == "hola"
        assert len(vistos) >= 2, "debe haber intentado un segundo modelo"

    def test_si_todos_estan_retirados_da_error_claro(self, monkeypatch):
        class Resp410:
            status_code = 410

        monkeypatch.setattr(providers.requests, "post", lambda *a, **k: Resp410())
        ok, msg = providers.verify_key("nvidia", "nvapi-" + "a" * 60)
        assert ok is False
        assert "retir" in msg.lower() or "disponible" in msg.lower()


class TestListModels:
    """El desplegable de Ajustes se alimenta de aquí, para no mantener a mano una
    lista de modelos que queda obsoleta cuando el proveedor retira modelos."""

    def test_otros_proveedores_devuelven_el_por_defecto(self):
        r = providers.list_models("groq")
        assert r["live"] is False
        assert r["models"][0] == providers.get_meta("groq")["model"]

    def test_nvidia_consulta_el_catalogo_en_vivo(self, monkeypatch):
        class Resp:
            def json(self):
                return {"data": [
                    {"id": "nvidia/nemotron-3-super-120b-a12b"},
                    {"id": "nvidia/nv-embedqa-mistral-7b-v2"},   # embedding: debe filtrarse
                    {"id": "meta/llama-guard-4-12b"},             # guard: fuera
                    {"id": "moonshotai/kimi-k3"},
                ]}

        monkeypatch.setattr(providers.requests, "get", lambda *a, **k: Resp())
        providers._models_cache.update({"at": 0.0, "data": None})
        r = providers.list_models("nvidia")
        assert r["live"] is True
        assert "moonshotai/kimi-k3" in r["models"]
        assert not any("embed" in m for m in r["models"])
        assert not any("guard" in m for m in r["models"])

    def test_cache_de_una_hora(self, monkeypatch):
        llamadas = []

        class Resp:
            def json(self):
                return {"data": [{"id": "moonshotai/kimi-k3"}]}

        def fake_get(*a, **k):
            llamadas.append(1)
            return Resp()

        monkeypatch.setattr(providers.requests, "get", fake_get)
        providers._models_cache.update({"at": 0.0, "data": None})
        providers.list_models("nvidia")
        providers.list_models("nvidia")
        providers.list_models("nvidia")
        assert len(llamadas) == 1, "el catálogo debe consultarse una vez por hora"

    def test_sin_red_devuelve_lista_vacia_sin_romper(self, monkeypatch):
        def boom(*a, **k):
            raise providers.requests.RequestException("sin red")

        monkeypatch.setattr(providers.requests, "get", boom)
        providers._models_cache.update({"at": 0.0, "data": None})
        assert providers.list_models("nvidia")["models"] == []


class TestModeloElegidoPorUsuario:
    class Cfg:
        def __init__(self, raw):
            self.provider_models = raw

    def test_usa_el_modelo_elegido(self):
        cfg = self.Cfg('{"nvidia": "moonshotai/kimi-k3"}')
        assert providers.get_model("nvidia", cfg) == "moonshotai/kimi-k3"

    def test_ignora_json_corrupto(self):
        assert providers.get_model("nvidia", self.Cfg("no es json")) is None
        assert providers.get_model("nvidia", self.Cfg(None)) is None
        assert providers.get_model("nvidia", None) is None

    def test_ignora_modelo_que_nvidia_ya_retiro(self):
        """Elegir un modelo que sale del catálogo no debe romper el análisis: se
        vuelve al por defecto (que a su vez tiene reservas)."""
        cfg = self.Cfg('{"nvidia": "meta/llama-3.3-70b-instruct"}')
        assert providers.get_model("nvidia", cfg) is None

    def test_contextvar_a_isla_peticiones(self):
        token = providers.set_model_override("moonshotai/kimi-k3")
        assert providers.get_model_override() == "moonshotai/kimi-k3"
        providers._model_override.reset(token)
        assert providers.get_model_override() is None


class TestCatalog:
    def test_no_expone_secretos(self):
        items = providers.catalog()
        assert items
        for item in items:
            assert set(item) == {"id", "label", "console", "free_tier", "min_len", "prefixes"}

    def test_incluye_los_proveedores_del_mercado(self):
        ids = {p["id"] for p in providers.catalog()}
        assert {"gemini", "openai", "anthropic", "deepseek", "groq", "mistral", "openrouter", "nvidia"} <= ids

    def test_todos_tienen_url_de_consola(self):
        for p in providers.catalog():
            assert p["console"].startswith("https://")