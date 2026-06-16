import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def find_project_root() -> Path:
    """Busca la raíz del proyecto subiendo directorios hasta encontrar .codex o AGENTS.md."""
    current = Path(__file__).resolve().parent
    for _ in range(6):
        if (current / ".codex").exists() or (current / "AGENTS.md").exists():
            return current
        current = current.parent
    # Fallback si no lo encuentra por estructura
    return Path(__file__).resolve().parent.parent.parent.parent

PROJECT_ROOT = find_project_root()
SKILLS_DIR = PROJECT_ROOT / ".codex" / "skills"

# Mapeo de habilidades recomendadas para cada rol de agente analítico
AGENT_SKILLS_MAP = {
    "PLANNER": [
        "agent-stability-and-guidance-control",
        "user-interaction-protocol"
    ],
    "EXECUTOR": [
        "agent-stability-and-guidance-control",
        "vektra-product-design",
        "universal-premium-web-design"
    ],
    "VALIDATOR": [
        "agent-stability-and-guidance-control",
        "vektra-code-verification"
    ],
    "STRATEGIST": [
        "agent-stability-and-guidance-control",
        "vektra-data-semantics"
    ]
}

def clean_frontmatter(content: str) -> str:
    """Elimina el frontmatter YAML delimitado por --- al inicio del archivo markdown."""
    content_stripped = content.strip()
    if content_stripped.startswith("---"):
        parts = content_stripped.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return content_stripped

def load_system_rules() -> str:
    """
    Carga las reglas críticas del sistema desde AI_RULES.md y las directrices
    generales desde AGENTS.md si están disponibles.
    """
    rules_text = []
    
    # 1. Cargar AI_RULES.md
    ai_rules_path = PROJECT_ROOT / "AI_RULES.md"
    if ai_rules_path.exists():
        try:
            with open(ai_rules_path, "r", encoding="utf-8") as f:
                rules_text.append("=== REGLAS TÉCNICAS E INQUEBRANTABLES DEL PROYECTO ===\n")
                rules_text.append(f.read().strip())
        except Exception as e:
            logger.warning("No se pudo leer AI_RULES.md: %s", e)
            
    # 2. Cargar AGENTS.md
    agents_path = PROJECT_ROOT / "AGENTS.md"
    if agents_path.exists():
        try:
            with open(agents_path, "r", encoding="utf-8") as f:
                rules_text.append("\n=== DIRECTRICES GENERALES DE AGENTES ===\n")
                rules_text.append(f.read().strip())
        except Exception as e:
            logger.warning("No se pudo leer AGENTS.md: %s", e)
            
    return "\n".join(rules_text)

def load_skills(skill_names: list[str]) -> str:
    """
    Carga el archivo SKILL.md de cada una de las skills especificadas en skill_names.
    Limpia el frontmatter de metadatos para optimizar el prompt.
    """
    skills_text = []
    
    for skill_name in skill_names:
        skill_file = SKILLS_DIR / skill_name / "SKILL.md"
        if skill_file.exists():
            try:
                with open(skill_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    clean_content = clean_frontmatter(content)
                    skills_text.append(f"--- INICIO HABILIDAD: {skill_name.upper()} ---")
                    skills_text.append(clean_content)
                    skills_text.append(f"--- FIN HABILIDAD: {skill_name.upper()} ---\n")
            except Exception as e:
                logger.warning("Error al cargar la skill '%s': %s", skill_name, e)
        else:
            logger.info("La skill '%s' no se encontró en la ruta %s", skill_name, skill_file)
            
    return "\n".join(skills_text)

def get_system_prompt_for_agent(agent_role: str) -> str:
    """
    Retorna el prompt de sistema (System Instruction) consolidado para un agente
    según su rol (PLANNER, EXECUTOR, VALIDATOR, STRATEGIST, o un rol genérico).
    """
    role_upper = agent_role.upper()
    
    # 1. Cargar reglas globales del sistema
    system_rules = load_system_rules()
    
    # 2. Cargar skills asignadas al rol (o por defecto si el rol no está mapeado)
    assigned_skills = AGENT_SKILLS_MAP.get(role_upper, ["agent-stability-and-guidance-control"])
    skills_content = load_skills(assigned_skills)
    
    # 3. Consolidar prompt de sistema
    prompt_parts = []
    
    prompt_parts.append(f"Rol del Agente de IA: {role_upper}")
    prompt_parts.append("Eres un componente especializado del sistema Agente-BI. Debes seguir de forma estricta las siguientes directrices y reglas del proyecto en cada una de tus respuestas.")
    
    if system_rules:
        prompt_parts.append("\n=== REGLAS GLOBALES Y DE SEGURIDAD ===")
        prompt_parts.append(system_rules)
        
    if skills_content:
        prompt_parts.append("\n=== HABILIDADES Y DIRECTRICES TÉCNICAS APLICABLES ===")
        prompt_parts.append(skills_content)
        
    prompt_parts.append("\n=== INSTRUCCIONES OPERATIVAS ===")
    prompt_parts.append("1. Ejecuta únicamente tu función asignada.")
    prompt_parts.append("2. Aplica las directrices de diseño, tipado y seguridad detalladas en las habilidades superiores de forma rigurosa.")
    prompt_parts.append("3. No inventes APIs, datos ni variables fuera de las suministradas.")
    
    return "\n".join(prompt_parts)
