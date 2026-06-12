# Continuidad del Proyecto Vektra BI

## Contexto General

Este proyecto es **Vektra BI**, una aplicacion BI con frontend en Next.js/Tailwind y backend en FastAPI. En esta fase se esta transformando el producto hacia un estilo visual global llamado **Dark BI Workspace Premium**: una interfaz dark-first, profesional, compacta, tecnica y orientada a analisis de datos.

El repo ya contiene instrucciones para agentes en `AGENTS.md` y skills especificas en `.codex/skills`.

Antes de hacer cambios, cualquier asistente debe leer:

- `AGENTS.md`
- `.codex/skills/vektra-product-design/SKILL.md`
- `.codex/skills/vektra-security-review/SKILL.md` si toca backend, auth, API, secretos o endpoints
- `.codex/skills/vektra-api-contracts/SKILL.md` si toca frontend/backend API
- `.codex/skills/vektra-architecture-refactor/SKILL.md` si toca estructura mayor

## Estado Actual

Ya se implemento un sistema visual global en el frontend:

- Tokens CSS dark-first en `client/src/app/globals.css`
- Uso de Tailwind v4 con tokens en CSS, sin `tailwind.config.js`
- Componentes reutilizables como `.panel`, `.btn-primary`, `.btn-ghost`, `.btn-toolbar`, `.input-bi`, `.badge`, `.nav-item`
- Acento semantico del modulo Simulador con variables `--module-simulation-*`
- Layout, Sidebar, Chat, Dashboard, Settings, Visual Summary, Simulador y Report Builder migrados visualmente al nuevo estilo

El estilo aprobado por el usuario es:

- Dark BI workspace premium
- Fondo negro/carbon
- Superficies oscuras diferenciadas
- Bordes sutiles
- UI compacta y profesional
- Acentos teal/cian/azul para BI
- Morado controlado para Simulador
- Nada de landing page, cards gigantes, gradientes decorativos gratuitos ni cards dentro de cards

## Resultado De La Ultima Verificacion

El otro asistente realizo una limpieza de calidad posterior al rediseño.

### Archivos corregidos en esa limpieza

- `client/src/components/simulation/SimForm.tsx`
  - Corrigio `react/no-unescaped-entities` escapando comillas en JSX.
- `client/src/context/ThemeContext.tsx`
  - Corrigio `react-hooks/set-state-in-effect` usando lazy initializer.
- `client/src/components/Sidebar.tsx`
  - Elimino iconos, funciones, variables de contexto e imports API sin uso.
  - Limpio logica obsoleta del sidebar rediseñado.
- `client/src/components/Chat.tsx`
  - Elimino `Loader2` sin uso.
- `client/src/components/DashboardView.tsx`
  - Elimino `Sparkles` sin uso.
- `client/src/components/ServerStatusTracker.tsx`
  - Elimino `CheckCircle2` e `isWakingUp` sin uso.
- `client/src/app/login/page.tsx`
  - Elimino `session` sin uso.

### Validaciones reportadas

- `npx tsc --noEmit`: pasa limpio con 0 errores.
- `npm run lint`: bajo de 115 a 92 problemas.
- Los 92 problemas restantes se consideran deuda tecnica por ahora, principalmente:
  - `@typescript-eslint/no-explicit-any`
  - `react-hooks/exhaustive-deps`
  - algunos `no-unused-vars` preexistentes
- Dev server corrio en `http://localhost:3000`.
- Verificacion visual reportada como correcta en:
  - Login
  - Chat + Sidebar
  - Dashboard
  - Settings
  - Simulator
  - Mobile responsive

## Importante

No hacer refactor masivo de los 92 problemas de lint sin aprobacion.

La instruccion actual es:

- Mantener el rediseño estable.
- No tocar backend todavia salvo que se pida.
- No cambiar contratos API sin aplicar `vektra-api-contracts`.
- No confiar en `user_id` del cliente como autoridad.
- No romper comportamiento existente.
- No eliminar el acento morado del Simulador; debe mantenerse como token semantico controlado.

## Proximo Paso Recomendado

Como el rediseño ya esta validado tecnicamente y visualmente, el siguiente bloque deberia ser uno de estos:

1. **Checkpoint Git**
   - Revisar `git status`.
   - Separar cambios intencionales del rediseño y skills.
   - No incluir `server/.venv-codex/`, `server/scratch/` ni `server/scratch_test.py` salvo que el usuario lo pida.
   - Commit sugerido: `feat: add Vektra design system and project skills`

2. **Hardening backend inicial**
   - Leer `vektra-security-review`.
   - Proteger o eliminar `/sources/clear-force`.
   - Revisar endpoints destructivos sin auth.
   - Agregar test minimo si aplica.

3. **Limpieza API gradual**
   - Leer `vektra-api-contracts`.
   - Empezar a retirar `user_id` como autoridad del cliente.
   - Mantener compatibilidad mientras se migra.

4. **Deuda lint por fases**
   - No resolver todo de golpe.
   - Primer bloque sugerido: tipos compartidos para Dashboard/Simulation/Chat para reducir `any`.

## Prompt Para Continuar Con Otro Asistente

```text
Lee primero AGENTS.md.

Despues lee estas skills segun la tarea:
- .codex/skills/vektra-product-design/SKILL.md
- .codex/skills/vektra-security-review/SKILL.md
- .codex/skills/vektra-api-contracts/SKILL.md
- .codex/skills/vektra-architecture-refactor/SKILL.md si propones refactor grande

Contexto:
Venimos de una migracion visual global del frontend de Vektra BI al sistema Dark BI Workspace Premium. El estilo fue aprobado por el usuario. El frontend usa Tailwind v4 y los tokens estan en client/src/app/globals.css. No crear tailwind.config.js salvo razon fuerte.

Estado validado:
- npx tsc --noEmit pasa con 0 errores.
- npm run lint bajo de 115 a 92 problemas.
- Los 92 restantes son deuda tecnica y no deben arreglarse en masa sin aprobacion.
- Login, Sidebar, Chat, Dashboard, Settings, Simulator y mobile fueron verificados visualmente.

Reglas:
- No romper el rediseño.
- No hacer refactors grandes no solicitados.
- No tocar backend si la tarea es solo frontend.
- No cambiar contratos API sin aplicar vektra-api-contracts.
- No confiar en user_id del cliente como autoridad.
- Mantener dark-first.
- Mantener el acento morado del Simulador como token semantico controlado, no eliminarlo.
- No incluir en git server/.venv-codex/, server/scratch/ ni server/scratch_test.py salvo instruccion explicita.

Tarea sugerida para continuar:
Primero revisa git status y resume el estado exacto de cambios. Luego propon el siguiente paso entre:
1. crear checkpoint/commit del sistema visual y skills,
2. iniciar hardening backend con /sources/clear-force,
3. limpiar contratos API user_id,
4. reducir deuda lint por fases.

Antes de editar archivos, dime que opcion recomiendas y que archivos tocarias.
```
