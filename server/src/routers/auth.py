from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from src.database import get_db, UserConfig
from src.engine.bi_analyst import validate_api_key
from src.utils.common import check_authorization, get_authenticated_user
from src.utils.security import encrypt_key, decrypt_key

router = APIRouter(tags=["Auth & Config"])

@router.post("/validate-key")
def validate_key(api_key: str = Form(...), provider: str = Form("gemini")):
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
async def get_user_config(user_id: Optional[str] = None, db: Session = Depends(get_db)):
    authenticated_user = get_authenticated_user()
    check_authorization(authenticated_user)
    config = db.query(UserConfig).filter(UserConfig.user_id == authenticated_user).first()
    if not config:
        return {"gemini_key": "", "mistral_key": "", "gamma_key": "", "preferred_provider": "gemini"}
    return {
        "gemini_key": mask_key(config.gemini_key),
        "mistral_key": mask_key(config.mistral_key),
        "gamma_key": mask_key(config.gamma_key),
        "preferred_provider": config.preferred_provider or "gemini"
    }

@router.post("/user-config")
async def set_user_config(
    user_id: Optional[str] = Form(None),
    gemini_key: Optional[str] = Form(None),
    mistral_key: Optional[str] = Form(None),
    gamma_key: Optional[str] = Form(None),
    preferred_provider: Optional[str] = Form(None),
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
        
    if preferred_provider is not None: config.preferred_provider = preferred_provider
    
    db.commit()
    return {"message": "Configuración guardada correctamente"}
