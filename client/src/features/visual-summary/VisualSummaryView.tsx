'use client';

import React from 'react';
import { useDashboard } from '@/context/DashboardContext';
import { ChevronDown, Sparkles, Clock } from 'lucide-react';

export function VisualSummaryView() {
    const { setSidebarOpen } = useDashboard();
    
    return (
        <div className="flex flex-col h-screen flex-1 bg-[var(--bi-canvas)] overflow-hidden border-l border-[var(--bi-border)]">
            {/* Header */}
            <header className="px-6 py-4 border-b border-[var(--bi-border)] flex items-center justify-between bg-[var(--bi-surface-0)] sticky top-0 z-10 w-full shrink-0 select-none">
                <div className="flex items-center gap-3">
                    <button
                        onClick={() => setSidebarOpen(true)}
                        className="lg:hidden p-2 text-[var(--bi-text-3)] hover:text-[var(--bi-text-1)]"
                    >
                        <ChevronDown className="w-5 h-5 -rotate-90" />
                    </button>
                    <div>
                        <div className="flex items-center gap-2">
                            <h2 className="text-sm font-semibold tracking-tight text-[var(--bi-text-1)] uppercase">Resumen Visual</h2>
                            <span className="text-[9px] bg-[var(--bi-blue-dim)] border border-[var(--bi-blue-border)] text-[var(--bi-blue)] py-0.5 px-2 rounded-md font-bold uppercase tracking-wider">Próximamente</span>
                        </div>
                        <p className="text-[10px] text-[var(--bi-text-3)] font-medium">Convierte ideas complejas y chats en diagramas visuales</p>
                    </div>
                </div>
            </header>

            {/* Contenido Muy Pronto */}
            <div className="flex-1 flex flex-col items-center justify-center p-6 text-center select-none bg-gradient-to-b from-[var(--bi-canvas)] to-[var(--bi-surface-0)]/40">
                <div className="max-w-md p-8 rounded-2xl border border-[var(--bi-border)] bg-[var(--bi-surface-0)]/60 backdrop-blur-md shadow-xl flex flex-col items-center space-y-6">
                    <div className="w-16 h-16 rounded-full bg-[var(--bi-blue-dim)] flex items-center justify-center border border-[var(--bi-blue-border)] animate-pulse">
                        <Clock className="w-8 h-8 text-[var(--bi-blue)]" />
                    </div>
                    
                    <div className="space-y-2">
                        <h3 className="text-lg font-bold text-[var(--bi-text-1)] tracking-tight">Estamos Rediseñando esta Experiencia</h3>
                        <p className="text-xs text-[var(--bi-text-3)] leading-relaxed">
                            El apartado de Resumen Visual está siendo reconstruido desde cero para ofrecerte diagramación interactiva de nivel profesional con edición en caliente, exportación mejorada y auto-distribución inteligente.
                        </p>
                    </div>
                    
                    <div className="flex items-center gap-2 text-[10px] bg-[var(--bi-surface-1)] border border-[var(--bi-border)] text-[var(--bi-text-2)] py-1.5 px-4 rounded-full font-semibold">
                        <Sparkles className="w-3.5 h-3.5 text-[var(--bi-blue)]" />
                        <span>¡Disponible muy pronto!</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
