"""
Módulo de Hardening de Seguridad Específica Móvil y Cliente
Implementa las políticas de seguridad específicas para clientes móviles y web desde .codex/skills/vektra-security-review/SKILL.md
"""

import re
import os
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException
import hashlib
import secrets

# Configuración de seguridad móvil
MOBILE_USER_AGENT_PATTERNS = [
    r'Mozilla/5\.0.*Mobile',
    r'Mozilla/5\.0.*Android',
    r'Mozilla/5\.0.*iPhone',
    r'Mozilla/5\.0.*iPad',
    r'CrOS.*Mobi',
    r'Opera.*Mobile',
]

# Orígenes permitidos por app
ALLOWED_ORIGINS_BY_APP = {
    "mobile": [
        "https://app.vektra-bi.com",
        "https://app.staging.vektra-bi.com"
    ],
    "web": [
        "https://agente-bi.vercel.app",
        "https://app.vektra-bi.com"
    ]
}

class MobileSecurity:
    """Hardening de seguridad específico para clientes móviles."""
    
    @staticmethod
    def detect_request_source(request: Request) -> str:
        """Detecta si una request viene de móvil, web, o desconocido."""
        user_agent = request.headers.get('User-Agent', '').lower()
        
        # Detectar dispositivos móviles
        for pattern in MOBILE_USER_AGENT_PATTERNS:
            if re.search(pattern, user_agent, re.IGNORECASE):
                return 'mobile'
        
        # Detectar clientes web normales
        if not any(term in user_agent for term in ['spider', 'bot', 'curl', 'postman']):
            return 'web'
        
        return 'unknown'
    
    @staticmethod
    def verify_client_app(request: Request, expected_source: str = 'mobile') -> bool:
        """Verifica que el cliente pertenece a una app móvil/autorizada."""
        source = MobileSecurity.detect_request_source(request)
        
        # Si esperamos móvil y el source coincide
        if expected_source == 'mobile' and source == 'mobile':
            return True
            
        # Si esperamos web y el source coincide  
        if expected_source == 'web' and source in ['web', 'unknown']:
            return True
            
        return False
    
    @staticmethod
    def sanitize_input_data(input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanea y normaliza datos de entrada para seguridad móvil."""
        sanitized = {}
        
        for key, value in input_data.items():
            if isinstance(value, str):
                # Remover posibles scripts/malware
                value = re.sub(r'<script.*?</script>', '', value, flags=re.IGNORECASE)
                value = re.sub(r'javascript:', '', value, flags=re.IGNORECASE)
                value = re.sub(r'on\w+\s*=', '', value, flags=re.IGNORECASE)
                
                # Limitar longitud para prevenir overflow
                if len(value) > 10000:
                    value = value[:10000] + '...'
                    
            sanitized[key] = value
            
        return sanitized
    
    @staticmethod
    def generate_secure_session_id() -> str:
        """Genera un ID de sesión seguro para dispositivos móviles."""
        return secrets.token_urlsafe(32)
class PKCEManager:
    """Manejo de PKCE (Proof Key for Code Exchange) para OAuth2 móvil seguro."""
    
    def __init__(self):
        self.code_verifier_length = 64
        self.code_verifier_expiry = timedelta(minutes=10)
    
    def generate_pkce_pair(self) -> tuple[str, str]:
        """Genera un par PKCE seguro (verifier + challenge)."""
        # Generar code_verifier seguro
        code_verifier = self._generate_code_verifier()
        
        # Derivar challenge usando SHA256
        code_challenge = self._derive_code_challenge(code_verifier)
        
        return code_verifier, code_challenge
    
    def _generate_code_verifier(self) -> str:
        """Genera un code_verifier seguro usando caracteres URL-safe."""
        alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~'
        return ''.join(secrets.choice(alphabet) for _ in range(self.code_verifier_length))
    
    def _derive_code_challenge(self, code_verifier: str) -> str:
        """Deriva un code_challenge usando SHA256 y base64 URL-safe sin padding."""
        sha256 = hashlib.sha256(code_verifier.encode('utf-8'))
        challenge = base64.urlsafe_b64encode(sha256.digest()).decode('utf-8').replace('=', '')
        return challenge
    
    def validate_code_verifier(self, stored_verifier: str, provided_verifier: str) -> bool:
        """Valida un code_verifier provisto contra el almacenado."""
        if not stored_verifier or not provided_verifier:
            return False
            
        # Usar comparación constante-time para prevenir timing attacks
        return secrets.compare_digest(stored_verifier, provided_verifier)
class OAuth2SecurityMiddleware:
    """Middleware de seguridad OAuth2 con PKCE para clientes móviles y web."""
    
    def __init__(self, pkce_manager: Optional[PKCEManager] = None):
        self.pkce_manager = pkce_manager or PKCEManager()
        self.auth_codes = {}  # En producción usar Redis/DB
    
    def store_auth_code_with_pkce(self, auth_code: str, code_verifier: str) -> bool:
        """Almacena un código de autorización con su code_verifier asociado."""
        try:
            self.auth_codes[auth_code] = {
                'code_verifier': code_verifier,
                'created_at': datetime.utcnow(),
                'used': False
            }
            return True
        except Exception:
            return False
    
    def validate_authorization_code_with_pkce(self, auth_code: str, code_verifier: str) -> bool:
        """Valida un código de autorización con su code_verifier usando PKCE."""
        if not auth_code or not code_verifier:
            return False
            
        auth_data = self.auth_codes.get(auth_code)
        if not auth_data or auth_data.get('used', False):
            return False
            
        # Validar code_verifier usando PKCE
        if not self.pkce_manager.validate_code_verifier(
            auth_data['code_verifier'], code_verifier
        ):
            return False
            
        # Marcar como usado
        auth_data['used'] = True
        return True
    
    def cleanup_expired_codes(self) -> int:
        """Limpia códigos de autorización expirados."""
        expired_codes = []
        for auth_code, data in self.auth_codes.items():
            if datetime.utcnow() > data['created_at'] + self.pkce_manager.code_verifier_expiry:
                expired_codes.append(auth_code)
        
        for code in expired_codes:
            del self.auth_codes[code]
            
        return len(expired_codes)
# Instancia global del manejador de seguridad OAuth2
_oauth2_security = OAuth2SecurityMiddleware()
def validate_mobile_request_security(request: Request, expected_client_type: str = 'mobile') -> Dict[str, Any]:
    """
    Middleware de seguridad validado para requests móviles.
    Implementa verificaciones de seguridad desde vektra-security-review SKILL.
    """
    result = {
        'valid': True,
        'message': 'Security check passed',
        'client_type': MobileSecurity.detect_request_source(request),
        'security_score': 100,
        'recommendations': []
    }
    
    # Verificar que el cliente es el esperado
    if expected_client_type not in ['mobile', 'web']:
        result['valid'] = False
        result['message'] = 'Invalid client type expected'
        return result
        
    if not MobileSecurity.verify_client_app(request, expected_client_type):
        result['valid'] = False
        result['message'] = 'Client application not authorized'
        result['security_score'] -= 50
        result['recommendations'].append('Verify client certificates and certificate pinning')
        return result
    
    # Sanitizar headers requests
    user_agent = request.headers.get('User-Agent', '')
    if len(user_agent) < 10:
        result['valid'] = False
        result['message'] = 'User-Agent header missing or malformed'
        result['security_score'] -= 30
    
    # Verificar autenticación de dispositivos específicos si es móvil
    if expected_client_type == 'mobile':
        # En producción, verificar certificado/device fingerprint
        if 'X-Mobile-Device-ID' not in request.headers:
            result['recommendations'].append('Implement device certificate verification for mobile clients')
        if 'X-App-Version' not in request.headers:
            result['recommendations'].append('Implement app version validation for mobile clients')
    
    # Verificar User-Agent no malicioso
    malicious_patterns = [
        r'sqlmap',
        r'nmap',
        r'nessus',
        r'exploit',
        r'curl/.*-d',
        r'postman'
    ]
    
    for pattern in malicious_patterns:
        if re.search(pattern, user_agent, re.IGNORECASE):
            result['valid'] = False
            result['message'] = 'Malicious client detected'
            result['security_score'] -= 80
            result['recommendations'].append('Implement WAF and IP blocking for malicious clients')
            break
    
    return result
# Exportar componentes clave
__all__ = [
    'MobileSecurity',
    'PKCEManager', 
    'OAuth2SecurityMiddleware',
    'validate_mobile_request_security',
    'generate_code_verifier',
    'derive_code_challenge'
]
