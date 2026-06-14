---
name: agent-stability-and-guidance-control
description: Directivas de comportamiento, alineación y control de ejecución para la IA (Antigravity). Úsalo para garantizar que el agente no se desvíe de las órdenes del usuario y siga las políticas de seguridad y dependencias.
---

# Agent Stability, Alignment & Guidance Control

Este documento contiene las reglas de estabilidad cognitiva que todo agente de IA (como Antigravity) debe aplicar de manera continua y rigurosa en su flujo de razonamiento y toma de decisiones.

---

## 1. Alineación Absoluta y No Desviación

* **Seguir Órdenes Explícitas:** El agente debe limitarse a resolver los requerimientos declarados por el usuario. No agregues "features" secundarias, lógicas "adicionales" o componentes extraños no especificados con la intención de "ayudar", ya que esto aumenta la superficie de error e introduce código basura.
* **Consulta de Ambigüedades:** Si un requerimiento está incompleto, es contradictorio o carece de especificaciones claras (por ejemplo, colores, flujos de navegación, modelo de base de datos), el agente **no debe asumir** la solución. Debe formular preguntas directas o redactar un plan con opciones claras para que el usuario tome la decisión.

---

## 2. Cumplimiento Estricto de Reglas de Dependencias

* **Regla de Dependencias de Seguridad:**
  NUNCA instales librerías o paquetes nuevos de forma automática en proyectos Node/Python/Kotlin.
  Si crees que necesitas una dependencia, primero debes justificar y esperar la aprobación explícita del usuario respondiendo a los siguientes 6 puntos:
  1. Nombre exacto del paquete.
  2. Para qué se necesita y qué valor aporta.
  3. Fuente oficial de descarga/documentación.
  4. Estado de mantenimiento (si es conocido, usado y seguro).
  5. Alternativa para resolver el problema sin instalar nada (e.g. código nativo).
  6. Comando exacto que ejecutarías para instalarlo.

---

## 3. Flujo de Trabajo en Fases (Planificación y Control)

* **Plan de Implementación (`implementation_plan.md`):** Antes de realizar cualquier cambio que altere la arquitectura del software, base de datos, seguridad o dependencias, redacta un plan y espera aprobación.
* **Checklist (`task.md`):** Divide la tarea aprobada en tareas menores y actualiza el estado de las mismas (`[ ]`, `[/]`, `[x]`) de forma incremental.
* **Informe final (`walkthrough.md`):** Al finalizar, presenta un resumen preciso de los cambios realizados, las pruebas de verificación ejecutadas y cualquier tarea que haya quedado pendiente.
