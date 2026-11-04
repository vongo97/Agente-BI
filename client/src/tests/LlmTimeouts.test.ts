import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { LLM_TIMEOUT_MS } from '@/lib/api';

/**
 * P-61 (ampliación 2026-11-04): regresión del timeout de las llamadas LLM.
 *
 * El flujo de /analyze tarda 30-90 s (hasta ~3 min con presupuesto de
 * proveedor). Con el timeout por defecto de 30 s el cliente abortaba con
 * "Tiempo de espera agotado al conectar con el servidor" (reproducido en
 * producción con el dataset INE) y, encima, reintentaba 2 veces: cada
 * reintento re-ejecutaba el análisis completo en el servidor. Esta guarda
 * estática (mismo patrón que CSP.test.ts) falla si una llamada LLM nueva
 * se añade sin `LLM_NETWORK_OPTIONS`.
 */
const LLM_ENDPOINTS = [
  '/analyze',
  '/generate-report-summary',
  '/auto-dashboard',
  '/suggest-questions',
  '/visual-summary',
  '/simulation/ontology',
  '/simulation/generate-agents',
  '/simulation/suggestions',
] as const;

describe('LLM network options (P-61)', () => {
  const source = readFileSync(join(process.cwd(), 'src/lib/api.ts'), 'utf-8');

  it('defines a timeout long enough for provider budgets (>= 120 s) without retries', () => {
    expect(LLM_TIMEOUT_MS).toBeGreaterThanOrEqual(120_000);
    expect(source).toContain('timeoutMs: LLM_TIMEOUT_MS');
    expect(source).toContain('retries: 0');
  });

  it.each(LLM_ENDPOINTS)('passes LLM_NETWORK_OPTIONS to %s', (endpoint) => {
    const callIndex = source.indexOf('`${API_URL}' + endpoint + '`');
    expect(callIndex).toBeGreaterThanOrEqual(0);
    const callEnd = source.indexOf('});', callIndex);
    const callBody = source.slice(callIndex, callEnd);
    expect(callBody).toContain('LLM_NETWORK_OPTIONS');
  });

  it('covers every LLM call site defined in the module', () => {
    const uses = source.match(/LLM_NETWORK_OPTIONS\);/g) ?? [];
    expect(uses.length).toBe(LLM_ENDPOINTS.length);
  });
});
