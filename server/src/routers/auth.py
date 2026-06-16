from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional
from src.database import get_db, UserConfig
from src.engine.bi_analyst import validate_api_key
from src.utils.common import check_authorization, get_authenticated_user
from src.utils.security import encrypt_key, decrypt_key
from src.utils.limiter import limiter

router = APIRouter(tags=["Auth & Config"])

@router.post("/validate-key")
@limiter.limit("5/minute")
@limiter.limit("20/hour")
def validate_key(request: Request, api_key: str = Form(...), provider: str = Form("gemini")):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    is_valid, error = validate_api_key(api_key, provider=provider)
    return {"valid": is_valid, "error": error}

def is_masked(key: str) -> bool:
    if not key: return False
    return "..." in key or key.startswith("xxxx")

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
    if not config:
        return {
            "gemini_key": "", "mistral_key": "", "gamma_key": "", "groq_key": "", "preferred_provider": "gemini",
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
            "chart_theme": "neon"
        }
    return {
        "gemini_key": mask_key(config.gemini_key),
        "mistral_key": mask_key(config.mistral_key),
        "gamma_key": mask_key(config.gamma_key),
        "groq_key": mask_key(config.groq_key),
        "preferred_provider": config.preferred_provider or "gemini",
        "temperature": config.temperature if config.temperature is not None else 0.2,
        "anomaly_sensitivity": config.anomaly_sensitivity if config.anomaly_sensitivity is not None else 2.5,
        "magic_clean_strategy": config.magic_clean_strategy or "remove",
        "currency_format": config.currency_format or "USD",
        "date_format": config.date_format or "DD/MM/YYYY",
        "brand_color": config.brand_color or "#2dd4bf",
        "brand_logo_url": config.brand_logo_url or "",
        "report_org_name": config.report_org_name or "VEKTRA BI",
        "report_footer_text": config.report_footer_text or "Confidencial - Solo uso interno",
        "pdf_orientation": config.pdf_orientation or "portrait",
        "pdf_include_data_table": config.pdf_include_data_table if config.pdf_include_data_table is not None else True,
        "chart_theme": config.chart_theme or "neon"
    }

@router.post("/user-config")
async def set_user_config(
    gemini_key: Optional[str] = Form(None),
    mistral_key: Optional[str] = Form(None),
    gamma_key: Optional[str] = Form(None),
    groq_key: Optional[str] = Form(None),
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
    db: Session = Depends(get_db)
):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    config = db.query(UserConfig).filter(UserConfig.user_id == authenticated_user).first()
    if not config:
        config = UserConfig(user_id=authenticated_user)
        db.add(config)
    
    if gemini_key is not None and not is_masked(gemini_key) and gemini_key.strip() != "":
        config.gemini_key = encrypt_key(gemini_key)
    elif gemini_key == "":
        config.gemini_key = None
        
    if mistral_key is not None and not is_masked(mistral_key) and mistral_key.strip() != "":
        config.mistral_key = encrypt_key(mistral_key)
    elif mistral_key == "":
        config.mistral_key = None
        
    if gamma_key is not None and not is_masked(gamma_key) and gamma_key.strip() != "":
        config.gamma_key = encrypt_key(gamma_key)
    elif gamma_key == "":
        config.gamma_key = None

    if groq_key is not None and not is_masked(groq_key) and groq_key.strip() != "":
        config.groq_key = encrypt_key(groq_key)
    elif groq_key == "":
        config.groq_key = None
        
    if preferred_provider is not None: config.preferred_provider = preferred_provider
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

