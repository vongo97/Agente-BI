"""
Password Strength Validation Module
Módulo para validación y fortalecimiento de contraseñas en todo el sistema.
Permite verificar poligráfos de contraseñas, detección de patrones débiles,
valores mínimos específicos para cada proveedor, historial de uso y sugerencias
para prevenir forzamiento de credenciales.
"""

import json
import hashlib
import secrets
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from src.utils.logging_config import setup_logging

logger = setup_logging(__name__)
class PasswordPolicy:
    """
    Política de contraseñas aplicable a cada proveedor.
    
    Define longitud mínima, requisitos de carácter, y restricciones específicas.
    """

    PROVIDER_GITHUB = "github"
    PROVIDER_GITLAB = "gitlab"
    PROVIDER_BITBUCKET = "bitbucket"
    PROVIDER_GITEE = "gitlab-enterprise"
    PROVIDER_GOOGLE = "google"
    PROVIDER_AZURE = "azure"
    PROVIDER_AWS = "aws"
    PROVIDER_MICROSOFT = "microsoft"
    PROVIDER_JAZZIAM = "jazziam"
    PROVIDER_OKTA = "okta"
    PROVIDER_AUTH0 = "auth0"
    PROVIDER_KEYCLOAK = "keycloak"
    PROVIDER_AD = "active-directory"
    PROVIDER_LDAP = "ldap"
    PROVIDER_SAML = "saml"
    PROVIDER_OAUTH2 = "oauth2"

    DEFAULT_POLICY = {
        # Longitudes mínimas por proveedor
        "min_length": {
            PROVIDER_GITHUB: 8,
            PROVIDER_GITLAB: 8,
            PROVIDER_BITBUCKET: 8,
            PROVIDER_GITEE: 8,
            PROVIDER_GOOGLE: 12,
            PROVIDER_AZURE: 12,
            PROVIDER_AWS: 8,
            PROVIDER_MICROSOFT: 12,
            PROVIDER_JAZZIAM: 10,
            PROVIDER_OKTA: 8,
            PROVIDER_AUTH0: 8,
            PROVIDER_KEYCLOAK: 8,
            PROVIDER_AD: 8,
            PROVIDER_LDAP: 8,
            PROVIDER_SAML: 8,
            PROVIDER_OAUTH2: 8
        },
        # Mínimo número de tipos de caracteres requeridos
        "min_char_types": 3,
        # Patrones de contraseña prohibidos
        "ban_patterns": [
            r'(.)\\1{3,}',  # 3+ chars repetidos
            r'12345',
            r'password',
            r'123456',
            r'qwerty',
            r'admin',
            r'user',
            r'test',
            r'demo',
            r'guest',
            r'host',
            r'root',
        ],
        # Tipos de caracteres requeridos (mínimo)
        "required_char_types": [
            string.ascii_lowercase,
            string.ascii_uppercase,
            string.digits,
            string.punctuation
        ],
        # Máximo score histórico permitido para evitar repeticiones
        "max_history_score": 80,
        # Score para contraseñas comunes
        "common_password_score": 90,
        # Permitir espacios en las contraseñas
        "allow_spaces": False,
        # Modo de producción (stricto)
        "production_mode": True
    }

    @classmethod
    def generate_password(cls, policy: dict, length: int = None) -> Dict[str, Any]:
        """
        Genera una contraseña aleatoria que cumple con la política dada.

        Args:
            policy: Política de contraseñas
            length: Longitud deseada (si no se especifica, se usa la mínima)

        Returns:
            Dict con la contraseña generada y su fuerza
        """
        try:
            min_len = policy["min_length"].get("default", policy.get("min_length", 8))

            target_len = length if length else min_len

            chars = policy["required_char_types"][0]
            for c in range(1, len(policy["required_char_types"])):
                chars += policy["required_char_types"][c]

            password = ""
            while True:
                password = ''.join(secrets.choice(chars) for _ in range(target_len))

                if policy.get("allow_spaces", False):
                    password = password.replace(" ", "")

                errors = cls._validate_password(password, policy)
                if not errors:
                    break

            strength = cls._calculate_password_strength(password, policy)
            return {"password": password, "strength": strength, "policy": policy}

        except Exception as e:
            logger.error(f"Error generando contraseña: {e}")
            return {"error": f"Error generando contraseña: {str(e)}"}

    @classmethod
    def _validate_password(cls, password: str, policy: dict) -> List[str]:
        """
        Valida una contraseña contra la política dada.

        Args:
            password: La contraseña a validar
            policy: La política de contraseñas

        Returns:
            Lista de errores, vacía si la contraseña es válida
        """
        errors = []

        # Validar longitud
        min_length = policy["min_length"].get("default", policy.get("min_length", 8))
        if len(password) < min_length:
            errors.append(f"La longitud debe ser al menos {min_length} caracteres")

        # Validar tipos de caracteres
        char_types = 0
        for char_type in policy["required_char_types"]:
            if any(c in password for c in char_type):
                char_types += 1

        if char_types < policy.get("min_char_types", 3):
            errors.append(f"Debe contener al menos {policy.get('min_char_types', 3)} tipos de caracteres")

        # Validar patrones
        for pattern in policy.get("ban_patterns", []):
            if re.search(pattern, password, re.IGNORECASE):
                errors.append(f"Contiene un patrón no permitido: {pattern}")

        # Validar si es un password común
        if len(password) <= 20:
            normalized = password.lower()
            if normalized in ["password", "123456", "admin", "user", "test"]:
                errors.append("No puede ser un password común")

        return errors

    @classmethod
    def _calculate_password_strength(cls, password: str, policy: dict) -> Dict[str, Any]:
        """
        Calcula el nivel de seguridad de una contraseña.

        Args:
            password: La contraseña a evaluar

        Returns:
            Dict con puntuación y recomendaciones
        """
        score = 0
        max_score = 100
        checks = []

        # Longitud (0-40 puntos)
        length = len(password)
        if length >= 16:
            score += 40
        elif length >= 12:
            score += 30
        elif length >= 8:
            score += 15
        else:
            score += 0

        # Diversidad de caracteres (0-30 puntos)
        char_types = 0
        for char_type in policy["required_char_types"]:
            if any(c in password for c in char_type):
                char_types += 1

        if char_types == 2:
            score += 15
        elif char_types == 3:
            score += 25
        elif char_types == 4:
            score += 30

        # Número de substrings únicas (0-15 puntos)
        unique_substrings = len(set(password))
        if unique_substrings >= 8:
            score += 15

        # Aleatoriedad (0-15 puntos)
        import math
        entropy = len(password) * math.log2(len(set(password)))
        entropy_percent = min(100, int(entropy / 5))
        score += entropy_percent

        # Longitud vs complejidad (0-10 puntos)
        if length >= policy.get("min_length", 8) + 4:
            score += 10

        recommendations = []
        if score < 50:
            recommendations.append("Muy débil - considere usar una contraseña más larga y compleja")
        elif score < 70:
            recommendations.append("Moderadamente débil - añada más tipos de caracteres")
        elif score < 85:
            recommendations.append("Aceptable - podría ser mejorada")
        else:
            recommendations.append("Segura - buena contraseña")

        return {"score": score, "max_score": max_score, "percentage": min(100, (score / max_score) * 100), "recommendations": recommendations}
class PasswordHistory:
    """
    Maneja el historial y control de repeticiones de contraseñas.

    Almacena hashes de contraseñas anteriores para prevenir el re-uso.
    """

    def __init__(self, storage_path: str = "password_history.json"):
        self.storage_path = storage_path
        self.history = self._load_history()

    def _load_history(self) -> Dict[str, Any]:
        try:
            with open(self.storage_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"hashes": {}, "last_cleanup": datetime.now().isoformat()}

    def _save_history(self):
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            logger.error(f"Error guardando historial de contraseñas: {e}")

    def is_password_used(self, password: str, max_age_hours: int = 72) -> bool:
        """
        Verifica si una contraseña ya fue usada en el historial reciente.

        Args:
            password: La contraseña a verificar
            max_age_hours: Maximum de horas que la contraseña puede permanecer en el historial

        Returns:
            True si la contraseña está en el historial dentro del período
        """
        password_hash = self._hash_password(password)
        current_time = datetime.now()

        for hash_entry in self.history["hashes"].values():
            if hash_entry["hash"] == password_hash:
                if "expires_at" in hash_entry:
                    expires_at = datetime.fromisoformat(hash_entry["expires_at"])
                    if expires_at > current_time:
                        return True
                break

        return False

    def add_password(self, password: str, expires_hours: int = 72):
        """
        Agrega una contraseña al historial (hash).

        Args:
            password: La contraseña a agregar
            expires_hours: Horas hasta su expiración
        """
        password_hash = self._hash_password(password)
        expires_at = datetime.now() + timedelta(hours=expires_hours)

        self.history["hashes"][password_hash] = {
            "hash": password_hash,
            "created_at": datetime.now().isoformat(),
            "expires_at": expires_at.isoformat(),
            "provider": None  # Se puede agregar más tarde
        }

        self._save_history()
        self._cleanup_expired_entries()

    def _hash_password(self, password: str) -> str:
        """Genera un hash seguro de la contraseña."""
        salt = os.urandom(32)
        iterations = 100000

        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            iterations
        )

        return hashlib.sha256(salt + key).hexdigest()

    def _cleanup_expired_entries(self):
        """Limpia entradas expiradas del historial."""
        current_time = datetime.now()
        expired_keys = []

        for key, entry in self.history["hashes"].items():
            if "expires_at" in entry:
                expires_at = datetime.fromisoformat(entry["expires_at"])
                if expires_at < current_time:
                    expired_keys.append(key)

        for key in expired_keys:
            del self.history["hashes"][key]

        if expired_keys:
            logger.debug(f"Limpiadas {len(expired_keys)} entradas de contraseñas expiradas")

        self._save_history()

    def get_used_passwords_for_user(self, user_id: str) -> List[str]:
        """
        Obtiene contraseñas usadas por usuario específico.

        Args:
            user_id: ID del usuario

        Returns:
            Lista de contraseñas hash usadas por este usuario
        """
        used_passwords = []
        for hash_entry in self.history["hashes"].values():
            if hash_entry.get("user_id") == user_id:
                used_passwords.append(hash_entry["hash"])

        return used_passwords
class PasswordPolicyEnforcer:
    """
    Aplica políticas de contraseñas en todo el sistema y maneja la validación.
    """

    def __init__(self, policy_file: str = "password_policy.json"):
        self.policies = self._load_policies(policy_file)
        self.history = PasswordHistory()

    def _load_policies(self, policy_file: str) -> Dict[str, Any]:
        """Carga las políticas de contraseñas desde un archivo."""
        try:
            with open(policy_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return PasswordPolicy.DEFAULT_POLICY

    def validate_password_for_provider(
        self,
        password: str,
        provider: str = PasswordPolicy.PROVIDER_GITHUB,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Valida una contraseña contra la política del proveedor y el historial.

        Args:
            password: La contraseña a validar
            provider: Proveedor (GitHub, GitLab, etc.)
            user_id: ID de usuario opcional (para historial)

        Returns:
            Dict con resultados de validación, puntuación y recomendaciones
        """
        # Obtener política para el proveedor
        provider_policy = self.policies.get("providers", {}).get(provider, self.policies)

        # Si el usuario está autenticado, verificar si la contraseña está en su historial
        if user_id and self.history.is_password_used(password):
            return {
                "valid": False,
                "message": "La contraseña no puede ser una password usada anteriormente",
                "error_code": "PASSWORD_IN_HISTORY",
                "score": 0,
                "recommendations": ["Use una contraseña diferente de anteriores"]
            }

        # Validar contra la política
        validation_errors = PasswordPolicy._validate_password(password, provider_policy)

        if validation_errors:
            return {
                "valid": False,
                "message": "La contraseña no cumple con los requisitos",
                "errors": validation_errors,
                "error_code": "POLICY_VIOLATION",
                "score": 0,
                "recommendations": self._generate_recommendations(password, provider_policy)
            }

        # Calcular puntuación de seguridad
        security_score = PasswordPolicy._calculate_password_strength(password, provider_policy)

        return {
            "valid": True,
            "message": "La contraseña cumple con los requisitos de seguridad",
            "score": security_score,
            "provider": provider,
            "recommendations": self._generate_recommendations(password, provider_policy)
        }

    def generate_secure_password(
        self,
        provider: str = PasswordPolicy.PROVIDER_GITHUB,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Genera una contraseña segura que cumple con los requisitos del proveedor.

        Args:
            provider: Proveedor (GitHub, GitLab, etc.)
            user_id: ID de usuario opcional (para registrar en historial)

        Returns:
            Dict con contraseña generada y metadata
        """
        # Obtener política para el proveedor
        provider_policy = self.policies.get("providers", {}).get(provider, self.policies)

        # Generar contraseña segura
        password_data = PasswordPolicy.generate_password(provider_policy)

        if "error" in password_data:
            return password_data

        password = password_data["password"]
        strength = password_data["strength"]

        # Registrar en historial si se proporciona user_id
        if user_id:
            self.history.add_password(password)

        return {
            "password": password,
            "score": strength["score"],
            "percentage": strength["percentage"],
            "recommendations": strength["recommendations"],
            "provider": provider
        }

    def enforce_policy_on_form(
        self,
        password_field: str,
        confirm_password_field: str,
        user_id: Optional[str] = None,
        provider: str = PasswordPolicy.PROVIDER_GITHUB
    ) -> Dict[str, Any]:
        """
        Valida dos campos de contraseña (password y confirm password) en un formulario.

        Args:
            password_field: Contraseña ingresada por el usuario
            confirm_password_field: Confirmación de contraseña ingresada por el usuario
            user_id: ID de usuario opcional
            provider: Proveedor para políticas específicas

        Returns:
            Dict con resultado de validación y mensajes de error
        """
        errors = []

        # Validar que las contraseñas coincidan
        if password_field != confirm_password_field:
            errors.append("Las contraseñas no coinciden")

        # Validar password
        password_validation = self.validate_password_for_provider(password_field, provider, user_id)
        if not password_validation["valid"]:
            errors.extend(password_validation["errors"])
            password_validation["message"] = f"Password no válido: {'; '.join(password_validation.get('errors', ['Error desconocido']))}"

        if errors:
            return {
                "valid": False,
                "message": "; ".join(errors),
                "error_code": "VALIDATION_FAILED"
            }

        return {
            "valid": True,
            "message": "La contraseña cumple con todos los requisitos",
            "password_data": {
                "password": password_field,
                "score": password_validation["score"],
                "provider": provider
            }
        }

    def _generate_recommendations(self, password: str, policy: dict) -> List[str]:
        recommendations = []

        # Verificar longitud
        min_length = policy.get("min_length", {"default": 8})
        if "default" in min_length:
            min_len = min_length["default"]
        else:
            min_len = min_length.get(PasswordPolicy.PROVIDER_GITHUB, 8)

        if len(password) < min_len:
            recommendations.append(f"Use al menos {min_len} caracteres")

        # Verificar tipos de caracteres
        char_types = 0
        for char_type in policy.get("required_char_types", []):
            if any(c in password for c in char_type):
                char_types += 1

        if char_types < 3:
            recommendations.append("Incluye letras mayúsculas, minúsculas, números y símbolos")

        # Verificar patrones
        banned_patterns = policy.get("ban_patterns", [])
        for pattern in banned_patterns:
            if re.search(pattern, password, re.IGNORECASE):
                recommendations.append(f"Evite incluir patrones como '12345' o 'password'")
                break

        return recommendations
class PasswordPolicyViolationNotification:
    """
    Notificación para violaciones de políticas de contraseñas.
    Envía alertas cuando una contraseña no cumple con la política.
    """

    def __init__(self, notification_channel: str = "email"):
        self.channel = notification_channel
        self.log_file = "password_policy_notifications.log"

    def notify_violation(
        self,
        user_id: str,
        password: str,
        violations: List[str],
        severity: str = "warning"
    ):
        """
        Notifica una violación de política de contraseña.

        Args:
            user_id: ID del usuario
            password: La contraseña que falló
            violations: Lista de violaciones
            severity: Nivel de severidad (warning, error, critical)
        """
        message = f"Violación de política de contraseña para usuario {user_id}:\n"
        message += f"Contraseña: {password[:4]}****{password[-4:] if len(password) > 8 else ''}\n"
        message += f"Violaciones: {'; '.join(violations)}\n"
        message += f"Severidad: {severity}\n"
        message += f"Fecha: {datetime.now().isoformat()}\n"

        # Logear la notificación
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'severity': severity,
            'message': message,
            'password_hash': hashlib.sha256(password.encode()).hexdigest()
        }

        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')

            # Enviar por email si el canal es email
            if self.channel == 'email':
                self._send_email_notification(user_id, message)

            logger.info(f"Notificación de violación de contraseña enviada para usuario {user_id}")

        except Exception as e:
            logger.error(f"Error enviando notificación de violación de contraseña: {e}")

    def _send_email_notification(self, user_id: str, message: str):
        """Envía notificación por email (implementación placeholder)."""
        # Implementar envío de email real aquí
        logger.debug(f"Email notification would be sent to {user_id}: {message[:100]}...")

    def get_recent_violations(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Obtiene notificaciones de violaciones recientes.

        Args:
            hours: Número de horas hacia atrás a buscar

        Returns:
            Lista de notificaciones recientes
        """
        notifications = []
        cutoff_time = datetime.now() - timedelta(hours=hours)

        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line.strip())
                        entry_time = datetime.fromisoformat(log_entry['timestamp'])
                        if entry_time > cutoff_time:
                            notifications.append(log_entry)
                    except json.JSONDecodeError:
                        continue

        except FileNotFoundError:
            pass

        return notifications

    def cleanup_old_notifications(self, days: int = 30):
        """
        Elimina notificaciones más antiguas que el número especificado de días.

        Args:
            days: Número de días
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        cleaned_count = 0

        try:
            with open(self.log_file, 'r') as f:
                lines = f.readlines()

            filtered_lines = []
            for line in lines:
                try:
                    log_entry = json.loads(line.strip())
                    entry_time = datetime.fromisoformat(log_entry['timestamp'])
                    if entry_time > cutoff_time:
                        filtered_lines.append(line)
                    else:
                        cleaned_count += 1
                except json.JSONDecodeError:
                    filtered_lines.append(line)

            with open(self.log_file, 'w') as f:
                f.writelines(filtered_lines)

            if cleaned_count > 0:
                logger.debug(f"Eliminadas {cleaned_count} notificaciones antiguas")

        except FileNotFoundError:
            pass

__all__ = [
    'PasswordPolicy',
    'PasswordHistory',
    'PasswordPolicyEnforcer',
    'PasswordPolicyViolationNotification'
]
