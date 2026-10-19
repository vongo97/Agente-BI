"""Tests de regresion para P-04: cada proveedor usa SOLO su propia clave.

Antes, `dashboard.py`, `visual_summary.py` y `data.py` repetian este bloque:

    elif (len(api_key) < 10 or "..." in api_key) and user_config.gemini_key:
        api_key = decrypt_key(user_config.gemini_key)

sin mirar el proveedor activo. Con OpenAI / Anthropic / DeepSeek / OpenRouter /
NVIDIA seleccionado, la clave de Google acababa enviandose a otro tercero.

Ahora las tres rutas pasan por `resolve_keys()`, que solo lee `"{provider}_key"`
(con `hybrid` como unica excepcion documentada: Gemini + Mistral).
"""
import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.engine.providers import resolve_keys  # noqa: E402
from src.utils.security import encrypt_key  # noqa: E402

ROUTERS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "routers"))
RUTAS_CON_FALLBACK = ("dashboard.py", "visual_summary.py", "data.py")

GEMINI = "AIzaGEMINI-fake-key-123456"
OPENAI = "sk-openai-fake-key-123456"
ANTHROPIC = "sk-ant-fake-key-123456"
DEEPSEEK = "sk-deepseek-fake-key-123456"
GROQ = "gsk_groq_fake_key_123456"
MISTRAL = "mistral-fake-key-123456"
OPENROUTER = "sk-or-fake-key-123456"
NVIDIA = "nvapi-fake-key-123456"


class FakeUserConfig:
    """Sustituto de la fila UserConfig: solo los campos que consulta resolve_keys."""

    def __init__(self, **fields):
        for name, value in fields.items():
            setattr(self, name, value)


def cfg_completa() -> FakeUserConfig:
    return FakeUserConfig(
        gemini_key=encrypt_key(GEMINI),
        openai_key=encrypt_key(OPENAI),
        anthropic_key=encrypt_key(ANTHROPIC),
        deepseek_key=encrypt_key(DEEPSEEK),
        groq_key=encrypt_key(GROQ),
        mistral_key=encrypt_key(MISTRAL),
        openrouter_key=encrypt_key(OPENROUTER),
        nvidia_key=encrypt_key(NVIDIA),
    )


class ResolveKeysNoCruzaClavesTest(unittest.TestCase):
    """El corazon de P-04: ninguna clave se sustituye por la de otro proveedor."""

    def setUp(self):
        self.cfg = cfg_completa()

    def test_openai_no_recibe_la_clave_de_gemini(self):
        api, mistral, error = resolve_keys("openai", "sk-open...xxx", None, self.cfg)
        self.assertEqual(api, OPENAI)
        self.assertNotIn("GEMINI", api)
        self.assertIsNone(error)

    def test_anthropic_vacio_usa_su_propia_clave(self):
        api, _, error = resolve_keys("anthropic", "", None, self.cfg)
        self.assertEqual(api, ANTHROPIC)
        self.assertNotIn("GEMINI", api)
        self.assertIsNone(error)

    def test_deepseek_openrouter_nvidia(self):
        for provider, esperada in (
            ("deepseek", DEEPSEEK),
            ("openrouter", OPENROUTER),
            ("nvidia", NVIDIA),
        ):
            with self.subTest(provider=provider):
                api, _, error = resolve_keys(provider, "masked...key" , None, self.cfg)
                self.assertEqual(api, esperada)
                self.assertNotIn("GEMINI", api)
                self.assertIsNone(error)

    def test_groq_usa_su_clave(self):
        api, _, error = resolve_keys("groq", "", None, self.cfg)
        self.assertEqual(api, GROQ)
        self.assertIsNone(error)

    def test_gemini_sigue_usando_gemini(self):
        api, _, error = resolve_keys("gemini", "", None, self.cfg)
        self.assertEqual(api, GEMINI)
        self.assertIsNone(error)

    def test_mistral_viaja_en_su_propio_campo(self):
        api, mistral, error = resolve_keys("mistral", "clave-de-gemini", "", self.cfg)
        self.assertEqual(mistral, MISTRAL)
        self.assertNotEqual(api, GEMINI)  # nunca se cuela Gemini como clave Mistral
        self.assertIsNone(error)

    def test_hybrid_usa_gemini_y_mistral(self):
        api, mistral, error = resolve_keys("hybrid", "", None, self.cfg)
        self.assertEqual(api, GEMINI)
        self.assertEqual(mistral, MISTRAL)
        self.assertIsNone(error)

    def test_clave_del_cliente_manda_si_es_utilizable(self):
        enviada = "sk-openai-enviada-por-el-cliente-123456"
        api, _, error = resolve_keys("openai", enviada, None, self.cfg)
        self.assertEqual(api, enviada)
        self.assertNotIn("GEMINI", api)
        self.assertIsNone(error)

    def test_sin_clave_propia_devuelve_error_y_no_la_de_gemini(self):
        cfg = FakeUserConfig(gemini_key=encrypt_key(GEMINI))  # solo tiene Gemini
        api, _, error = resolve_keys("openai", "", None, cfg)
        self.assertEqual(api, "")
        self.assertNotIn("GEMINI", api)
        self.assertIsNotNone(error, "Debe pedir la clave de OpenAI, no reusar la de Gemini")


class RoutersSinFallbackAGeminiTest(unittest.TestCase):
    """Guardia estatica: el patron viejo no puede volver a aparecer."""

    def test_no_queda_user_config_gemini_key_en_routers(self):
        for nombre in RUTAS_CON_FALLBACK:
            with self.subTest(archivo=nombre):
                with open(os.path.join(ROUTERS_DIR, nombre), "r", encoding="utf-8") as fh:
                    fuente = fh.read()
                self.assertNotIn(
                    "user_config.gemini_key",
                    fuente,
                    f"P-04: {nombre} sigue resolviendo claves a mano; usa resolve_keys()",
                )

    def test_los_routers_usan_resolve_keys(self):
        for nombre in RUTAS_CON_FALLBACK:
            with self.subTest(archivo=nombre):
                with open(os.path.join(ROUTERS_DIR, nombre), "r", encoding="utf-8") as fh:
                    fuente = fh.read()
                self.assertIn(
                    "resolve_keys(provider",
                    fuente,
                    f"P-04: {nombre} debe resolver la clave con resolve_keys(provider, ...)",
                )


class SimulationSinCruceDeClavesTest(unittest.TestCase):
    """simulation.py tenia dos fugas: el enjambre usaba la clave de Gemini como
    clave del proveedor activo (create_simulation y generate-agents)."""

    def setUp(self):
        with open(os.path.join(ROUTERS_DIR, "simulation.py"), "r", encoding="utf-8") as fh:
            self.fuente = fh.read()

    def _cuerpo(self, nombre_func: str) -> str:
        """Devuelve el cuerpo del endpoint hasta el siguiente @router."""
        inicio = self.fuente.index(f"async def {nombre_func}")
        resto = self.fuente[inicio + 1:]
        siguiente = resto.find("\n@router.")
        fin = len(self.fuente) if siguiente == -1 else inicio + 1 + siguiente
        return self.fuente[inicio:fin]

    def test_create_simulation_no_usa_gemini_como_clave_del_proveedor(self):
        cuerpo = self._cuerpo("create_simulation")
        self.assertNotIn("api_key = decrypt_key(config.gemini_key)", cuerpo)
        self.assertIn("resolve_keys(req.provider", cuerpo)

    def test_generate_agents_no_usa_gemini_como_clave_del_proveedor(self):
        cuerpo = self._cuerpo("generate_agents_endpoint")
        self.assertNotIn('else (groq_key if prov == "groq" else gemini_key)', cuerpo)
        self.assertIn("resolve_keys(prov", cuerpo)

    def test_gemini_key_solo_para_el_cliente_de_gemini(self):
        self.assertIn(
            'gemini_key = key if prov == "gemini" else',
            self.fuente,
            "P-04: gemini_key debe alimentar solo al cliente de Gemini del enjambre",
        )


if __name__ == "__main__":
    unittest.main()
