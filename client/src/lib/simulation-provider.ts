export function simulationKeyForProvider(
  provider: string,
  keys: { gemini: string; mistral: string; groq: string },
): string {
  if (provider === "gemini") return keys.gemini;
  if (provider === "mistral") return keys.mistral;
  if (provider === "groq") return keys.groq;
  // Otros proveedores se resuelven en el backend desde la configuración cifrada.
  return "";
}
