import os
import logging
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional
from src.database import get_db, UserConfig
from src.utils.common import check_authorization, get_authenticated_user
from src.utils.security import decrypt_key
from src.engine.visual_summary_engine import generate_visual_summary
from src.utils.limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Visual Summary"])

@router.post("/visual-summary")
@limiter.limit("5/minute")
@limiter.limit("20/hour")
def get_visual_summary(
    request: Request,
    text: str = Form(...),
    api_key: str = Form(...),
    user_id: Optional[str] = Form(None),
    provider: str = Form("gemini"),
    mistral_key: Optional[str] = Form(None),
    visual_type: Optional[str] = Form(None),
    mode: str = Form("rapido"),
    db: Session = Depends(get_db)
):
    # 1. Verificar Feature Flag
    enable_vs = os.environ.get("ENABLE_VISUAL_SUMMARY", "true").lower() == "true"
    if not enable_vs:
        raise HTTPException(
            status_code=400,
            detail="La funcionalidad experimental de Resumen Visual está desactivada en el servidor."
        )

    authenticated_user = get_authenticated_user()
    # 2. Validar autorización
    check_authorization(authenticated_user)
    
    # 3. Auto-recuperación y descifrado de claves API
    if len(api_key) < 10 or "..." in api_key or (provider == "mistral" and (not mistral_key or len(mistral_key) < 10 or "..." in mistral_key)):
        user_config = db.query(UserConfig).filter(UserConfig.user_id == authenticated_user).first()
        if user_config:
            if (len(api_key) < 10 or "..." in api_key) and user_config.gemini_key:
                api_key = decrypt_key(user_config.gemini_key)
            if provider == "mistral" and (not mistral_key or len(mistral_key) < 10 or "..." in mistral_key) and user_config.mistral_key:
                mistral_key = decrypt_key(user_config.mistral_key)
    else:
        api_key = decrypt_key(api_key)
        if mistral_key:
            mistral_key = decrypt_key(mistral_key)

    # 4. Procesamiento
    try:
        result = generate_visual_summary(
            text=text,
            provider=provider,
            api_key=api_key,
            mistral_key=mistral_key,
            visual_type=visual_type,
            mode=mode
        )
        return result
    except ValueError as ve:
        logger.warning(f"Error de validación en Visual Summary: {ve}")
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logger.error(f"Error generando Visual Summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error en el motor de generación visual: Ocurrió un error interno al procesar el resumen."
        )
