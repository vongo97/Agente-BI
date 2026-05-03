'use client';

import { useState, useEffect, useRef } from "react";
import { useSession } from "next-auth/react";
import { useDashboard } from "@/context/DashboardContext";
import { createSimulation, getSimulations, getSimulationDetails, getSimulationMessages, getDataSources, retrySimulation, getSimulationPdfUrl } from "@/lib/api";
import { Brain, Play, Clock, CheckCircle, AlertCircle, MessageSquare, Shield, Activity, Sparkles, Database, ChevronRight, User, Bot, RefreshCcw, FileText } from "lucide-react";
import ReactMarkdown from 'react-markdown';

export function SimulationSandbox() {
    const { data: session } = useSession();
    const { dataSources, apiKey, aiProvider } = useDashboard();
    const [simulations, setSimulations] = useState<any[]>([]);
    const [activeSim, setActiveSim] = useState<any>(null);
    const [messages, setMessages] = useState<any[]>([]);
    const [title, setTitle] = useState("");
    const [hypothesis, setHypothesis] = useState("");
    const [loading, setLoading] = useState(false);
    const [polling, setPolling] = useState(false);
    const [availableSources, setAvailableSources] = useState<any[]>([]);
    const [selectedSourceId, setSelectedSourceId] = useState<number | undefined>(dataSources[0]?.id);
    
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const userId = session?.user?.email || "invitado@agente-bi.local";

    useEffect(() => {
        fetchSimulations();
        fetchSources();
    }, [userId]);

    useEffect(() => {
        let interval: any;
        if (polling && activeSim && activeSim.status === "running") {
            interval = setInterval(() => {
                fetchSimDetails(activeSim.id);
                fetchMessages(activeSim.id);
            }, 3000);
        }
        return () => clearInterval(interval);
    }, [polling, activeSim]);

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    const fetchSources = async () => {
        try {
            const data = await getDataSources(userId);
            setAvailableSources(data);
        } catch (err) {
            console.error("Error fetching sources", err);
        }
    };

    const fetchSimulations = async () => {
        try {
            const data = await getSimulations(userId);
            setSimulations(data);
        } catch (err) {
            console.error("Error fetching simulations", err);
        }
    };

    const fetchSimDetails = async (id: number) => {
        try {
            const data = await getSimulationDetails(id);
            setActiveSim(data);
            if (data.status !== "running") setPolling(false);
        } catch (err) {
            console.error("Error fetching sim details", err);
        }
    };

    const fetchMessages = async (id: number) => {
        try {
            const data = await getSimulationMessages(id);
            setMessages(data);
        } catch (err) {
            console.error("Error fetching messages", err);
        }
    };

    const handleStartSim = async () => {
        if (!title || !hypothesis) return;
        setLoading(true);
        try {
            const res = await createSimulation(userId, title, hypothesis, selectedSourceId, apiKey);
            setActiveSim(res);
            setMessages([]);
            setTitle("");
            setHypothesis("");
            setPolling(true);
            fetchSimulations();
        } catch (err: any) {
            alert(err.message || "Error al iniciar simulación");
        } finally {
            setLoading(false);
        }
    };

    const handleRetry = async () => {
        if (!activeSim) return;
        setLoading(true);
        try {
            await retrySimulation(activeSim.id);
            setPolling(true);
            fetchSimulations();
            fetchSimDetails(activeSim.id);
            setMessages([]);
        } catch (err: any) {
            alert(err.message || "Error al reintentar simulación");
        } finally {
            setLoading(false);
        }
    };

    const selectSimulation = (sim: any) => {
        setActiveSim(sim);
        fetchMessages(sim.id);
        if (sim.status === "running") setPolling(true);
        else setPolling(false);
    };

    return (
        <div className="flex-1 bg-black flex h-screen overflow-hidden border-l border-white/5">
            {/* Sidebar de Historial de Simulaciones */}
            <div className="w-80 border-r border-white/5 flex flex-col bg-[#050505]">
                <div className="p-6 border-b border-white/5 bg-white/[0.02]">
                    <div className="flex items-center gap-3 mb-2">
                        <Brain className="w-5 h-5 text-purple-500" />
                        <h2 className="text-xs font-black text-white uppercase tracking-[0.2em]">Ensayos del Futuro</h2>
                    </div>
                    <p className="text-[10px] text-gray-500 font-bold uppercase tracking-widest leading-relaxed">Motor de Inteligencia de Enjambre MiroFish Lite</p>
                </div>

                <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
                    {simulations.map((sim) => (
                        <button
                            key={sim.id}
                            onClick={() => selectSimulation(sim)}
                            className={`w-full text-left p-4 rounded-2xl border transition-all group ${
                                activeSim?.id === sim.id 
                                ? 'bg-purple-600/10 border-purple-500/40 text-white' 
                                : 'bg-white/[0.02] border-white/5 text-gray-400 hover:bg-white/[0.05]'
                            }`}
                        >
                            <div className="flex items-center justify-between mb-2">
                                <span className={`text-[8px] font-black px-2 py-0.5 rounded uppercase tracking-tighter ${
                                    sim.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                                    sim.status === 'running' ? 'bg-blue-500/20 text-blue-400 animate-pulse' :
                                    'bg-gray-500/20 text-gray-400'
                                }`}>
                                    {sim.status}
                                </span>
                                <Clock className="w-3 h-3 text-gray-600" />
                            </div>
                            <p className="text-xs font-bold truncate mb-1">{sim.title}</p>
                            <p className="text-[10px] text-gray-600 truncate">{sim.hypothesis}</p>
                        </button>
                    ))}
                </div>
                
                <div className="p-4 bg-white/[0.01] border-t border-white/5">
                    <button 
                        onClick={() => setActiveSim(null)}
                        className="w-full py-3 bg-purple-600 hover:bg-purple-500 rounded-xl text-white text-[10px] font-black uppercase tracking-widest transition-all flex items-center justify-center gap-2"
                    >
                        <Sparkles className="w-3.5 h-3.5" />
                        Nuevo Escenario
                    </button>
                </div>
            </div>

            {/* Area Principal */}
            <div className="flex-1 flex flex-col relative">
                {activeSim ? (
                    <div className="flex-1 flex flex-col overflow-hidden">
                        {/* Header de Simulación Activa */}
                        <header className="h-20 border-b border-white/5 bg-black/40 backdrop-blur-xl flex items-center justify-between px-8 shrink-0">
                            <div className="flex items-center gap-4">
                                <div className={`p-3 rounded-2xl ${
                                    activeSim.status === 'running' ? 'bg-blue-600/10 text-blue-400 animate-pulse' : 
                                    activeSim.status === 'error' ? 'bg-red-600/10 text-red-400' :
                                    'bg-green-600/10 text-green-400'
                                }`}>
                                    <Activity className="w-6 h-6" />
                                </div>
                                <div>
                                    <h3 className="text-sm font-black text-white uppercase tracking-widest">{activeSim.title}</h3>
                                    <div className="flex items-center gap-2 mt-1">
                                        <Shield className="w-3 h-3 text-gray-600" />
                                        <p className="text-[10px] text-gray-500 font-bold uppercase truncate max-w-md">{activeSim.hypothesis}</p>
                                    </div>
                                </div>
                            </div>
                            <div className="flex items-center gap-4">
                                {activeSim.status === 'error' && (
                                    <button 
                                        onClick={handleRetry}
                                        disabled={loading}
                                        className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-xl text-[10px] font-black uppercase tracking-widest transition-all"
                                    >
                                        <RefreshCcw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                                        Reintentar Simulación
                                    </button>
                                )}
                                <div className="text-right hidden sm:block">
                                    <p className="text-[9px] text-gray-600 font-black uppercase tracking-tighter">Estado del Enjambre</p>
                                    <p className={`text-[11px] font-bold uppercase tracking-widest ${
                                        activeSim.status === 'running' ? 'text-blue-400' : 
                                        activeSim.status === 'error' ? 'text-red-400' :
                                        'text-green-400'
                                    }`}>
                                        {activeSim.status === 'running' ? 'Sincronizando Mentes AI...' : 
                                         activeSim.status === 'error' ? 'Error en Inferencia' :
                                         'Futuro Consolidado'}
                                    </p>
                                </div>
                            </div>
                        </header>

                        <div className="flex-1 flex overflow-hidden">
                            {/* Feed de Discusión (El Swarm) */}
                            <div className="flex-1 flex flex-col bg-black border-r border-white/5 overflow-hidden">
                                <div className="p-4 bg-white/[0.02] border-b border-white/5 flex items-center justify-between shrink-0">
                                    <span className="text-[10px] font-black text-gray-500 uppercase tracking-widest flex items-center gap-2">
                                        <MessageSquare className="w-3.5 h-3.5" /> Debate en Tiempo Real
                                    </span>
                                    {activeSim.status === 'running' && (
                                        <div className="flex items-center gap-2">
                                            <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-ping" />
                                            <span className="text-[9px] font-bold text-blue-400 uppercase tracking-tighter">IA Pensando</span>
                                        </div>
                                    )}
                                </div>
                                
                                <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
                                    {messages.length === 0 && (
                                        <div className="h-full flex flex-col items-center justify-center text-center opacity-20">
                                            <Bot className="w-16 h-16 mb-4" />
                                            <p className="text-xs font-bold uppercase tracking-widest">Esperando primera señal...</p>
                                        </div>
                                    )}
                                    {messages.map((msg, idx) => (
                                        <div key={msg.id || idx} className="flex gap-4 animate-in fade-in slide-in-from-bottom-2">
                                            <div className={`shrink-0 w-10 h-10 rounded-xl flex items-center justify-center border ${
                                                msg.agent_role === 'Sistema' ? 'bg-gray-600/10 border-gray-600/30' : 'bg-purple-600/10 border-purple-500/30'
                                            }`}>
                                                {msg.agent_role === 'Sistema' ? <Shield className="w-5 h-5 text-gray-500" /> : <User className="w-5 h-5 text-purple-400" />}
                                            </div>
                                            <div className="flex-1">
                                                <div className="flex items-center gap-2 mb-1">
                                                    <span className="text-[11px] font-bold text-white tracking-tight">{msg.agent_name}</span>
                                                    <span className="text-[9px] font-black text-gray-600 uppercase bg-white/5 px-1.5 py-0.5 rounded tracking-tighter">{msg.agent_role}</span>
                                                    <span className="text-[8px] text-gray-700 font-bold ml-auto uppercase tracking-tighter">Ronda {msg.round}</span>
                                                </div>
                                                <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-4">
                                                    <p className="text-sm text-gray-300 leading-relaxed font-medium">{msg.content}</p>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                    <div ref={messagesEndRef} />
                                </div>
                            </div>

                            {/* Reporte Estratégico (Columna Derecha) */}
                            <div className="w-[450px] bg-[#050505] flex flex-col overflow-hidden">
                                <div className="p-4 bg-purple-600/10 border-b border-purple-500/20 shrink-0 flex items-center justify-between">
                                    <span className="text-[10px] font-black text-purple-400 uppercase tracking-widest flex items-center gap-2">
                                        <Shield className="w-3.5 h-3.5" /> Reporte de Trayectoria Futura
                                    </span>
                                    {activeSim.result_report && (
                                        <a 
                                            href={getSimulationPdfUrl(activeSim.id, userId)}
                                            download
                                            className="flex items-center gap-1.5 px-3 py-1.5 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-[9px] font-black uppercase tracking-widest transition-all shadow-lg shadow-purple-600/20"
                                        >
                                            <FileText className="w-3 h-3" />
                                            PDF
                                        </a>
                                    )}
                                </div>
                                <div className="flex-1 overflow-y-auto p-6 custom-scrollbar prose prose-invert prose-sm max-w-none">
                                    {activeSim.result_report ? (
                                        <ReactMarkdown 
                                            components={{
                                                h1: ({node, ...props}) => <h1 className="text-lg font-black text-white uppercase tracking-widest border-b border-white/10 pb-2 mb-6" {...props} />,
                                                h2: ({node, ...props}) => <h2 className="text-sm font-bold text-purple-400 uppercase tracking-widest mt-8 mb-4 flex items-center gap-2" {...props} />,
                                                table: ({node, ...props}) => <div className="overflow-x-auto my-6"><table className="w-full text-left border-collapse" {...props} /></div>,
                                                th: ({node, ...props}) => <th className="bg-white/5 p-2 text-[10px] font-black uppercase text-gray-500 border border-white/5" {...props} />,
                                                td: ({node, ...props}) => <td className="p-2 text-xs border border-white/5 text-gray-300" {...props} />,
                                                blockquote: ({node, ...props}) => <blockquote className="border-l-4 border-purple-600 bg-purple-600/5 p-4 rounded-r-xl italic" {...props} />,
                                            }}
                                        >
                                            {activeSim.result_report}
                                        </ReactMarkdown>
                                    ) : (
                                        <div className="h-full flex flex-col items-center justify-center text-center opacity-30">
                                            <Clock className="w-12 h-12 mb-4" />
                                            <p className="text-[10px] font-black uppercase tracking-widest">Generando análisis profundo...</p>
                                            <p className="text-[8px] text-gray-600 mt-2 uppercase">El motor Deep Think está evaluando las dinámicas del enjambre</p>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                ) : (
                    /* Pantalla de Creación de Escenario */
                    <div className="flex-1 flex flex-col items-center justify-center p-8 bg-black">
                        <div className="max-w-2xl w-full">
                            <div className="text-center mb-12">
                                <div className="inline-flex p-4 bg-purple-600/10 rounded-3xl mb-6">
                                    <Brain className="w-12 h-12 text-purple-500" />
                                </div>
                                <h2 className="text-3xl font-black text-white uppercase tracking-tight mb-4">Ensayo de Escenarios</h2>
                                <p className="text-gray-500 leading-relaxed">Configura un escenario hipotético y deja que el enjambre de IA simule las reacciones y el futuro probable basado en tus datos.</p>
                            </div>

                            <div className="space-y-6 bg-white/[0.02] border border-white/5 p-8 rounded-[40px] backdrop-blur-3xl shadow-2xl">
                                <div>
                                    <label className="text-[10px] font-black text-gray-600 uppercase tracking-widest mb-3 block">Título del Ensayo</label>
                                    <input 
                                        type="text" 
                                        value={title}
                                        onChange={(e) => setTitle(e.target.value)}
                                        placeholder="Ej: Estrategia de Precios 2026"
                                        className="w-full bg-black border border-white/10 rounded-2xl px-6 py-4 text-sm text-white focus:outline-none focus:border-purple-500/50 transition-all placeholder:text-gray-800"
                                    />
                                </div>

                                <div>
                                    <label className="text-[10px] font-black text-gray-600 uppercase tracking-widest mb-3 block">Hipótesis Estratégica (MiroFish Context)</label>
                                    <textarea 
                                        rows={4}
                                        value={hypothesis}
                                        onChange={(e) => setHypothesis(e.target.value)}
                                        placeholder="Define qué quieres probar. Ej: ¿Qué pasaría si aumentamos el precio un 15% mientras la competencia baja sus costos logísticos?"
                                        className="w-full bg-black border border-white/10 rounded-2xl px-6 py-4 text-sm text-white focus:outline-none focus:border-purple-500/50 transition-all placeholder:text-gray-800 resize-none"
                                    />
                                </div>

                                <div>
                                    <label className="text-[10px] font-black text-gray-600 uppercase tracking-widest mb-3 block">Fuente de Datos Base</label>
                                    <div className="grid grid-cols-2 gap-3">
                                        <select 
                                            value={selectedSourceId || ""}
                                            onChange={(e) => setSelectedSourceId(e.target.value ? Number(e.target.value) : undefined)}
                                            className="col-span-2 bg-black border border-white/10 rounded-2xl px-6 py-4 text-sm text-white focus:outline-none focus:border-purple-500/50 appearance-none cursor-pointer"
                                        >
                                            <option value="">Utilizar pool de datos actual (Recomendado)</option>
                                            {availableSources.map(s => (
                                                <option key={s.id} value={s.id}>{s.name} ({s.type})</option>
                                            ))}
                                        </select>
                                    </div>
                                </div>

                                <button 
                                    onClick={handleStartSim}
                                    disabled={loading || !title || !hypothesis}
                                    className="w-full py-5 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 disabled:hover:bg-purple-600 rounded-3xl text-white font-black uppercase tracking-[0.3em] transition-all flex items-center justify-center gap-3 shadow-xl shadow-purple-600/20"
                                >
                                    {loading ? (
                                        <Activity className="w-5 h-5 animate-spin" />
                                    ) : (
                                        <>
                                            <Play className="w-4 h-4 fill-current" />
                                            Iniciar Simulación de Enjambre
                                        </>
                                    )}
                                </button>
                                
                                <div className="flex items-center gap-4 pt-4 opacity-30 justify-center">
                                    <div className="flex items-center gap-2">
                                        <Shield className="w-3 h-3" />
                                        <span className="text-[8px] font-bold uppercase tracking-widest">
                                            {aiProvider === 'gemini' ? 'Gemini 3.1 Driven' : 
                                             aiProvider === 'mistral' ? 'Mistral Large Driven' : 
                                             'Enjambre Multimodelo (Dual)'}
                                        </span>
                                    </div>
                                    <div className="w-1 h-1 bg-gray-500 rounded-full" />
                                    <div className="flex items-center gap-2">
                                        <Sparkles className="w-3 h-3" />
                                        <span className="text-[8px] font-bold uppercase tracking-widest text-purple-400">MiroFish Protocol v2</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
