"use client";

import { useState } from "react";
import {
    AlertTriangle,
    CalendarDays,
    ChevronDown,
    Database,
    Hash,
    Minus,
    Rows3,
    ShieldCheck,
    TrendingDown,
    TrendingUp,
} from "lucide-react";
import type { AuditFact, AuditPayload, AuditSeverity } from "@/types/shared";

interface InsightCardsProps {
    audit: AuditPayload;
}

const SEVERITY_STYLES: Record<AuditSeverity, { border: string; bg: string; text: string; label: string }> = {
    alta: {
        border: "border-[var(--bi-red-border)]",
        bg: "bg-[var(--bi-red-dim)]",
        text: "text-[var(--bi-red)]",
        label: "Alta",
    },
    media: {
        border: "border-[var(--bi-amber)]/25",
        bg: "bg-[var(--bi-amber-dim)]",
        text: "text-[var(--bi-amber)]",
        label: "Media",
    },
    baja: {
        border: "border-[var(--bi-blue-border)]",
        bg: "bg-[var(--bi-blue-dim)]",
        text: "text-[var(--bi-blue)]",
        label: "Baja",
    },
    info: {
        border: "border-[var(--bi-border)]",
        bg: "bg-[var(--bi-surface-1)]",
        text: "text-[var(--bi-text-2)]",
        label: "Dato",
    },
};

function formatNumber(value: number) {
    return new Intl.NumberFormat("es-ES").format(value);
}

function DirectionIcon({ fact }: { fact: AuditFact }) {
    const className = `w-4 h-4 flex-shrink-0 ${
        fact.direction === "negative"
            ? "text-[var(--bi-red)]"
            : fact.direction === "positive"
                ? "text-[var(--bi-green)]"
                : "text-[var(--bi-text-3)]"
    }`;
    if (fact.direction === "negative") return <TrendingDown className={className} aria-label="Negativo" />;
    if (fact.direction === "positive") return <TrendingUp className={className} aria-label="Positivo" />;
    return <Minus className={className} aria-label="Neutral" />;
}

function FactCard({ fact }: { fact: AuditFact }) {
    const style = SEVERITY_STYLES[fact.severity] ?? SEVERITY_STYLES.info;
    return (
        <article className={`rounded-lg border p-3 ${style.border} ${style.bg}`}>
            <div className="flex items-center justify-between gap-2 mb-1">
                <span className={`text-[9px] font-semibold uppercase tracking-wider ${style.text}`}>
                    {fact.category} · {style.label}
                </span>
                <span className="text-[9px] font-mono text-[var(--bi-text-3)]">{fact.id}</span>
            </div>
            <h4 className="text-xs font-semibold text-[var(--bi-text-1)] leading-snug">{fact.title}</h4>
            <div className="flex items-end justify-between gap-2 mt-1.5">
                <p className={`text-lg font-semibold tabular-nums leading-none break-words ${style.text}`}>
                    {fact.display_value}
                </p>
                <DirectionIcon fact={fact} />
            </div>
            <p className="text-[11px] text-[var(--bi-text-2)] leading-relaxed mt-2">{fact.definition}</p>
            <details className="mt-2 group">
                <summary className="list-none cursor-pointer text-[10px] font-semibold text-[var(--bi-teal)] hover:text-[var(--bi-teal-hover)] flex items-center gap-1">
                    <ChevronDown className="w-3 h-3 transition-transform group-open:rotate-180" />
                    Ver cálculo
                </summary>
                <div className="mt-1.5 rounded border border-[var(--bi-border)] bg-[var(--bi-surface-0)] px-2 py-1.5 space-y-1">
                    <code className="block text-[10px] text-[var(--bi-text-2)] break-words">{fact.evidence}</code>
                    <p className="text-[9px] text-[var(--bi-text-3)]">
                        Muestra: {formatNumber(fact.sample_size)} registros
                    </p>
                </div>
            </details>
        </article>
    );
}

export function InsightCards({ audit }: InsightCardsProps) {
    const [showAll, setShowAll] = useState(false);
    const insights = audit.insights ?? [];
    const profile = audit.profile;
    const visible = showAll ? insights : insights.slice(0, 6);
    const hiddenCount = Math.max(0, insights.length - visible.length);
    const quality = profile?.quality ?? [];

    return (
        <section className="rounded-lg border border-[var(--bi-teal-border)] bg-[var(--bi-surface-0)] overflow-hidden">
            <div className="flex items-center justify-between gap-3 px-3 py-2.5 border-b border-[var(--bi-border)] bg-[var(--bi-teal-dim)]">
                <div className="flex items-center gap-2 min-w-0">
                    <ShieldCheck className="w-4 h-4 text-[var(--bi-teal)] flex-shrink-0" />
                    <div className="min-w-0">
                        <p className="text-[11px] font-semibold text-[var(--bi-text-1)]">
                            Auditoría verificada
                        </p>
                        <p className="text-[10px] text-[var(--bi-text-2)] truncate">
                            {insights.length > 0
                                ? `${insights.length} hallazgos calculados con pandas · sin LLM`
                                : "Perfil calculado con pandas · sin métricas inventadas"}
                        </p>
                    </div>
                </div>
                {audit.source_name && (
                    <span className="hidden sm:inline text-[9px] font-mono text-[var(--bi-text-3)] truncate max-w-[220px]">
                        {audit.source_name}
                    </span>
                )}
            </div>

            <div className="p-3 space-y-3">
                <div className="flex flex-wrap gap-1.5">
                    <span className="inline-flex items-center gap-1 px-2 py-1 rounded border border-[var(--bi-border)] bg-[var(--bi-surface-1)] text-[10px] text-[var(--bi-text-2)]">
                        <Rows3 className="w-3 h-3 text-[var(--bi-teal)]" />
                        {formatNumber(profile.rows)} líneas
                    </span>
                    <span className="inline-flex items-center gap-1 px-2 py-1 rounded border border-[var(--bi-border)] bg-[var(--bi-surface-1)] text-[10px] text-[var(--bi-text-2)]">
                        <Database className="w-3 h-3 text-[var(--bi-blue)]" />
                        {formatNumber(profile.columns)} columnas
                    </span>
                    {profile.orders !== null && (
                        <span className="inline-flex items-center gap-1 px-2 py-1 rounded border border-[var(--bi-border)] bg-[var(--bi-surface-1)] text-[10px] text-[var(--bi-text-2)]">
                            <Hash className="w-3 h-3 text-[var(--bi-amber)]" />
                            {formatNumber(profile.orders)} órdenes
                        </span>
                    )}
                    {profile.date_start && profile.date_end && (
                        <span className="inline-flex items-center gap-1 px-2 py-1 rounded border border-[var(--bi-border)] bg-[var(--bi-surface-1)] text-[10px] text-[var(--bi-text-2)]">
                            <CalendarDays className="w-3 h-3 text-[var(--bi-blue)]" />
                            {profile.date_start} → {profile.date_end}
                        </span>
                    )}
                    <span className="inline-flex items-center px-2 py-1 rounded border border-dashed border-[var(--bi-border)] text-[10px] text-[var(--bi-text-3)]">
                        {profile.grain}
                    </span>
                </div>

                {quality.length > 0 && (
                    <div className="rounded border border-[var(--bi-amber)]/20 bg-[var(--bi-amber-dim)] px-2.5 py-2">
                        <div className="flex items-center gap-1.5 text-[var(--bi-amber)] mb-1">
                            <AlertTriangle className="w-3 h-3" />
                            <span className="text-[9px] font-semibold uppercase tracking-wider">Calidad del dato</span>
                        </div>
                        <ul className="space-y-0.5">
                            {quality.slice(0, 4).map((item, index) => (
                                <li key={index} className="text-[10px] text-[var(--bi-text-2)] leading-snug">
                                    {item}
                                </li>
                            ))}
                        </ul>
                        {quality.length > 4 && (
                            <p className="text-[9px] text-[var(--bi-text-3)] mt-1">
                                +{quality.length - 4} observaciones más en la metodología.
                            </p>
                        )}
                    </div>
                )}

                {insights.length > 0 ? (
                    <>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                            {visible.map((fact) => (
                                <FactCard key={fact.id} fact={fact} />
                            ))}
                        </div>
                        {insights.length > 6 && (
                            <button
                                type="button"
                                onClick={() => setShowAll((value) => !value)}
                                className="w-full py-1.5 rounded border border-[var(--bi-border)] bg-[var(--bi-surface-1)] text-[10px] font-semibold text-[var(--bi-text-2)] hover:text-[var(--bi-text-1)] hover:bg-[var(--bi-surface-2)] transition-colors cursor-pointer"
                            >
                                {showAll ? "Ver menos" : `Ver los ${insights.length} hallazgos (${hiddenCount} más)`}
                            </button>
                        )}
                    </>
                ) : (
                    <div className="rounded border border-[var(--bi-border)] bg-[var(--bi-surface-1)] px-3 py-2 text-[11px] text-[var(--bi-text-2)]">
                        No hay columnas de ventas/profit suficientes para calcular hallazgos de rentabilidad.
                        El perfil y la calidad del dataset sí están verificados.
                    </div>
                )}

                <details className="group">
                    <summary className="list-none cursor-pointer text-[10px] font-semibold text-[var(--bi-text-3)] hover:text-[var(--bi-text-1)] flex items-center gap-1">
                        <ChevronDown className="w-3 h-3 transition-transform group-open:rotate-180" />
                        Metodología y definiciones
                    </summary>
                    <div className="mt-2 rounded border border-[var(--bi-border)] bg-[var(--bi-surface-1)] p-2.5 space-y-2">
                        <ul className="space-y-1">
                            {audit.methodology.map((item, index) => (
                                <li key={index} className="text-[10px] text-[var(--bi-text-2)] leading-relaxed">
                                    · {item}
                                </li>
                            ))}
                        </ul>
                        <div className="pt-2 border-t border-[var(--bi-border)] space-y-1">
                            {audit.definitions.map((item) => (
                                <p key={item.term} className="text-[10px] text-[var(--bi-text-2)] leading-relaxed">
                                    <span className="font-semibold text-[var(--bi-text-1)]">{item.term}:</span>{" "}
                                    {item.definition}
                                </p>
                            ))}
                        </div>
                    </div>
                </details>
            </div>
        </section>
    );
}
