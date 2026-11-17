import { History, X } from "lucide-react";
import { Simulation } from "@/types/shared";

interface SimHistoryProps {
    simulations: Simulation[];
    activeSim: Simulation | null;
    loadSim: (sim: Simulation) => void;
    /** P-40: en movil el historial es un cajon, no una columna fija. */
    isOpen: boolean;
    onClose: () => void;
}

export function SimHistory({ simulations, activeSim, loadSim, isOpen, onClose }: SimHistoryProps) {
    return (
        <>
            {/* P-40: velo del cajon (solo movil). */}
            {isOpen && (
                <div
                    className="fixed inset-0 bg-black/60 backdrop-blur-md z-40 md:hidden"
                    onClick={onClose}
                    aria-hidden="true"
                />
            )}

            <aside
                aria-label="Historial de ensayos"
                className={`
                    fixed md:relative inset-y-0 left-0 z-50
                    w-72 md:w-80 border-r border-[var(--bi-border)] flex flex-col
                    bg-[var(--bi-surface-0)] flex-shrink-0 h-screen md:h-auto
                    transition-transform duration-300 ease-in-out
                    ${isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
                `}
            >
            {/* P-40: cerrar el cajon (solo movil). */}
            <button
                type="button"
                onClick={onClose}
                className="md:hidden absolute top-3 right-3 p-1.5 rounded text-[var(--bi-text-3)] hover:text-[var(--bi-text-1)] hover:bg-[var(--bi-surface-2)] transition-colors z-10"
                aria-label="Cerrar historial"
            >
                <X className="w-4 h-4" />
            </button>
            <div className="p-6 border-b border-[var(--bi-border)]">
                <h2 className="text-[10px] font-bold text-[var(--bi-text-3)] uppercase tracking-[0.25em] flex items-center gap-2">
                    <History className="w-4 h-4 text-[var(--module-simulation-accent)]" /> Historial de Ensayos
                </h2>
            </div>
            
            <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar bg-[var(--bi-canvas)]/30">
                {simulations.length > 0 ? (
                    simulations.map((sim) => {
                        const isActive = activeSim?.id === sim.id;
                        return (
                            <button
                                key={sim.id}
                                type="button"
                                onClick={() => loadSim(sim)}
                                className={`w-full p-4 rounded-xl border text-left transition-all duration-200 group cursor-pointer hover:translate-x-0.5 ${
                                    isActive 
                                    ? 'bg-[var(--module-simulation-accent-soft)] border-[var(--module-simulation-accent)] ring-1 ring-[var(--module-simulation-accent)] shadow-lg shadow-[rgba(168,85,247,0.1)]' 
                                    : 'bg-[var(--bi-surface-0)] border-[var(--bi-border)] hover:border-[var(--module-simulation-border)]/50 hover:bg-[var(--bi-surface-1)] hover:shadow-md'
                                }`}
                            >
                                <div className="flex items-center justify-between mb-2">
                                    <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded border tracking-wider transition-all ${
                                        sim.status === 'completed' 
                                            ? 'bg-[var(--bi-green-dim)] text-[var(--bi-green)] border-[var(--bi-green)]/20' 
                                            : sim.status === 'running'
                                                ? 'bg-[var(--module-simulation-accent-soft)] text-[var(--module-simulation-accent)] border-[var(--module-simulation-border)] animate-pulse'
                                                : 'bg-[var(--bi-red-dim)] text-[var(--bi-red)] border-[var(--bi-red-border)]'
                                    }`}>
                                        {sim.status === 'completed' ? 'Listo' : sim.status === 'running' ? 'En Curso' : sim.status === 'pending' ? 'Pendiente' : 'Desconocido'}
                                    </span>
                                    <span className="text-[10px] text-[var(--bi-text-3)] font-semibold">
                                        {new Date(sim.created_at).toLocaleDateString()}
                                    </span>
                                </div>
                                <p className={`text-xs font-bold truncate transition-colors ${
                                    isActive ? 'text-[var(--bi-text-1)]' : 'text-[var(--bi-text-2)] group-hover:text-[var(--bi-text-1)]'
                                }`}>
                                    {sim.title}
                                </p>
                            </button>
                        );
                    })
                ) : (
                    <div className="py-12 text-center">
                        <p className="text-[10px] text-[var(--bi-text-3)] italic">No hay ensayos previos.</p>
                    </div>
                )}
            </div>
            </aside>
        </>
    );
}
