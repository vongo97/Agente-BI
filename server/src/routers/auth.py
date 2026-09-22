from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from sqlalchemy.orm import Session
from typing import Optional
import logging
import secrets
import json
from datetime import datetime, timedelta
from src.database import get_db, UserConfig
from src.engine.bi_analyst import validate_api_key
from src.utils.common import check_authorization, get_authenticated_user
from src.utils.security import encrypt_key, decrypt_key
from src.utils.limiter import limiter
from src.utils.mobile_security import validate_mobile_request_security
from src.utils.pkce_storage_factory import PKCEStorageFactory
from src.utils.pkce_middleware import PKCEAuthMiddleware

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Auth & Config"])

# Initialize PKCE middleware with Redis storage and mobile security
pkce_storage_factory = PKCEStorageFactory()
pkce_auth_middleware_instance = PKCEAuthMiddleware(
    app=None,
    exclude_paths=[
        "/docs",
        "/redoc",
        "/openapi.json",
        "/health",
        "/static",
        "/auth/validate-key",
        "/auth/generate-pkce",
        "/auth/validate-pkce-flow",
        "/api/v1/authorization",
        "/api/v1/analyze",
        "/api/v1/suggest-questions",
        "/api/v1/detect-anomalies",
        "/api/v1/generate-report-summary"
    ],
    storage_factory=pkce_storage_factory,
    strict_validation=True,
    rate_limit_per_ip=100,
    rate_limit_per_user=30
)

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

# PKCE endpoints for mobile app integration
@router.post("/generate-pkce")
@limiter.limit("10/minute")
def generate_pkce(request: Request, storage_type: str = Form("redis")):
    """Generate and store new PKCE (Proof Key for Code Exchange) for secure OAuth2 mobile authentication."""
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    
    try:
        # Generate new auth_code for the user
        import secrets
        auth_code = f"{authenticated_user}_{secrets.token_urlsafe(32)}"
        
        # Generate and store new PKCE par
        storage = pkce_storage_factory.create_storage(storage_type)
        expires_in = 600  # 10 minutes in seconds
        
        code_verifier = secrets.token_urlsafe(64)
        import hashlib, base64
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().replace('=', '')
        
        if storage.store_auth_code(auth_code, code_verifier, expires_in=timedelta(minutes=10)):
            return {
                "auth_code": auth_code,
                "code_verifier": code_verifier,
                "code_challenge": code_challenge,
                "expires_in": expires_in,
                "storage_type": storage_type,
                "message": "PKCE pair generated successfully for mobile OAuth2",
                "security_level": "high_risk_mitigated: persistent_512bit_entropy"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to store PKCE pair")
            
    except Exception as e:
        logger.error(f"PKCE generation error for user {authenticated_user}: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating PKCE: {str(e)}")

@router.post("/validate-pkce-flow")
@limiter.limit("20/minute")
def validate_pkce_flow(
    request: Request,
    auth_code: str = Form(...),
    code_verifier: str = Form(...),
    storage_type: str = Form("redis")
):
    """Validate PKCE auth code with code_verifier for secure mobile app authentication."""
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    
    # Validate user auth_code match to prevent authorization bypass
    if not auth_code.startswith(authenticated_user):
        raise HTTPException(status_code=403, detail="Invalid auth code format")
    
    storage = pkce_storage_factory.create_storage(storage_type)
    auth_data = storage.get_auth_code(auth_code)
    
    if not auth_data:
        return {
            "valid": False,
            "message": "PKCE auth code not found or expired",
            "error_code": "PKCE_INVALID_AUTH_CODE"
        }
    
    if auth_data.get('used'):
        return {
            "valid": False,
            "message": "PKCE auth code already used",
            "error_code": "PKCE_ALREADY_USED"
        }
    
    if not secrets.compare_digest(auth_data['code_verifier'], code_verifier):
        return {
            "valid": False,
            "message": "Invalid PKCE code verifier",
            "error_code": "PKCE_INVALID_VERIFIER"
        }
    
    marked = storage.mark_code_as_used(auth_code)
    
    if marked:
        return {
            "valid": True,
            "message": "PKCE validation successful - proceeding to OAuth2 token exchange",
            "success_code": "PKCE_AUTH_SUCCESS_001",
            "auth_code": auth_code,
            "security_score": 95
        }
    else:
        return {
            "valid": False,
            "message": "Failed to complete PKCE validation",
            "error_code": "PKCE_STORAGE_FAILURE"
        }

@router.post("/validate-key")
@limiter.limit("5/minute")
@limiter.limit("20/hour")
def validate_key(request: Request, api_key: str = Form(...), provider: str = Form("gemini")):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    
    # Apply mobile security validation for improved mobile app security
    security_result = validate_mobile_request_security(request)
    if not security_result['valid']:
        raise HTTPException(
            status_code=403,
            detail=f"Security validation failed: {security_result['message']}"
        )
    
    # Enhanced API key validation with strict format checking
    is_valid, error = validate_api_key(api_key, provider=provider)
    return {"valid": is_valid, "error": error, "security_info": security_result}