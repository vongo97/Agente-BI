from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from src.database import get_db, UserConfig
from src.engine.bi_analyst import validate_api_key
from src.utils.common import check_authorization

router = APIRouter(tags=["Auth & Config"])

@router.post("/validate-key")
async def validate_key(api_key: str = Form(...), provider: str = Form("gemini")):
    is_valid, error = validate_api_key(api_key, provider=provider)
    return {"valid": is_valid, "error": error}

@router.get("/user-config")
async def get_user_config(user_id: str, db: Session = Depends(get_db)):
    check_authorization(user_id)
    config = db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
    if not config:
        return {"gemini_key": "", "mistral_key": "", "gamma_key": ""}
    return {
        "gemini_key": config.gemini_key,
        "mistral_key": config.mistral_key,
        "gamma_key": config.gamma_key
    }

@router.post("/user-config")
async def set_user_config(
    user_id: str = Form(...),
    gemini_key: Optional[str] = Form(None),
    mistral_key: Optional[str] = Form(None),
    gamma_key: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    check_authorization(user_id)
    config = db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
    if not config:
        config = UserConfig(user_id=user_id)
        db.add(config)
    
    if gemini_key is not None: config.gemini_key = gemini_key
    if mistral_key is not None: config.mistral_key = mistral_key
    if gamma_key is not None: config.gamma_key = gamma_key
    
    db.commit()
    return {"message": "Configuración guardada correctamente"}
