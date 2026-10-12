"use client";

import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, Eye, EyeOff, Key } from "lucide-react";
import { getAiProviders, getProviderModels, saveProviderKeys, saveProviderModels, validateApiKey } from "@/lib/api";

export type AiProvider = {
    id: string;
    label: string;
    console: string;
    free_tier: boolean;
    min_len: number;
    prefixes: string[];
};

type State = { kind: "idle" | "checking" | "ok" | "warn" | "error"; text: string };

const IDLE: State = { kind: "idle", text: "" };

/**
 * Panel de credenciales. Una única fuente de verdad: la lista de proveedores llega del
 * backend (/providers), así que añadir uno en src/engine/providers.py lo hace aparecer
 * aquí sin tocar este componente. No hay listas de proveedores escritas a mano en
 * ninguna otra pantalla.
 */
export function ProviderKeysPanel({ compact = false }: { compact?: boolean }) {
    const [providers, setProviders] = useState<AiProvider[]>([]);
    const [values, setValues] = useState<Record<string, string>>({});
    const [state, setState] = useState<Record<string, State>>({});
    const [reveal, setReveal] = useState<Record<string, boolean>>({});
    const [models, setModels] = useState<Record<string, string[]>>({});
    const [selectedModel, setSelectedModel] = useState<Record<string, string>>({});

    useEffect(() => {
        let cancelled = false;
        getAiProviders()
            .then((r) => { if (!cancelled && r?.providers) setProviders(r.providers); })
            .catch(() => { /* catálogo informativo: si falla, la pantalla sigue usable */ });
        return () => { cancelled = true; };
    }, []);

    // Los modelos se piden solo para el proveedor que tenga más de uno (hoy NVIDIA).
    const ensureModels = useCallback(async (providerId: string) => {
        if (models[providerId]) return;
        try {
            const r = await getProviderModels(providerId);
            if (r?.models?.length) {
                setModels((m) => ({ ...m, [providerId]: r.models }));
                setSelectedModel((s) => (s[providerId] ? s : { ...s, [providerId]: r.models[0] }));
            }
        } catch {
            /* sin modelos en vivo: se mantiene el modelo por defecto del servidor */
        }
    }, [models]);

    const validate = async (p: AiProvider) => {
        const key = (values[p.id] || "").trim();
        if (!key || key.includes("...")) {
            setState((s) => ({ ...s, [p.id]: { kind: "error", text: "Pega tu clave para validarla." } }));
            return;
        }
        setState((s) => ({ ...s, [p.id]: { kind: "checking", text: "Comprobando con el proveedor…" } }));
        try {
            const res = await validateApiKey(key, p.id);
            if (!res.valid) {
                setState((s) => ({ ...s, [p.id]: { kind: "error", text: res.error || "El proveedor rechazó la clave." } }));
                return;
            }
            if (res.detected_provider && res.detected_provider !== p.id) {
                setState((s) => ({ ...s, [p.id]: { kind: "warn", text: `Clave válida, pero es de ${res.detected_provider}. Guárdala en su campo.` } }));
                return;
            }
            await saveProviderKeys({ [`${p.id}_key`]: key });
            setValues((v) => ({ ...v, [p.id]: "" }));
            setState((s) => ({ ...s, [p.id]: { kind: "ok", text: res.message || "Clave válida y guardada." } }));
            await ensureModels(p.id);
        } catch (err) {
            setState((s) => ({ ...s, [p.id]: { kind: "error", text: (err as Error).message } }));
        }
    };

    const chooseModel = async (providerId: string, model: string) => {
        setSelectedModel((s) => ({ ...s, [providerId]: model }));
        try {
            await saveProviderModels({ [providerId]: model });
            setState((s) => ({ ...s, [providerId]: { kind: "ok", text: `Modelo seleccionado: ${model}` } }));
        } catch {
            setState((s) => ({ ...s, [providerId]: { kind: "error", text: "No se pudo guardar el modelo." } }));
        }
    };

    return (
        <div className="space-y-5">
            {!compact && (
                <p className="text-[11px] text-[var(--bi-text-3)] leading-relaxed">
                    Pega tu clave propia del proveedor. Se cifra antes de guardarse y nunca se
                    muestra completa. Los marcados <span className="text-[var(--bi-green)]">GRATIS</span> no
                    requieren tarjeta.
                </p>
            )}
            {providers.length === 0 && (
                <p className="text-[11px] text-[var(--bi-text-3)]">No se pudo cargar el catálogo de proveedores.</p>
            )}
            {providers.map((p) => {
                const st = state[p.id] ?? IDLE;
                const tone = st.kind === "ok" ? "text-[var(--bi-green)]"
                    : st.kind === "error" ? "text-[var(--sim-accent)]"
                    : st.kind === "warn" ? "text-[var(--bi-purple)]"
                    : "text-[var(--bi-text-3)]";
                return (
                    <div key={p.id} className="space-y-2">
                        <label className="text-xs font-semibold text-[var(--bi-text-3)] uppercase tracking-widest ml-1 flex items-center justify-between gap-3 flex-wrap">
                            <span className="flex items-center gap-2">
                                {p.label}
                                {p.free_tier && (
                                    <span className="text-[9px] px-1.5 py-0.5 rounded border border-[var(--bi-green-border)] text-[var(--bi-green)]">GRATIS</span>
                                )}
                            </span>
                            <a href={p.console} target="_blank" rel="noreferrer"
                                className="text-[10px] text-[var(--bi-blue)] hover:underline font-medium normal-case tracking-normal">
                                Obtener clave →
                            </a>
                        </label>
                        <div className="flex gap-2">
                            <div className="relative flex-1">
                                <input
                                    type={reveal[p.id] ? "text" : "password"}
                                    value={values[p.id] || ""}
                                    onChange={(e) => setValues((v) => ({ ...v, [p.id]: e.target.value }))}
                                    onFocus={() => ensureModels(p.id)}
                                    placeholder={p.prefixes[0] ? `${p.prefixes[0]}…` : "pega tu clave"}
                                    className="w-full bg-[var(--bi-surface-1)] border border-[var(--bi-border)] rounded-xl px-4 py-3 pr-12 text-xs text-[var(--bi-text-1)] focus:outline-none focus:border-[var(--bi-green-border)] focus:ring-1 focus:ring-[var(--bi-green-border)] transition-all font-mono"
                                />
                                <button
                                    onClick={() => setReveal((r) => ({ ...r, [p.id]: !r[p.id] }))}
                                    className="absolute right-4 top-1/2 -translate-y-1/2 text-[var(--bi-text-3)] hover:text-[var(--bi-text-1)] transition-colors"
                                    aria-label={`Ver clave de ${p.label}`}
                                >
                                    {reveal[p.id] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                </button>
                            </div>
                            <button
                                onClick={() => validate(p)}
                                disabled={st.kind === "checking"}
                                className="shrink-0 px-4 rounded-xl bg-[var(--bi-surface-1)] border border-[var(--bi-green-border)] text-[var(--bi-green)] text-[10px] font-bold uppercase tracking-wider hover:bg-[var(--bi-surface-2)] transition-colors disabled:opacity-50"
                            >
                                {st.kind === "checking" ? "..." : "Validar"}
                            </button>
                        </div>
                        {models[p.id] && models[p.id].length > 1 && (
                            <select
                                value={selectedModel[p.id] || ""}
                                onChange={(e) => chooseModel(p.id, e.target.value)}
                                className="w-full bg-[var(--bi-surface-1)] border border-[var(--bi-border)] rounded-xl px-4 py-2.5 text-[11px] text-[var(--bi-text-1)] focus:outline-none focus:border-[var(--bi-green-border)] font-mono"
                            >
                                {models[p.id].map((m) => (
                                    <option key={m} value={m}>{m}</option>
                                ))}
                            </select>
                        )}
                        {st.text && <p className={`text-[10px] pl-1 ${tone}`}>{st.text}</p>}
                    </div>
                );
            })}
        </div>
    );
}