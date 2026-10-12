"""
Registro de proveedores de IA y cliente unificado.

Antes cada proveedor tenía su propio bloque dentro de generate_ai_content() y la
"validación" solo miraba longitud y una regex (sin llamar nunca a la API: una clave
incorrecta pasaba el filtro y el fallo aparecía después, durante el análisis, como un
error confuso).

Aquí se centraliza:
- Metadatos de cada proveedor (modelo por defecto, estilo de API, prefijo de clave).
- normalize_key(): limpia comillas/espacios de un pegado desde el panel del proveedor.
- detect_provider(): deduce el proveedor a partir del prefijo de la clave.
- verify_key(): validación REAL contra el endpoint /models del proveedor (no consume tokens).
- chat(): llamada de generación con el mismo formato para todos.
"""
import json
import logging
import re
from contextvars import ContextVar
from typing import Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# Estilos de API: "gemini" (SDK propio), "openai" (compatible con /chat/completions),
# "anthropic" (API Messages).
PROVIDERS = {
    "gemini": {
        "label": "Google Gemini",
        "style": "gemini",
        "model": "gemini-2.0-flash",
        "prefixes": ("AIzaSy",),
        "min_len": 32,
        "console": "https://aistudio.google.com/apikey",
        "free_tier": True,
    },
    "openai": {
        "label": "OpenAI",
        "style": "openai",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "prefixes": ("sk-proj-", "sk-svcacct-", "sk-"),
        "min_len": 32,
        "console": "https://platform.openai.com/api-keys",
        "free_tier": False,
    },
    "anthropic": {
        "label": "Anthropic Claude",
        "style": "anthropic",
        "base_url": "https://api.anthropic.com/v1",
        "model": "claude-3-5-sonnet-latest",
        "prefixes": ("sk-ant-",),
        "min_len": 40,
        "console": "https://console.anthropic.com/settings/keys",
        "free_tier": False,
    },
    "deepseek": {
        "label": "DeepSeek",
        "style": "openai",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "prefixes": ("sk-",),
        "min_len": 32,
        "console": "https://platform.deepseek.com/api_keys",
        "free_tier": True,
    },
    "groq": {
        "label": "Groq",
        "style": "openai",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "prefixes": ("gsk_",),
        "min_len": 32,
        "console": "https://console.groq.com/keys",
        "free_tier": True,
    },
    "mistral": {
        "label": "Mistral AI",
        "style": "openai",
        "base_url": "https://api.mistral.ai/v1",
        "model": "mistral-large-latest",
        "prefixes": (),
        "min_len": 32,
        "console": "https://console.mistral.ai/api-keys",
        "free_tier": True,
    },
    "openrouter": {
        "label": "OpenRouter",
        "style": "openai",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "openai/gpt-4o-mini",
        "prefixes": ("sk-or-",),
        "min_len": 40,
        "console": "https://openrouter.ai/keys",
        "free_tier": False,
    },
    "nvidia": {
        "label": "NVIDIA NIM",
        "style": "openai",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "model": "nvidia/nemotron-3-super-120b-a12b",
        # El catalogo de NVIDIA cambia sin avisar: cuando retiran un modelo el
        # endpoint responde 410 Gone. En vez de romper, se prueban alternativas.
        "model_fallbacks": [
            "nvidia/nemotron-4-340b-instruct",
            "moonshotai/kimi-k3",
            "deepseek-ai/deepseek-v4.1-flash",
            "openai/gpt-oss-20b",
        ],
        "prefixes": ("nvapi-",),
        "min_len": 40,
        "console": "https://build.nvidia.com/settings/api-keys",
        "free_tier": True,
        # El catalogo de modelos de NVIDIA es publico: GET /models responde 200 sin
        # clave, asi que no sirve para validarla. Se comprueba con una complet minima
        # de 1 token (coste cero) contra el modelo por defecto.
        "verify": "chat",
    },
}

DEFAULT_PROVIDER = "gemini"
KEY_TIMEOUT = 12  # segundos: /models no consume tokens, debe ser rápido


def normalize_key(raw: Optional[str]) -> str:
    """Limpia una clave pegada desde un panel: comillas, espacios y saltos de línea.
    Sin esto, 'AIza...' pegado con comillas falla la validación por formato."""
    if not raw:
        return ""
    key = raw.strip()
    # Quita comillas envolventes (comunes al copiar de un panel o de un email)
    if len(key) >= 2 and key[0] == key[-1] and key[0] in ("'", '"'):
        key = key[1:-1].strip()
    return key


def detect_provider(key: str) -> Optional[str]:
    """Deduce el proveedor por el prefijo de la clave. None si no es concluyente.

    Se comparan TODOS los prefijos de todos los proveedores por longitud (no los del
    proveedor actual), porque varios comparten inicio: 'sk-ant-' (Anthropic) y
    'sk-or-' (OpenRouter) empiezan igual que el 'sk-' de OpenAI/DeepSeek, asi que el
    mas especifico tiene que ganar.
    """
    key = normalize_key(key)
    if not key:
        return None
    candidatos = [
        (prefix, pid)
        for pid, meta in PROVIDERS.items()
        for prefix in meta["prefixes"]
        if key.startswith(prefix)
    ]
    if not candidatos:
        return None
    return max(candidatos, key=lambda c: len(c[0]))[1]


def get_meta(provider: str) -> dict:
    return PROVIDERS.get(provider, PROVIDERS[DEFAULT_PROVIDER])


def catalog() -> list:
    """Catálogo para el frontend: nunca incluye secretos."""
    return [
        {
            "id": pid,
            "label": meta["label"],
            "console": meta["console"],
            "free_tier": meta["free_tier"],
            "min_len": meta["min_len"],
            "prefixes": list(meta["prefixes"]),
        }
        for pid, meta in PROVIDERS.items()
    ]


def _verify_openai_style(provider: str, key: str) -> Tuple[bool, Optional[str]]:
    meta = PROVIDERS[provider]
    try:
        resp = requests.get(
            f"{meta['base_url']}/models",
            headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
            timeout=KEY_TIMEOUT,
        )
    except requests.RequestException as e:
        # Si no hay red, no se puede affirmar que la clave sea inválida.
        return True, None  # validación inconclusive: no bloquear al usuario
    if resp.status_code in (200, 401, 403):
        if resp.status_code == 200:
            return True, None
        body = resp.text.lower()
        if "quota" in body or "billing" in body or "credit" in body:
            return True, "La clave es válida pero la cuenta no tiene créditos o cuota."
        return False, "El proveedor rechazó la clave (401/403). Revísala o genera una nueva."
    if resp.status_code == 429:
        return True, "La clave es válida (límite de peticiones alcanzado en la validación)."
    return False, f"El proveedor respondió {resp.status_code} al validar la clave."


def get_model(provider: str, user_config=None) -> Optional[str]:
    """Modelo elegido por el usuario para ese proveedor, si guardó uno válido."""
    if not user_config:
        return None
    raw = getattr(user_config, "provider_models", None)
    if not raw:
        return None
    try:
        chosen = json.loads(raw).get(provider)
    except Exception:
        return None
    meta = get_meta(provider)
    # Si el proveedor retiró ese modelo del catálogo, se ignora la elección y se usa
    # el por defecto (que a su vez tiene reservas).
    disponibles = [meta["model"], *meta.get("model_fallbacks", [])]
    return chosen if chosen in disponibles else None


def _openai_call(provider: str, key: str, payload_extra: dict, timeout: int, model_override: Optional[str] = None):
    """POST a /chat/completions probando el modelo principal y, si el proveedor lo
    ha retirado (410/404), los de reserva. Devuelve (respuesta, modelo_usado)."""
    meta = PROVIDERS[provider]
    principal = model_override or meta["model"]
    modelos = [principal] + [m for m in meta.get("model_fallbacks", []) if m != principal]
    ultimo = None
    for model in modelos:
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        if provider == "openrouter":
            headers["HTTP-Referer"] = "https://agente-bi.onrender.com"
            headers["X-Title"] = "Vektra BI"
        try:
            resp = requests.post(
                f"{meta['base_url']}/chat/completions",
                headers=headers,
                json={"model": model, **payload_extra},
                timeout=timeout,
            )
        except requests.RequestException:
            raise
        if resp.status_code in (410, 404) and model != modelos[-1]:
            logger.info("%s: el modelo '%s' ya no esta disponible, probando alternativa", provider, model)
            ultimo = resp
            continue
        return resp, model
    raise ultimo if ultimo is not None else None


def _verify_openai_chat(provider: str, key: str) -> Tuple[bool, Optional[str]]:
    """Valida con una complet mínima (1 token). Necesario cuando /models es público
    y responde 200 sin clave (NVIDIA), donde el listado no dice nada."""
    meta = PROVIDERS[provider]
    try:
        resp, model = _openai_call(
            provider, key,
            {"messages": [{"role": "user", "content": "hi"}], "max_tokens": 1},
            timeout=25,
        )
    except requests.RequestException:
        return True, None  # sin red: no se puede afirmar que la clave sea inválida
    if resp is None:
        return False, "Ningún modelo de NVIDIA está disponible ahora mismo. Inténtalo más tarde."
    if resp.status_code == 200:
        return True, None
    if resp.status_code in (401, 403):
        return False, "NVIDIA rechazó la clave (401/403). Revísala o genera una nueva en build.nvidia.com."
    if resp.status_code == 429:
        return True, "La clave es válida (límite de peticiones alcanzado en la validación)."
    if resp.status_code in (404, 410):
        # Agotadas todas las alternativas: NVIDIA retiró los modelos configurados.
        return False, (
            "NVIDIA retiró los modelos que usamos para validar (410 Gone). "
            "Es un problema del catálogo de NVIDIA, no de tu clave."
        )
    return False, f"NVIDIA respondió {resp.status_code} al validar la clave."


def _verify_anthropic(key: str) -> Tuple[bool, Optional[str]]:
    try:
        resp = requests.get(
            "https://api.anthropic.com/v1/models",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
            timeout=KEY_TIMEOUT,
        )
    except requests.RequestException:
        return True, None
    if resp.status_code == 200:
        return True, None
    if resp.status_code in (401, 403):
        return False, "Anthropic rechazó la clave (401/403)."
    if resp.status_code == 429:
        return True, "La clave es válida (límite de peticiones alcanzado)."
    return False, f"Anthropic respondió {resp.status_code} al validar la clave."


def _verify_gemini(key: str) -> Tuple[bool, Optional[str]]:
    try:
        resp = requests.get(
            f"https://generativelanguage.googleapis.com/v1beta/models?key={key}",
            timeout=KEY_TIMEOUT,
        )
    except requests.RequestException:
        return True, None
    if resp.status_code == 200:
        return True, None
    if resp.status_code == 429:
        return True, "La clave es válida (cuota de validación alcanzada)."
    if resp.status_code in (400, 401, 403):
        return False, "Google rechazó la clave (API key not valid)."
    return False, f"Google respondió {resp.status_code} al validar la clave."


def verify_key(provider: str, key: str, timeout_note: bool = True) -> Tuple[bool, Optional[str]]:
    """Valida la clave contra el proveedor real. (válida, mensaje_para_el_usuario)"""
    key = normalize_key(key)
    meta = get_meta(provider)
    if not key:
        return False, "API Key vacía."

    # Se comprueba el charset ANTES que la longitud: un pegado con espacios y comas
    # da un mensaje util ("pegala sin comillas") en lugar de un generico "demasiado corta".
    if not re.match(r"^[A-Za-z0-9._\-]+$", key):
        return False, "La clave contiene caracteres no válidos. Pégala sin comillas ni espacios."
    if len(key) < meta["min_len"]:
        return False, (
            f"La clave de {meta['label']} es demasiado corta "
            f"({len(key)} caracteres, mínimo {meta['min_len']})."
        )

    style = meta["style"]
    if meta.get("verify") == "chat":
        return _verify_openai_chat(provider, key)
    if style == "gemini":
        return _verify_gemini(key)
    if style == "anthropic":
        return _verify_anthropic(key)
    return _verify_openai_style(provider, key)


_models_cache: dict = {"at": 0.0, "data": None}
_MODELS_TTL = 3600  # 1 hora: el catalogo de NVIDIA cambia pocas veces

# Modelo elegido por el usuario para esta peticion. Se propaga con ContextVar (igual
# que request_var en utils/common.py) en vez de añadir un parámetro a las diez
# funciones del motor: el contexto es por petición, así que dos usuarios simultáneos
# con modelos distintos no se pisan.
_model_override: ContextVar = ContextVar("ai_model_override", default=None)


def set_model_override(model: Optional[str]):
    return _model_override.set(model)


def get_model_override() -> Optional[str]:
    return _model_override.get()


def list_models(provider: str) -> dict:
    """Modelos disponibles para un proveedor.

    NVIDIA publica su catalogo sin clave (GET /models responde 200 a cualquiera), asi
    que se listan en vivo y se cachean una hora. Para el resto se devuelve el modelo
    por defecto mas sus reservas.
    """
    meta = get_meta(provider)
    if provider != "nvidia":
        return {
            "provider": provider,
            "models": [meta["model"], *meta.get("model_fallbacks", [])],
            "live": False,
        }

    import time
    now = time.time()
    if _models_cache["data"] and now - _models_cache["at"] < _MODELS_TTL:
        return {"provider": provider, "models": _models_cache["data"], "live": True}

    try:
        resp = requests.get(f"{meta['base_url']}/models", timeout=KEY_TIMEOUT)
        ids = [m["id"] for m in resp.json().get("data", []) if m.get("id")]
    except Exception as e:
        logger.warning("No se pudo listar el catalogo de NVIDIA: %s", type(e).__name__)
        ids = []

    # Se filtran los que no sirven para chatear (embeddings, visión, guardas).
    excluir = ("embed", "guard", "retriev", "detector", "safety", "topic-control", "parse")
    utiles = [i for i in ids if not any(e in i.lower() for e in excluir)]
    utiles.sort()
    _models_cache["data"] = utiles
    _models_cache["at"] = now
    return {"provider": provider, "models": utiles, "live": True}


def resolve_keys(provider: str, api_key: Optional[str], mistral_key: Optional[str],
                 user_config) -> Tuple[str, str, Optional[str]]:
    """Resuelve la clave efectiva de un proveedor.

    El frontend manda lo que tiene en memoria (puede estar vacio, enmascarado
    "abcd...wxyz" o incluso cifrado si venga del storage). Aqui se decide:
      - vacio / enmascarado / demasiado corta -> se toma la cifrada del usuario.
      - empieza por "gAAAA" (cifrado Fernet) -> se descifra tal cual.
      - en otro caso -> se usa tal cual viene.

    Devuelve (api_key, mistral_key, error_para_el_usuario).
    """
    from src.utils.security import decrypt_key

    api_key = normalize_key(api_key)
    mistral_key = normalize_key(mistral_key)

    def from_db(field: str) -> str:
        if not user_config:
            return ""
        stored = getattr(user_config, field, None)
        if not stored:
            return ""
        try:
            return normalize_key(decrypt_key(stored))
        except Exception:
            logger.warning("No se pudo descifrar la clave guardada (%s)", field)
            return ""

    def usable(value: str) -> bool:
        return bool(value) and len(value) >= 10 and "..." not in value

    # Mistral viaja en su propio campo por compatibilidad con el flujo "hybrid".
    if provider == "mistral":
        if not usable(mistral_key):
            mistral_key = from_db("mistral_key")
        elif mistral_key.startswith("gAAAA"):
            mistral_key = normalize_key(decrypt_key(mistral_key))
    else:
        if not usable(api_key):
            api_key = from_db(f"{provider}_key")
        elif api_key.startswith("gAAAA"):
            api_key = normalize_key(decrypt_key(api_key))

    meta = get_meta(provider)
    if provider in PROVIDERS and not api_key and not mistral_key:
        return api_key, mistral_key, (
            f"No hay ninguna clave de {meta['label']} guardada. "
            f"Abre Ajustes → Inteligencia Artificial y pega una clave de {meta['console']}."
        )
    return api_key, mistral_key, None


def chat(provider: str, key: str, prompt: str, temperature: float = 0.7,
         system_instruction: Optional[str] = None, timeout: int = 90,
         model_override: Optional[str] = None) -> str:
    """Generación unificada. Lanza excepción para que el llamador la gestione."""
    key = normalize_key(key)
    meta = get_meta(provider)
    style = meta["style"]

    if style == "gemini":
        from src.engine.bi_analyst import get_client, MODELS  # import perezoso: evita ciclo
        from google.genai import types
        client = get_client(key)
        cfg = {"temperature": temperature}
        if system_instruction:
            cfg["system_instruction"] = system_instruction
        model = MODELS.get("GEMINI_SWARM", meta["model"])
        resp = client.models.generate_content(model=model, contents=prompt,
                                              config=types.GenerateContentConfig(**cfg))
        return resp.text

    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    if style == "anthropic":
        payload = {"model": meta["model"], "max_tokens": 4096,
                   "temperature": temperature, "messages": messages}
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json=payload, timeout=timeout,
        )
        resp.raise_for_status()
        blocks = resp.json().get("content", [])
        return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")

    # OpenAI y compatibles
    payload = {"messages": messages, "temperature": temperature}
    resp, _model = _openai_call(provider, key, payload, timeout=timeout, model_override=model_override)
    if resp is None:
        raise RuntimeError("Ningún modelo disponible en este proveedor ahora mismo.")
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]