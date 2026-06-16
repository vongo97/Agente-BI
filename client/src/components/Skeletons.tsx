'use client';

import React from 'react';

// Esqueleto Shimmer genérico
export function Shimmer({ className }: { className?: string }) {
    return <div className={`shimmer-skeleton rounded ${className || ''}`} />;
}

// Esqueleto de una tarjeta KPI
export function KpiSkeleton() {
    return (
        <div className="bg-[var(--bi-surface-0)] border border-[var(--bi-border)] rounded-xl p-5 flex flex-col justify-between h-32 relative overflow-hidden">
            <div className="flex items-center justify-between">
                <Shimmer className="w-8 h-8 rounded-lg" />
                <Shimmer className="w-4 h-4 rounded-full" />
            </div>
            <div className="space-y-2">
                <Shimmer className="w-24 h-3" />
                <Shimmer className="w-16 h-6" />
            </div>
            <div className="mt-2">
                <Shimmer className="w-32 h-2.5" />
            </div>
        </div>
    );
}

// Esqueleto de un gráfico (con siluetas simuladas)
export function ChartSkeleton({ type = 'bar' }: { type?: 'bar' | 'line' | 'pie' }) {
    return (
        <div className="w-full h-full flex flex-col p-4 bg-[var(--bi-surface-0)] border border-[var(--bi-border)] rounded-xl relative overflow-hidden">
            {/* Header del gráfico */}
            <div className="flex items-center justify-between mb-4 border-b border-[var(--bi-border)] pb-2 shrink-0">
                <div className="space-y-1">
                    <Shimmer className="w-16 h-2" />
                    <Shimmer className="w-32 h-3.5" />
                </div>
                <div className="flex gap-2">
                    <Shimmer className="w-6 h-6 rounded-md" />
                    <Shimmer className="w-6 h-6 rounded-md" />
                </div>
            </div>

            {/* Contenido del gráfico simulado */}
            <div className="flex-1 flex items-end gap-3 justify-center min-h-[200px] w-full px-4 relative">
                {type === 'bar' && (
                    <div className="w-full h-full flex items-end justify-between gap-2.5">
                        <Shimmer className="w-[12%] h-[40%] rounded-t-md" />
                        <Shimmer className="w-[12%] h-[75%] rounded-t-md" />
                        <Shimmer className="w-[12%] h-[55%] rounded-t-md" />
                        <Shimmer className="w-[12%] h-[90%] rounded-t-md" />
                        <Shimmer className="w-[12%] h-[30%] rounded-t-md" />
                        <Shimmer className="w-[12%] h-[65%] rounded-t-md" />
                        <Shimmer className="w-[12%] h-[50%] rounded-t-md" />
                    </div>
                )}

                {type === 'line' && (
                    <div className="w-full h-full flex flex-col justify-between py-6">
                        {/* Ejes y rejilla simulada */}
                        <div className="w-full border-b border-[var(--bi-border)] opacity-30 h-1" />
                        <div className="w-full border-b border-[var(--bi-border)] opacity-30 h-1" />
                        <div className="w-full border-b border-[var(--bi-border)] opacity-30 h-1" />
                        {/* Línea shimmer diagonal */}
                        <div className="absolute inset-0 flex items-center justify-center">
                            <svg className="w-full h-full text-[var(--bi-border-strong)] opacity-20" viewBox="0 0 100 100" preserveAspectRatio="none">
                                <path
                                    d="M0,80 Q25,20 50,50 T100,20"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth="3"
                                    className="animate-pulse"
                                />
                            </svg>
                        </div>
                    </div>
                )}

                {type === 'pie' && (
                    <div className="w-full h-full flex items-center justify-center py-4">
                        <div className="w-36 h-36 rounded-full border-8 border-[var(--bi-border-strong)] border-t-[var(--bi-blue-dim)] animate-spin duration-3000" />
                    </div>
                )}
            </div>
        </div>
    );
}

// Esqueleto de una fila de tabla shimmer
export function TableRowSkeleton() {
    return (
        <div className="flex items-center justify-between py-3 border-b border-[var(--bi-border)] px-4">
            <Shimmer className="w-1/4 h-3" />
            <Shimmer className="w-1/6 h-3" />
            <Shimmer className="w-1/5 h-3" />
            <Shimmer className="w-12 h-3" />
        </div>
    );
}

// Esqueleto para representar el Dashboard completo cargando
export function DashboardSkeleton() {
    return (
        <div className="flex-1 bg-[var(--bi-canvas)] flex flex-col h-screen overflow-hidden border-l border-[var(--bi-border)] animate-pulse">
            {/* Header del Dashboard */}
            <header className="h-16 border-b border-[var(--bi-border)] flex items-center justify-between px-8 bg-[var(--bi-surface-0)]/80 backdrop-blur-xl shrink-0">
                <div className="flex items-center gap-4">
                    <Shimmer className="w-8 h-8 rounded-lg" />
                    <Shimmer className="w-48 h-4" />
                </div>
                <div className="flex gap-3">
                    <Shimmer className="w-24 h-8 rounded-lg" />
                </div>
            </header>

            {/* Grid del Dashboard */}
            <div className="flex-1 overflow-y-auto p-6 max-w-7xl mx-auto w-full space-y-6">
                {/* 3 KPIs principales en Shimmer */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                    <KpiSkeleton />
                    <KpiSkeleton />
                    <KpiSkeleton />
                </div>

                {/* 2 Gráficos grandes en Shimmer */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
                    <ChartSkeleton type="bar" />
                    <ChartSkeleton type="line" />
                </div>
            </div>
        </div>
    );
}
