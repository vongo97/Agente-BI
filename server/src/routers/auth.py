from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional
from src.database import get_db, UserConfig
from src.engine.bi_analyst import validate_api_key
from src.utils.common import check_authorization, get_authenticated_user
from src.utils.security import encrypt_key, decrypt_key
from src.utils.limiter import limiter

router = APIRouter(tags=["Auth & Config"])

# Campos de clave por proveedor. Se recorren en bloque para que anadir un proveedor
# nuevo sea una linea en src/engine/providers.py mas una aqui, y no otra copia del
# bloque de if/elif. La clave viaja siempre cifrada; al cliente solo le vuelve
# enmascarada.
PROVIDER_KEY_FIELDS = (
    "gemini_key", "mistral_key", "groq_key",
    "openai_key", "anthropic_key", "deepseek_key", "openrouter_key", "nvidia_key",
)

@router.get("/providers")
def list_providers():
    """Catalogo de proveedores soportados para pintar la pantalla de Ajustes."""
    from src.engine.providers import catalog
    return {"providers": catalog()}

@router.get("/providers/{provider_id}/models")
def list_provider_models(provider_id: str):
    """Modelos disponibles de un proveedor.

    NVIDIA se consulta en vivo a su catalogo publico (con cache de 1 hora), de modo
    que el desplegable de Ajustes no dependa de una lista escrita a mano que se queda
    obsoleta cuando el proveedor retira modelos.
    """
    from src.engine.providers import PROVIDERS, list_models
    if provider_id not in PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Proveedor '{provider_id}' desconocido.")
    return list_models(provider_id)

@router.post("/validate-key")
@limiter.limit("10/minute")
@limiter.limit("40/hour")
def validate_key(request: Request, api_key: str = Form(...), provider: str = Form("gemini"), db: Session = Depends(get_db)):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    from src.engine.providers import detect_provider
    is_valid, message = validate_api_key(api_key, provider=provider)
    detected = detect_provider(api_key)
    # Validacion real + guardado automatico: si la clave es valida y corresponde al
    # proveedor pedido, se cifra y se guarda en la cuenta en la misma llamada.
    if is_valid and (detected is None or detected == provider):
        field = f"{provider}_key"
        if field in PROVIDER_KEY_FIELDS:
            config = db.query(UserConfig).filter(UserConfig.user_id == authenticated_user).first()
            if not config:
                config = UserConfig(user_id=authenticated_user)
                db.add(config)
            setattr(config, field, encrypt_key(api_key))
            db.commit()
    return {
        "valid": is_valid,
        "error": None if is_valid else message,
        "message": message if is_valid else message,
        "detected_provider": detected,
    }

def is_masked(key: str) -> bool:
    if not key: return False
    return "..." in key or key.startswith("xxxx")

def generate_code_verifier(length: int = 64) -> str:
    """Genera un code_verifier seguro usando caracteres URL-safe."""
    import secrets
    import string
    alphabet = string.ascii_letters + string.digits + "-_.~"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def derive_code_challenge(code_verifier: str) -> str:
    """Deriva un code_challenge usando SHA256 y base64 URL-safe sin padding."""
    import hashlib
    import base64
    sha256 = hashlib.sha256(code_verifier.encode('utf-8'))
    challenge = base64.urlsafe_b64encode(sha256.digest()).decode('utf-8').replace('=', '')
    return challenge

def mask_key(encrypted_key: Optional[str]) -> str:
    if not encrypted_key: return ""
    try:
        decrypted = decrypt_key(encrypted_key)
        if not decrypted: return ""
        if len(decrypted) <= 8:
            return "xxxx...xxxx"
        return f"{decrypted[:4]}...{decrypted[-4:]}"
    except Exception:
        return "xxxx...xxxx"

@router.get("/user-config")
async def get_user_config(db: Session = Depends(get_db)):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    config = db.query(UserConfig).filter(UserConfig.user_id == authenticated_user).first()

    defaults = {
        "preferred_provider": "gemini",
        "temperature": 0.2,
        "anomaly_sensitivity": 2.5,
        "magic_clean_strategy": "remove",
        "currency_format": "USD",
        "date_format": "DD/MM/YYYY",
        "brand_color": "#2dd4bf",
        "brand_logo_url": "",
        "report_org_name": "VEKTRA BI",
        "report_footer_text": "Confidencial - Solo uso interno",
        "pdf_orientation": "portrait",
        "pdf_include_data_table": True,
        "chart_theme": "neon",
    }

    if not config:
        payload = {f: "" for f in PROVIDER_KEY_FIELDS}
        payload["gamma_key"] = ""
        payload.update(defaults)
        return payload

    payload = {f: mask_key(getattr(config, f, None)) for f in PROVIDER_KEY_FIELDS}
    payload["gamma_key"] = mask_key(config.gamma_key)
    import json as _json
    try:
        payload["provider_models"] = _json.loads(config.provider_models or "{}")
    except Exception:
        payload["provider_models"] = {}
    for field, fallback in defaults.items():
        value = getattr(config, field, None)
        payload[field] = fallback if value is None else value
    return payload

@router.post("/user-config")
@limiter.limit("10/minute")
async def set_user_config(
    request: Request,
    gemini_key: Optional[str] = Form(None),
    mistral_key: Optional[str] = Form(None),
    gamma_key: Optional[str] = Form(None),
    groq_key: Optional[str] = Form(None),
    openai_key: Optional[str] = Form(None),
    anthropic_key: Optional[str] = Form(None),
    deepseek_key: Optional[str] = Form(None),
    openrouter_key: Optional[str] = Form(None),
    nvidia_key: Optional[str] = Form(None),
    preferred_provider: Optional[str] = Form(None),
    temperature: Optional[float] = Form(None),
    anomaly_sensitivity: Optional[float] = Form(None),
    magic_clean_strategy: Optional[str] = Form(None),
    currency_format: Optional[str] = Form(None),
    date_format: Optional[str] = Form(None),
    brand_color: Optional[str] = Form(None),
    brand_logo_url: Optional[str] = Form(None),
    report_org_name: Optional[str] = Form(None),
    report_footer_text: Optional[str] = Form(None),
    pdf_orientation: Optional[str] = Form(None),
    pdf_include_data_table: Optional[bool] = Form(None),
    chart_theme: Optional[str] = Form(None),
    provider_models: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    config = db.query(UserConfig).filter(UserConfig.user_id == authenticated_user).first()
    if not config:
        config = UserConfig(user_id=authenticated_user)
        db.add(config)
    
    # Claves de proveedor en bloque. Se leen del formulario para no repetir el mismo
    # if/elif por cada proveedor anadido: vacio = borrar, enmascarada = no tocar
    # (el frontend reenvia "abcd...wxyz" y no queremos pisar la clave real con eso),
    # cualquier otro valor = guardar cifrado.
    form = await request.form()
    for field in PROVIDER_KEY_FIELDS + ("gamma_key",):
        if field not in form:
            continue
        value = str(form.get(field) or "")
        if value == "":
            setattr(config, field, None)
        elif not is_masked(value):
            setattr(config, field, encrypt_key(value))
        
    if preferred_provider is not None: config.preferred_provider = preferred_provider

    # Modelos elegidos por el usuario (JSON). Se fusiona con lo que ya habia: el
    # frontend puede enviar solo el proveedor que acaba de cambiar sin borrar el resto.
    if provider_models:
        import json as _json
        try:
            elegidos = _json.loads(provider_models)
        except Exception:
            elegidos = None
        if isinstance(elegidos, dict) and elegidos:
            actuales = {}
            if config.provider_models:
                try:
                    actuales = _json.loads(config.provider_models) or {}
                except Exception:
                    actuales = {}
            actuales.update({str(k): str(v) for k, v in elegidos.items() if v})
            config.provider_models = _json.dumps(actuales)
    if temperature is not None: config.temperature = temperature
    if anomaly_sensitivity is not None: config.anomaly_sensitivity = anomaly_sensitivity
    if magic_clean_strategy is not None: config.magic_clean_strategy = magic_clean_strategy
    if currency_format is not None: config.currency_format = currency_format
    if date_format is not None: config.date_format = date_format
    if brand_color is not None: config.brand_color = brand_color
    if brand_logo_url is not None: config.brand_logo_url = brand_logo_url
    if report_org_name is not None: config.report_org_name = report_org_name
    if report_footer_text is not None: config.report_footer_text = report_footer_text
    if pdf_orientation is not None: config.pdf_orientation = pdf_orientation
    if pdf_include_data_table is not None: config.pdf_include_data_table = pdf_include_data_table
    if chart_theme is not None: config.chart_theme = chart_theme
    
    db.commit()
    return {"message": "Configuración guardada correctamente"}

