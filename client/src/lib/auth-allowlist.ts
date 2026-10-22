/**
 * Utilidad de allowlist de emails autorizados (P-15).
 *
 * Lee la variable de entorno NEXT_PUBLIC_AUTHORIZED_EMAILS (lista separada por comas)
 * y permite comprobar si un email tiene acceso a la aplicación.
 *
 * Si la variable no está definida, se permite el acceso a cualquier email autenticado
 * (comportamiento anterior). Si está definida, solo los emails de la lista pueden entrar.
 */
const RAW = (process.env.NEXT_PUBLIC_AUTHORIZED_EMAILS || "").trim();

const AUTHORIZED_EMAILS = RAW
  ? new Set(
      RAW.split(",").map((e) => e.trim().toLowerCase()).filter(Boolean)
    )
  : null;

/**
 * Comprueba si un email está en la allowlist.
 * - Si no hay allowlist configurada (variable vacía), devuelve true (acceso abierto).
 * - Si hay allowlist, devuelve true solo si el email (case-insensitive) está incluido.
 */
export function isAuthorizedEmail(email: string | undefined | null): boolean {
  if (!email) return false;
  if (AUTHORIZED_EMAILS === null) return true;
  return AUTHORIZED_EMAILS.has(email.trim().toLowerCase());
}

/**
 * Devuelve la lista de emails autorizados (para mostrar en mensajes de error).
 */
export function getAuthorizedEmails(): string[] {
  if (AUTHORIZED_EMAILS === null) return [];
  return Array.from(AUTHORIZED_EMAILS);
}

/**
 * Indica si la allowlist está activa (variable configurada).
 */
export function hasAuthorizedEmailsConfigured(): boolean {
  return AUTHORIZED_EMAILS !== null;
}
