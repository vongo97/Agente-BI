'use client';

import { useDashboard } from "@/context/DashboardContext";
import { Coffee, AlertCircle, CheckCircle2 } from "lucide-react";

export function ServerStatusTracker() {
    const { isServerHealthy, isWakingUp } = useDashboard();

    if (isServerHealthy === true) return null;

    return (
        <div className="fixed bottom-6 right-6 z-[60] animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className={`
                px-5 py-4 rounded-2xl border backdrop-blur-xl shadow-2xl flex items-center gap-4
                ${isServerHealthy === false
                    ? 'bg-amber-500/10 border-amber-500/20 text-amber-200'
                    : 'bg-blue-500/10 border-blue-500/20 text-blue-200'}
            `}>
                <div className={`
                    p-2.5 rounded-xl
                    ${isServerHealthy === false ? 'bg-amber-500/20' : 'bg-blue-500/20'}
                `}>
                    {isServerHealthy === false ? (
                        <Coffee className="w-5 h-5 animate-bounce" />
                    ) : (
                        <AlertCircle className="w-5 h-5" />
                    )}
                </div>
                <div>
                    <p className="text-sm font-bold tracking-tight">
                        {isServerHealthy === false
                            ? "Preparando el motor..."
                            : "Conectando con el servidor..."}
                    </p>
                    <p className="text-[10px] font-medium opacity-60 uppercase tracking-widest mt-0.5">
                        {isServerHealthy === false
                            ? "Render está despertando (esto toma ~30s)"
                            : "Verificando disponibilidad..."}
                    </p>
                </div>
            </div>
        </div>
    );
}
