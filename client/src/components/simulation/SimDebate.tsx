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
        <div className="col-span-12 lg:col-span-7 space-y-8 pb-20">
            <div className="flex items-center justify-between px-2">
                <h3 className="text-[10px] font-black text-gray-600 uppercase tracking-widest">Interacción del Enjambre</h3>
                <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-purple-500 animate-pulse"></span>
                    <span className="text-[9px] font-bold text-purple-400 uppercase tracking-tighter">Debate en Curso</span>
                </div>
            </div>
            
            <div className="space-y-4">
                {messages
                    .filter(m => m.content && !m.content.includes("Límite de cuota") && !m.content.includes("Error Gemini"))
                    .map((m, idx) => (
                    <div key={idx} className="bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-2xl p-6 space-y-3 animate-in slide-in-from-bottom-4 duration-500 relative overflow-hidden group shadow-lg hover:shadow-purple-500/5 transition-all">
                        {/* Badge de Ronda */}
                        {m.round_number && (
                            <div className="absolute top-0 right-0 px-3 py-1 bg-purple-600/20 text-purple-400 text-[8px] font-black uppercase tracking-widest rounded-bl-xl border-l border-b border-purple-500/20 group-hover:bg-purple-600/30 transition-all">
                                Ronda {m.round_number}
                            </div>
                        )}
                        
                        <div className="flex items-center justify-between">
                            <div className="flex flex-col">
                                <span className="text-[10px] font-black text-purple-400 uppercase tracking-widest bg-purple-500/10 px-2 py-1 rounded inline-block w-fit">
                                    {m.agent_name || "Agente"}
                                </span>
                                <span className="text-[9px] text-gray-600 font-bold mt-1 uppercase tracking-tighter">{m.agent_role}</span>
                            </div>
                        </div>
                        <div className="text-sm text-gray-300 leading-relaxed font-medium markdown-content">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {m.content}
                            </ReactMarkdown>
                        </div>
                    </div>
                ))}
                
                {polling && (
                    <div className="flex flex-col gap-4 p-6 bg-purple-600/5 rounded-2xl border border-dashed border-purple-500/20 animate-pulse">
                        <div className="flex items-center gap-3">
                            <Loader2 className="w-4 h-4 text-purple-500 animate-spin" />
                            <div className="flex flex-col">
                                <span className="text-[10px] font-black text-purple-500 uppercase tracking-[0.2em]">
                                    Ronda {activeSim?.current_round || 1} • Procesando Debate
                                </span>
                                <span className="text-[8px] text-gray-500 font-bold uppercase tracking-widest">
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
