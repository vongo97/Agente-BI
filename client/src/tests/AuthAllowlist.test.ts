import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

const origEnv = process.env.NEXT_PUBLIC_AUTHORIZED_EMAILS;

beforeEach(() => {
  vi.resetModules();
});

afterEach(() => {
  process.env.NEXT_PUBLIC_AUTHORIZED_EMAILS = origEnv;
});

async function reloadModule(value: string | undefined) {
  if (value === undefined) {
    delete process.env.NEXT_PUBLIC_AUTHORIZED_EMAILS;
  } else {
    process.env.NEXT_PUBLIC_AUTHORIZED_EMAILS = value;
  }
  return await import('@/lib/auth-allowlist');
}

describe('P-15 auth-allowlist', () => {
  it('sin variable configurada: acceso abierto (cualquier email autorizado)', async () => {
    const mod = await reloadModule(undefined);
    expect(mod.hasAuthorizedEmailsConfigured()).toBe(false);
    expect(mod.isAuthorizedEmail('cualquier@correo.com')).toBe(true);
    expect(mod.isAuthorizedEmail('invitado@agente-bi.local')).toBe(true);
    expect(mod.getAuthorizedEmails()).toEqual([]);
  });

  it('con variable configurada: solo emails de la lista están autorizados', async () => {
    const mod = await reloadModule('ana@empresa.com, luis@empresa.com');
    expect(mod.hasAuthorizedEmailsConfigured()).toBe(true);
    expect(mod.getAuthorizedEmails()).toEqual(['ana@empresa.com', 'luis@empresa.com']);

    expect(mod.isAuthorizedEmail('ana@empresa.com')).toBe(true);
    expect(mod.isAuthorizedEmail('LUIS@EMPRESA.COM')).toBe(true); // case-insensitive
    expect(mod.isAuthorizedEmail('otro@correo.com')).toBe(false);
    expect(mod.isAuthorizedEmail('')).toBe(false);
    expect(mod.isAuthorizedEmail(undefined as any)).toBe(false);
    expect(mod.isAuthorizedEmail(null as any)).toBe(false);
  });

  it('ignorar espacios y entradas vacías en la lista', async () => {
    const mod = await reloadModule('  ana@empresa.com , , luis@empresa.com  ');
    expect(mod.getAuthorizedEmails()).toEqual(['ana@empresa.com', 'luis@empresa.com']);
    expect(mod.isAuthorizedEmail('ana@empresa.com')).toBe(true);
    expect(mod.isAuthorizedEmail('invitado@agente-bi.local')).toBe(false);
  });

  it('email con mayúsculas/minúsculas se normaliza', async () => {
    const mod = await reloadModule('Ana@Empresa.com');
    expect(mod.isAuthorizedEmail('ana@empresa.com')).toBe(true);
    expect(mod.isAuthorizedEmail('ANA@EMPRESA.COM')).toBe(true);
  });
});
