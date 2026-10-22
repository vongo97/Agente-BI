import { describe, it, expect } from 'vitest';

function buildCsp(apiUrl: string | undefined): string {
  const apiBaseUrl = (apiUrl || "http://127.0.0.1:8000").replace(/\/+$/, "");
  const connectSources = [
    "'self'",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "ws://localhost:8000",
    "wss://localhost:8000",
    apiBaseUrl,
  ];

  return `
    default-src 'self';
    script-src 'self';
    style-src 'self';
    img-src 'self' blob: data: https://lh3.googleusercontent.com;
    font-src 'self' https://fonts.gstatic.com;
    connect-src ${[...new Set(connectSources)].join(" ")};
    frame-ancestors 'none';
    base-uri 'self';
    form-action 'self';
    object-src 'none';
    frame-src 'none';
  `.replace(/\s{2,}/g, ' ').trim();
}

describe('P-07 CSP endurecida', () => {
  it('no permite unsafe-eval en script-src', () => {
    const csp = buildCsp(undefined);
    expect(csp).not.toContain("'unsafe-eval'");
  });

  it('no permite unsafe-inline en script-src', () => {
    const csp = buildCsp(undefined);
    expect(csp).not.toContain("'unsafe-inline'");
  });

  it('no permite unsafe-inline en style-src', () => {
    const csp = buildCsp(undefined);
    expect(csp).not.toContain("'unsafe-inline'");
  });

  it('incluye frame-ancestors none', () => {
    const csp = buildCsp(undefined);
    expect(csp).toContain("frame-ancestors 'none'");
  });

  it('incluye base-uri self', () => {
    const csp = buildCsp(undefined);
    expect(csp).toContain("base-uri 'self'");
  });

  it('incluye form-action self', () => {
    const csp = buildCsp(undefined);
    expect(csp).toContain("form-action 'self'");
  });

  it('incluye object-src none', () => {
    const csp = buildCsp(undefined);
    expect(csp).toContain("object-src 'none'");
  });

  it('incluye frame-src none', () => {
    const csp = buildCsp(undefined);
    expect(csp).toContain("frame-src 'none'");
  });

  it('no permite ws: o wss: genéricos sin host específico', () => {
    const csp = buildCsp(undefined);
    // No debe aparecer 'ws:' seguido de espacio o punto y coma (esquema inválido sin host)
    expect(csp).not.toMatch(/ws:[^/]/);
    expect(csp).not.toMatch(/wss:[^/]/);
    // Pero ws://localhost:8000 y wss://localhost:8000 sí están permitidos
    expect(csp).toContain("ws://localhost:8000");
    expect(csp).toContain("wss://localhost:8000");
  });

  it('incluye la URL de API configurada en connect-src', () => {
    const csp = buildCsp("https://agente-bi-server-7nav-zifr.onrender.com");
    expect(csp).toContain("https://agente-bi-server-7nav-zifr.onrender.com");
  });

  it('default-src es self', () => {
    const csp = buildCsp(undefined);
    expect(csp).toMatch(/default-src 'self';/);
  });

  it('script-src es solo self', () => {
    const csp = buildCsp(undefined);
    expect(csp).toMatch(/script-src 'self';/);
  });

  it('style-src es solo self', () => {
    const csp = buildCsp(undefined);
    expect(csp).toMatch(/style-src 'self';/);
  });
});
