import { Loader2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface SimDebateProps {
    messages: any[];
    polling: boolean;
    activeSim: any;
}

export function SimDebate({ messages, polling, activeSim }: SimDebateProps) {
    return (
        <div className="col-span-12 lg:col-span-7 space-y-6 pb-20">
            <div className="flex items-center justify-between px-2">
                <h3 className="text-[10px] font-semibold text-[var(--bi-text-3)] uppercase tracking-widest">Interacción del Enjambre</h3>
                <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-[var(--sim-accent)] animate-pulse"></span>
                    <span className="text-[9px] font-bold text-[var(--sim-accent)] uppercase tracking-tighter">Debate en Curso</span>
                </div>
            </div>
            
            <div className="space-y-4">
                {messages
                    .filter(m => m.content && !m.content.includes("Límite de cuota") && !m.content.includes("Error Gemini"))
                    .map((m, idx) => (
                    <div key={idx} className="bg-[var(--bi-surface-0)] border border-[var(--bi-border)] rounded-lg p-6 space-y-3 animate-in slide-in-from-bottom-4 duration-500 relative overflow-hidden group shadow-md hover:border-[var(--sim-border)]/50 transition-all">
                        {/* Badge de Ronda */}
                        {m.round_number && (
                            <div className="absolute top-0 right-0 px-3 py-1 bg-[var(--sim-accent-soft)] text-[var(--sim-accent)] text-[8px] font-semibold uppercase tracking-wider rounded-bl-lg border-l border-b border-[var(--sim-border)] transition-all">
                                Ronda {m.round_number}
                            </div>
                        )}
                        
                        <div className="flex items-center justify-between">
                            <div className="flex flex-col">
                                <span className="text-[10px] font-bold text-[var(--sim-accent)] uppercase tracking-wider bg-[var(--sim-accent-soft)] px-2.5 py-0.5 rounded border border-[var(--sim-border)] inline-block w-fit">
                                    {m.agent_name || "Agente"}
                                </span>
                                <span className="text-[9px] text-[var(--bi-text-3)] font-semibold mt-1 uppercase tracking-tighter">{m.agent_role}</span>
                            </div>
                        </div>
                        <div className="text-sm text-[var(--bi-text-2)] leading-relaxed font-medium markdown-content">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {m.content}
                            </ReactMarkdown>
                        </div>
                    </div>
                ))}
                
                {polling && (
                    <div className="flex flex-col gap-4 p-6 bg-[var(--sim-accent-soft)]/10 rounded-lg border border-dashed border-[var(--sim-border)]/50 animate-pulse">
                        <div className="flex items-center gap-3">
                            <Loader2 className="w-4 h-4 text-[var(--sim-accent)] animate-spin" />
                            <div className="flex flex-col">
                                <span className="text-[10px] font-bold text-[var(--sim-accent)] uppercase tracking-wider">
                                    Ronda {activeSim?.current_round || 1} • Procesando Debate
                                </span>
                                <span className="text-[8px] text-[var(--bi-text-3)] font-semibold uppercase tracking-widest mt-0.5">
                                    Los agentes están analizando las variables en tiempo real...
                                </span>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
