import { describe, expect, it } from 'vitest';
import { simulationKeyForProvider } from '@/lib/simulation-provider';

describe('simulationKeyForProvider', () => {
  const keys = { gemini: 'gemini-secret', mistral: 'mistral-secret', groq: 'groq-secret' };

  it.each([
    ['gemini', 'gemini-secret'],
    ['mistral', 'mistral-secret'],
    ['groq', 'groq-secret'],
  ])('uses only the selected provider key (%s)', (provider, expected) => {
    expect(simulationKeyForProvider(provider, keys)).toBe(expected);
  });

  it.each(['openai', 'anthropic', 'deepseek', 'nvidia', 'hybrid'])
    ('does not pass the Gemini key for %s', (provider) => {
      expect(simulationKeyForProvider(provider, keys)).toBe('');
    });
});
