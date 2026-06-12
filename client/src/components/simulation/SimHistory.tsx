import { History } from "lucide-react";
import { Simulation } from "@/types/shared";

interface SimHistoryProps {
    simulations: Simulation[];
    activeSim: Simulation | null;
    loadSim: (sim: Simulation) => void;
}

export function SimHistory({ simulations, activeSim, loadSim }: SimHistoryProps) {
    return (
        <div className="w-80 border-r border-[var(--bi-border)] flex flex-col bg-[var(--bi-surface-0)]">
            <div className="p-6 border-b border-[var(--bi-border)]">
                <h2 className="text-[10px] font-semibold text-[var(--bi-text-3)] uppercase tracking-[0.2em] flex items-center gap-2">
                    <History className="w-3.5 h-3.5" /> Historial de Ensayos
                </h2>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
                {simulations.map((sim) => (
                    <button
                        key={sim.id}
                        onClick={() => loadSim(sim)}
                        className={`w-full p-4 rounded-lg border text-left transition-all group cursor-pointer ${activeSim?.id === sim.id 
                            ? 'bg-[var(--sim-accent-soft)] border-[var(--sim-accent)] ring-1 ring-[var(--sim-accent)]' 
                            : 'bg-[var(--bi-surface-1)] border-[var(--bi-border)] hover:border-[var(--bi-border-strong)]'}`}
                    >
                        <div className="flex items-center justify-between mb-2">
                            <span className={`text-[8px] font-semibold uppercase px-2 py-0.5 rounded border ${sim.status === 'completed' ? 'bg-[var(--bi-green-dim)] text-[var(--bi-green)] border-[var(--bi-green)]/20' : 'bg-[var(--sim-accent-soft)] text-[var(--sim-accent)] border-[var(--sim-border)]/20 animate-pulse'}`}>
                                {sim.status}
                            </span>
                            <span className="text-[9px] text-[var(--bi-text-3)] font-semibold">{new Date(sim.created_at).toLocaleDateString()}</span>
                        </div>
                        <p className="text-xs font-semibold text-[var(--bi-text-2)] group-hover:text-[var(--bi-text-1)] truncate">{sim.title}</p>
                    </button>
                ))}
            </div>
        </div>
    );
}
