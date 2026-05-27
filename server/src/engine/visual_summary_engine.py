import json
import logging
import re
from typing import Optional, Dict, Any
from google.genai import types
from .bi_analyst import get_client, MODELS, generate_ai_content

logger = logging.getLogger(__name__)

# Tipos visuales válidos
VALID_VISUAL_TYPES = {"flowchart", "mindmap", "timeline", "comparison", "architecture"}

# Prompt base sugerido para Napkin AI
VISUAL_SUMMARY_PROMPT_TEMPLATE = """Eres un generador de resúmenes visuales estilo Napkin AI.
Tu tarea es analizar el contenido proporcionado y convertirlo en una estructura visual clara.
Debes responder únicamente con JSON válido.
No agregues explicaciones fuera del JSON.
No uses Markdown fuera del campo mermaid.
El campo mermaid debe contener código Mermaid válido y renderizable.
Selecciona el tipo visual más adecuado según el contenido o usa la sugerencia del usuario.

Sugerencia del usuario para el tipo visual (si es provista, priorízala): {suggested_type}

Guía de tipos visuales a seleccionar si no hay sugerencia:
- Si el contenido describe pasos, procesos, flujos de trabajo o decisiones, usa "flowchart".
- Si describe conceptos relacionados, jerarquías de ideas o lluvia de ideas, usa "mindmap".
- Si describe eventos secuenciales ordenados con fechas o hitos en el tiempo, usa "timeline".
- Si compara elementos, pros y contras, ventajas y desventajas o características paralelas, usa "comparison".
- Si describe componentes técnicos, arquitectura de sistemas, flujos de datos de red o infraestructura, usa "architecture".

Contenido a resumir:
{inputText}

Devuelve exactamente esta estructura JSON:
{{
  "title": "Un título corto y directo para la visualización",
  "summary": ["Idea general de resumen 1", "Idea general de resumen 2"],
  "key_points": ["Punto clave 1", "Punto clave 2", "Punto clave 3"],
  "visual_type": "flowchart | mindmap | timeline | comparison | architecture",
  "mermaid": "Código Mermaid válido y autoconstruido que represente el contenido",
  "confidence": "low | medium | high"
}}
"""

def validate_visual_summary_response(data: Any) -> Dict[str, Any]:
    """
    Valida rigurosamente que el diccionario de respuesta del LLM cumpla con la estructura definida.
    Lanza un ValueError si los datos son inválidos.
    """
    if not isinstance(data, dict):
        raise ValueError("La respuesta de la IA no es un objeto JSON (dict).")
    
    # 1. Validar title
    if "title" not in data or not isinstance(data["title"], str) or not data["title"].strip():
        raise ValueError("El campo 'title' es requerido y debe ser un texto no vacío.")
    
    # 2. Validar summary
    if "summary" not in data or not isinstance(data["summary"], list):
        raise ValueError("El campo 'summary' es requerido y debe ser una lista de ideas.")
    if not all(isinstance(x, str) for x in data["summary"]):
        raise ValueError("Todos los elementos de 'summary' deben ser textos.")
        
    # 3. Validar key_points
    if "key_points" not in data or not isinstance(data["key_points"], list):
        raise ValueError("El campo 'key_points' es requerido y debe ser una lista de puntos clave.")
    if not all(isinstance(x, str) for x in data["key_points"]):
        raise ValueError("Todos los elementos de 'key_points' deben ser textos.")
        
    # 4. Validar visual_type
    visual_type = data.get("visual_type", "").lower().strip()
    if visual_type not in VALID_VISUAL_TYPES:
        raise ValueError(f"El campo 'visual_type' ('{visual_type}') debe ser uno de los permitidos: {list(VALID_VISUAL_TYPES)}.")
    data["visual_type"] = visual_type
    
    # 5. Validar mermaid
    mermaid = data.get("mermaid", "")
    if not isinstance(mermaid, str) or not mermaid.strip():
        raise ValueError("El campo 'mermaid' es requerido y no puede estar vacío.")
    
    # 6. Validar confidence
    confidence = data.get("confidence", "").lower().strip()
    if confidence not in {"low", "medium", "high"}:
        data["confidence"] = "medium"  # Fallback seguro
    else:
        data["confidence"] = confidence
        
    return data

def _generate_quick_mode(
    text: str,
    provider: str,
    api_key: str,
    mistral_key: Optional[str] = None,
    visual_type: Optional[str] = None
) -> Dict[str, Any]:
    """Genera el resumen visual en una sola petición al LLM."""
    suggested_type = visual_type if visual_type in VALID_VISUAL_TYPES else "Auto-detectar"
    prompt = VISUAL_SUMMARY_PROMPT_TEMPLATE.format(
        suggested_type=suggested_type,
        inputText=text
    )
    
    resp_text = ""
    if provider == "gemini":
        client = get_client(api_key)
        # Usamos response_mime_type para garantizar JSON
        response = client.models.generate_content(
            model=MODELS["GEMINI_ANALYTICS"],
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.4, # Menor temperatura para evitar alucinaciones en Mermaid
                response_mime_type="application/json"
            )
        )
        resp_text = response.text
    else:
        # Mistral u otros: usamos la llamada estándar y limpiamos Markdown
        key = mistral_key if provider == "mistral" else api_key
        resp_text = generate_ai_content(prompt, key, provider, temperature=0.3, model_level="ANALYTICS")
        
    if not resp_text:
        raise ValueError("No se recibió respuesta del modelo de lenguaje.")
        
    # Limpieza de Markdown si existe
    clean_resp = resp_text.strip()
    if "```json" in clean_resp:
        match = re.search(r"```json\s*(.*?)\s*```", clean_resp, re.DOTALL)
        if match:
            clean_resp = match.group(1)
    elif "```" in clean_resp:
        match = re.search(r"```\s*(.*?)\s*```", clean_resp, re.DOTALL)
        if match:
            clean_resp = match.group(1)
            
    try:
        data = json.loads(clean_resp)
    except Exception as e:
        logger.error(f"Error parseando JSON del LLM para Visual Summary. Raw response: {resp_text}")
        raise ValueError(f"La respuesta de la IA no pudo parsearse como JSON: {str(e)}")
        
    return validate_visual_summary_response(data)

def _generate_quality_mode(
    text: str,
    provider: str,
    api_key: str,
    mistral_key: Optional[str] = None,
    visual_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Modo Calidad estructurado. En esta primera fase, realiza un fallback al modo rápido
    pero loguea el inicio de la arquitectura secuencial planificada.
    """
    logger.info("[Modo Calidad] Iniciando pipeline de 3 pasos (Esqueleto). Ejecutando fallback optimizado al modo rápido en Fase 1.")
    
    # Aquí iría en el futuro la ejecución secuencial:
    # 1. Petición 1: Análisis semántico del contenido -> _quality_semantic_analysis(...)
    # 2. Petición 2: Generación del mapeo estructural visual -> _quality_visual_mapping(...)
    # 3. Petición 3: Generación, validación y autoreparación de Mermaid -> _quality_mermaid_generator(...)
    
    # Para Fase 1, ejecutamos el modo rápido con temperatura un poco más controlada
    return _generate_quick_mode(text, provider, api_key, mistral_key, visual_type)

def generate_visual_summary(
    text: str,
    provider: str,
    api_key: str,
    mistral_key: Optional[str] = None,
    visual_type: Optional[str] = None,
    mode: str = "rapido"
) -> Dict[str, Any]:
    """
    Función principal de entrada del motor de resúmenes visuales.
    Permite generar resúmenes con validación y manejo de modos (rápido y calidad).
    """
    if not text or not text.strip():
        raise ValueError("El texto de entrada está vacío.")
        
    if mode == "calidad":
        return _generate_quality_mode(text, provider, api_key, mistral_key, visual_type)
    else:
        return _generate_quick_mode(text, provider, api_key, mistral_key, visual_type)
