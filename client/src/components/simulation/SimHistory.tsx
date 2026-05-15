import { History } from "lucide-react";

interface SimHistoryProps {
    simulations: any[];
    activeSim: any;
    loadSim: (sim: any) => void;
}

export function SimHistory({ simulations, activeSim, loadSim }: SimHistoryProps) {
    return (
        <div className="w-80 border-r border-[var(--border-color)] flex flex-col bg-[var(--bg-secondary)]/50 backdrop-blur-xl">
            <div className="p-6 border-b border-[var(--border-color)]">
                <h2 className="text-[10px] font-black text-gray-500 uppercase tracking-[0.2em] flex items-center gap-2">
                    <History className="w-3 h-3" /> Historial de Ensayos
                </h2>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
                {simulations.map((sim) => (
                    <button
                        key={sim.id}
                        onClick={() => loadSim(sim)}
                        className={`w-full p-4 rounded-2xl border text-left transition-all group ${activeSim?.id === sim.id 
                            ? 'bg-purple-600/10 border-purple-500/30' 
                            : 'bg-white/[0.02] border-white/5 hover:border-white/10'}`}
                    >
                        <div className="flex items-center justify-between mb-2">
                            <span className={`text-[8px] font-black uppercase px-2 py-0.5 rounded ${sim.status === 'completed' ? 'bg-green-500/20 text-green-400' : 'bg-purple-500/20 text-purple-400 animate-pulse'}`}>
                                {sim.status}
                            </span>
                            <span className="text-[9px] text-gray-600 font-bold">{new Date(sim.created_at).toLocaleDateString()}</span>
                        </div>
                        <p className="text-xs font-bold text-gray-300 group-hover:text-white truncate">{sim.title}</p>
                    </button>
                ))}
            </div>
        </div>
    );
}
