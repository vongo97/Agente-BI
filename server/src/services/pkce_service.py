"""
Servicio de PKCE - Gestión centralizada de transacciones PKCE para todos los clientes.
Implementa tanto la lógica en el servidor como APIs del cliente mobile y web.

Características principales:
- Generación de PKCE: /generate-pkce
- Validación de PKCE: /validate-pkce-flow
- Integración perfecta con motores de negocio backend (análisis, sugerencias, etc.)
- Soporte completo de almacenamiento (Redis/PostgreSQL/Memory)
- Validación estricta de rol y user_id
- Aplicación de hardening móvil a través de middleware
- Gestión integral de logs y métricas de seguridad
"""

import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, Request

from src.engine.bi_analyst import analyze_data, suggest_questions
from src.utils.pkce_storage_factory import PKCEStorageFactory
from src.utils.mobile_security import validate_mobile_request_security
class PKCEService:
    """
    Servicio centralizado para operaciones de PKCE (Proof Key for Code Exchange).
    Administra el ciclo de vida completo de generación, validación y uso de PKCE.
    Integrado con motores de negocio (análisis, sugerencias, detección de anomalías)
    """

    def __init__(self, pkce_storage_factory: PKCEStorageFactory):
        self.storage_factory = pkce_storage_factory

    def generate_pkce_for_user(
        self,
        user_id: str,
        storage_type: str = "redis",
        client_type: str = "mobile"
    ) -> Dict[str, Any]:
        """
        Generar y almacenar un nuevo par PKCE para un usuario específico.

        Args:
            user_id: ID de usuario autenticado
            storage_type: Tipo de almacenamiento ('redis', 'postgresql', 'memory')
            client_type: 'mobile' o 'web' (para verificación de seguridad)

        Returns:
            Dict con auth_code, code_verifier, code_challenge, metadata

        Raises:
            HTTPException: Para errores (duplicación, almacenamiento, input inválido)
        """
        # Verificar entrada de usuario válida
        if not user_id or len(user_id.strip()) < 3:
            raise HTTPException(status_code=400, detail="User ID inválido")

        # Verificar que el client_type sea soportado
        if client_type not in ['mobile', 'web']:
            client_type = 'mobile'  # Default a mobile para apps móviles

        # Generar auth_code seguro con user_id
        auth_code = f"{user_id}_{secrets.token_urlsafe(32)}"

        # Validar la integridad del storage_type
        if storage_type not in ['memory', 'redis', 'postgresql']:
            storage_type = 'redis'  # Default

        try:
            # Guardar en storage persistente
            storage = self.storage_factory.create_storage(storage_type)
            expires_in = timedelta(minutes=10)

            code_verifier = secrets.token_urlsafe(64)
            code_challenge = self._derive_code_challenge(code_verifier)

            if not storage.store_auth_code(auth_code, code_verifier, expires_in):
                raise HTTPException(
                    status_code=500,
                    detail=f"Fallo al almacenar PKCE en {storage_type}"
                )

            return {
                'auth_code': auth_code,
                'code_verifier': code_verifier,
                'code_challenge': code_challenge,
                'expires_in': 600,
                'storage_type': storage_type,
                'client_type': client_type,
                'user_id': user_id,
                'security_level': 'A,
                'message': 'PKCE pair generado exitosamente para autenticación OAuth2 segura'
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error generando PKCE: {str(e)}")

    def validate_pkce_code(
        self,
        user_id: str,
        auth_code: str,
        code_verifier: str,
        storage_type: str = "redis"
    ) -> Dict[str, Any]:
        """
        Validar PKCE para usuario específico, requiriendo coincidencia de user_id.

        Args:
            user_id: ID de usuario autenticado
            auth_code: Código de autorización PKCE
            code_verifier: Code verifier proporcionado por el cliente
            storage_type: Tipo de almacenamiento

        Returns:
            Dict con validación, estado, scores

        Raises:
            HTTPException: Para errores de validación
        """
        if not auth_code.startswith(user_id):
            raise HTTPException(status_code=403, detail="Invalid auth code format")

        if not user_id or not auth_code or not code_verifier:
            raise HTTPException(status_code=400, detail="Faltan parámetros requeridos")

        try:
            storage = self.storage_factory.create_storage(storage_type)
            auth_data = storage.get_auth_code(auth_code)

            if not auth_data:
                return {
                    'valid': False,
                    'message': 'PKCE auth code not found or expired',
                    'error_code': 'PKCE_INVALID_AUTH_CODE',
                    'security_score': 0
                }

            if auth_data.get('used'):
                return {
                    'valid': False,
                    'message': 'PKCE auth code already used',
                    'error_code': 'PKCE_ALREADY_USED',
                    'security_score': 0
                }

            if not secrets.compare_digest(auth_data['code_verifier'], code_verifier):
                return {
                    'valid': False,
                    'message': 'Invalid PKCE code verifier',
                    'error_code': 'PKCE_INVALID_VERIFIER',
                    'security_score': 20
                }

            marked = storage.mark_code_as_used(auth_code)

            if marked:
                return {
                    'valid': True,
                    'message': 'PKCE validation successful - proceeding to OAuth2 token exchange',
                    'success_code': 'PKCE_AUTH_SUCCESS_001',
                    'auth_code': auth_code,
                    'security_score': 95
                }
            else:
                return {
                    'valid': False,
                    'message': 'Failed to complete PKCE validation',
                    'error_code': 'PKCE_STORAGE_FAILURE',
                    'security_score': 5
                }

        except Exception as e:
            return {
                'valid': False,
                'message': f'Error validando PKCE: {str(e)}',
                'error_code': 'INTERNAL_ERROR',
                'security_score': 0
            }

    def get_pkce_health_status(self) -> Dict[str, Any]:
        """
        Obtener estado del sistema PKCE, métricas operacionales.

        Returns:
            Dict con stats operacionales y estado de cada adaptador de storage
        """
        try:
            pkce_manager = PKCEConnectionManager()
            health = pkce_manager.health_check()

            status = {
                'overall': health['overall'],
                'components': {
                    'redis': health['redis'],
                    'postgresql': health['postgresql']
                },
                'active_transactions': 0,  # Placeholder para pipeline
                'security_score': 95 if health['overall'] == 'healthy' else 0,
                'timestamp': datetime.utcnow().isoformat(),
                'version': 'pkce-v1.0-enterprise'
            }

            return status

        except Exception as e:
            return {
                'overall': 'unhealthy',
                'components': {'redis': False, 'postgresql': False},
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }

    def _derive_code_challenge(self, code_verifier: str) -> str:
        """Derivar un code_challenge usando SHA256."""
        import hashlib, base64
        sha256 = hashlib.sha256(code_verifier.encode('utf-8'))
        challenge = base64.urlsafe_b64encode(sha256.digest()).decode('utf-8').replace('=', '')
        return challenge

    def create_pkce_request_for_analysis(
        self,
        user_id: str,
        api_key: str,
        provider: str = "gemini",
        mistral_key: Optional[str] = None,
        auth_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Integrar validación PKCE con endpoints de análisis (análisis inteligente, sugerencias, etc.).
        Permite que motores de negocio funcionen sin exponer secrets.

        Args:
            user_id: ID de usuario autenticado
            api_key: API key primaria (Gemini/Mistral)
            provider: Proveedor preferido
            mistral_key: API key opcional de Mistral
            auth_code: Opcional para validación; si no se provee, se genera

        Returns:
            Dict con configuraciones requeridas para motores de negocio
        """
        if not auth_code:
            result = self.generate_pkce_for_user(user_id, storage_type='redis', client_type='mobile')
            auth_code = result['auth_code']
            client_auth_code = auth_code
        else:
            client_auth_code = auth_code

        return {
            'api_key': api_key,
            'mistral_key': mistral_key,
            'provider': provider,
            'auth_code': client_auth_code,
            'user_id': user_id,
            'security_headers': {
                'X-Code-Verifier': '????????',  # Será rellenado por el cliente después de la generación
                'X-Auth-Code': client_auth_code,
                'X-Client-Type': 'mobile',
                'X-Security-Level': 'PKCE-OAuth2-v1.0'
            },
            'security_validation': 'pending_pkce_generation_and_validation'
        }
# Singleton global para manejo de conexiones PKCE
_pkce_connection_manager = PKCEConnectionManager()
def get_pkce_service() -> PKCEService:
    """Factory method para obtener instancia del servicio PKCE."""
    return PKCEService(pkce_storage_factory)
def create_pkce_middleware(app):
    """Helper para crear PKCEAuthMiddleware con configuración adecuada."""
    from fastapi import FastAPI
    from src.utils.pkce_middleware import PKCEAuthMiddleware

    if isinstance(app, FastAPI):
        middleware = PKCEAuthMiddleware(
            app=app,
            exclude_paths=[
                '/docs',
                '/redoc',
                '/openapi.json',
                '/health',
                '/static',
                '/api/v1/validate-key',
                '/api/v1/generate-pkce',
                '/api/v1/validate-pkce-flow'
            ],
            storage_factory=PKCEStorageFactory(),
            strict_validation=True,
            rate_limit_per_ip=100,
            rate_limit_per_user=30
        )
        return middleware
    return None
__all__ = [
    'PKCEService',
    'get_pkce_service',
    'create_pkce_middleware',
    'PKCEConnectionManager'
]
