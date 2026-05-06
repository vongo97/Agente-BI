'use client';

import { useState, useEffect } from "react";
import { Brain, Sparkles, Send, Loader2, History, ChevronRight, Download, FileText, Activity, AlertCircle, PlusCircle } from "lucide-react";
import { useDashboard } from "@/context/DashboardContext";
import { createSimulation, getSimulations, getSimulationDetails, getSimulationMessages, getSimulationPdfUrl, getDataSources, getSimulationSuggestions } from "@/lib/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function SimulationSandbox() {
    const { apiKey, mistralKey, aiProvider, setAiProvider, userId, dataSources } = useDashboard();
    const [title, setTitle] = useState("");
    const [hypothesis, setHypothesis] = useState("");
    const [loading, setLoading] = useState(false);
    const [simulations, setSimulations] = useState<any[]>([]);
    const [activeSim, setActiveSim] = useState<any>(null);
    const [messages, setMessages] = useState<any[]>([]);
    const [polling, setPolling] = useState(false);
    const [selectedSources, setSelectedSources] = useState<Set<number>>(new Set());
    const [allHistoricalSources, setAllHistoricalSources] = useState<any[]>([]);
    const [suggestions, setSuggestions] = useState<any[]>([]);
    const [loadingSuggestions, setLoadingSuggestions] = useState(false);

    useEffect(() => {
        fetchSimulations();
        fetchHistoricalSources();
    }, [userId]);

    const fetchHistoricalSources = async () => {
        try {
            const data = await getDataSources(userId);
            setAllHistoricalSources(data);
        } catch (e) {
            console.error("Error fetching historical sources", e);
        }
    };

    useEffect(() => {
        if (dataSources.length > 0) {
            setSelectedSources(new Set(dataSources.map(ds => ds.id).filter((id): id is number => id !== undefined)));
        }
    }, [dataSources]);

    const toggleSource = (id: number) => {
        const next = new Set(selectedSources);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        setSelectedSources(next);
        setSuggestions([]);
    };

    const fetchSuggestions = async () => {
        const currentUserId = userId || localStorage.getItem("userId") || "invitado@agente-bi.local";
        if (selectedSources.size === 0 || (!apiKey && !mistralKey)) return;
        setLoadingSuggestions(true);
        try {
            const ids = Array.from(selectedSources);
            const data = await getSimulationSuggestions(currentUserId, ids, apiKey, aiProvider, mistralKey);
            setSuggestions(data);
        } catch (err) {
            console.error("Error fetching suggestions", err);
        } finally {
            setLoadingSuggestions(false);
        }
    };

    const applySuggestion = (sug: any) => {
        setTitle(sug.title);
        setHypothesis(sug.hypothesis);
    };

    useEffect(() => {
        let interval: any;
        if (polling && activeSim?.id) {
            interval = setInterval(async () => {
                const details = await getSimulationDetails(activeSim.id);
                const msgs = await getSimulationMessages(activeSim.id);
                setMessages(msgs);
                setActiveSim(details); // Actualizar siempre para ver cambios de ronda
                if (details.status === 'completed' || details.status === 'error') {
                    setPolling(false);
                    fetchSimulations();
                }
            }, 2000);
        }
        return () => clearInterval(interval);
    }, [polling, activeSim]);

    const fetchSimulations = async () => {
        try {
            const data = await getSimulations(userId);
            setSimulations(data);
        } catch (err) {
            console.error("Error fetching simulations", err);
        }
    };

    const handleStart = async () => {
        const currentUserId = userId || localStorage.getItem("userId") || "invitado@agente-bi.local";
        const currentApiKey = aiProvider === 'mistral' ? mistralKey : apiKey;
        
        if (!currentApiKey && aiProvider !== 'hybrid') {
            alert("Asegúrate de tener una API Key para el motor seleccionado.");
            return;
        }
        if (!title || !hypothesis) {
            alert("Completa el título y la hipótesis.");
            return;
        }
        if (selectedSources.size === 0) {
            alert("Selecciona al menos un archivo.");
            return;
        }
        setLoading(true);
        try {
            const ids = Array.from(selectedSources);
            const res = await createSimulation(
                currentUserId, 
                title, 
                hypothesis, 
                undefined, 
                apiKey, 
                ids as any, 
                aiProvider, 
                mistralKey
            );
            const initialDetails = await getSimulationDetails(res.simulation_id);
            setActiveSim(initialDetails);
            setMessages([]);
            setPolling(true);
            setTitle("");
            setHypothesis("");
        } catch (err) {
            alert("Error al iniciar simulación");
        } finally {
            setLoading(false);
        }
    };

    const loadSim = async (sim: any) => {
        setActiveSim(sim);
        const msgs = await getSimulationMessages(sim.id);
        setMessages(msgs);
        setPolling(sim.status === 'running');
    };

    return (
        <div className="flex h-full bg-[var(--bg-primary)] overflow-hidden">
            {/* Sidebar de Historial */}
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

            {/* Panel Central */}
            <div className="flex-1 flex flex-col overflow-hidden">
                <header className="p-8 border-b border-[var(--border-color)] bg-gradient-to-r from-purple-900/10 to-transparent">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <div className="p-3 bg-purple-600 rounded-2xl shadow-xl shadow-purple-600/20">
                                <Brain className="w-6 h-6 text-white" />
                            </div>
                            <div>
                                <h1 className="text-2xl font-black text-white tracking-tight italic">Ensayos del Futuro</h1>
                                <p className="text-[10px] text-purple-400 font-black uppercase tracking-widest">Inteligencia de Enjambre • Mirofish Lite</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-3">
                            <button
                                onClick={() => {
                                    setActiveSim(null);
                                    setTitle("");
                                    setHypothesis("");
                                }}
                                className="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 text-gray-300 rounded-xl text-[10px] font-black uppercase tracking-widest border border-white/5 transition-all"
                            >
                                <PlusCircle className="w-3.5 h-3.5" /> Nuevo Ensayo
                            </button>

                            {activeSim?.status === 'completed' && (
                                <a 
                                    href={getSimulationPdfUrl(activeSim.id, userId)} 
                                    target="_blank"
                                    className="flex items-center gap-2 px-6 py-2.5 bg-purple-600 hover:bg-purple-500 text-white rounded-xl text-[10px] font-black uppercase tracking-widest shadow-xl shadow-purple-600/20 transition-all"
                                >
                                    <Download className="w-3.5 h-3.5" /> Exportar Veredicto
                                </a>
                            )}
                        </div>
                    </div>
                </header>

                <div className="flex-1 overflow-y-auto p-8 space-y-12 custom-scrollbar">
                    {!activeSim && (
                        <div className="max-w-2xl mx-auto space-y-8 py-12">
                            {/* Selector de Motor */}
                            <div className="space-y-4">
                                <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Motor de Inteligencia</label>
                                <div className="grid grid-cols-3 gap-3">
                                    {[
                                        { id: 'gemini', label: 'Gemini 3.1', icon: <Sparkles className="w-3 h-3" /> },
                                        { id: 'mistral', label: 'Mistral Large', icon: <Brain className="w-3 h-3" /> },
                                        { id: 'hybrid', label: 'Híbrido (Dual)', icon: <Activity className="w-3 h-3" /> }
                                    ].map((p) => (
                                        <button
                                            key={p.id}
                                            onClick={() => setAiProvider(p.id as any)}
                                            className={`flex items-center justify-center gap-2 px-4 py-3 rounded-xl border text-[10px] font-black uppercase transition-all ${
                                                aiProvider === p.id 
                                                ? 'bg-purple-600 border-purple-500 text-white shadow-lg shadow-purple-600/20' 
                                                : 'bg-white/[0.02] border-white/5 text-gray-500 hover:border-white/10'
                                            }`}
                                        >
                                            {p.icon} {p.label}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <div className="space-y-4">
                                <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Título del Escenario</label>
                                <input 
                                    value={title}
                                    onChange={(e) => setTitle(e.target.value)}
                                    placeholder="Ej: Impacto de la Devaluación en el Sector Agro"
                                    className="w-full bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-2xl px-6 py-4 text-white focus:outline-none focus:border-purple-500/50 transition-all"
                                />
                            </div>
                            <div className="space-y-4">
                                <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Hipótesis a Debatir</label>
                                <textarea 
                                    value={hypothesis}
                                    onChange={(e) => setHypothesis(e.target.value)}
                                    placeholder="¿Qué pasaría si...? Define la trayectoria que quieres que los agentes analicen."
                                    rows={4}
                                    className="w-full bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-2xl px-6 py-4 text-white focus:outline-none focus:border-purple-500/50 transition-all resize-none"
                                />
                            </div>

                            {/* Sugerencias de IA */}
                            <div className="space-y-4">
                                <div className="flex items-center justify-between">
                                    <label className="text-[10px] font-black text-purple-400 uppercase tracking-widest flex items-center gap-2">
                                        <Sparkles className="w-3 h-3" /> Escenarios Sugeridos
                                    </label>
                                    <button 
                                        onClick={fetchSuggestions}
                                        disabled={loadingSuggestions || selectedSources.size === 0}
                                        className="text-[9px] font-black text-white bg-purple-600/40 hover:bg-purple-600/60 px-3 py-1 rounded-full transition-all disabled:opacity-30"
                                    >
                                        {loadingSuggestions ? 'Generando...' : 'Obtener Sugerencias'}
                                    </button>
                                </div>
                                
                                {suggestions.length > 0 ? (
                                    <div className="grid grid-cols-1 gap-3">
                                        {suggestions.map((sug, i) => (
                                            <button 
                                                key={i}
                                                onClick={() => applySuggestion(sug)}
                                                className="group text-left p-4 bg-purple-900/10 border border-purple-500/10 rounded-2xl hover:border-purple-500/30 hover:bg-purple-900/20 transition-all"
                                            >
                                                <div className="flex items-center justify-between mb-1">
                                                    <span className="text-[10px] font-black text-purple-300 uppercase tracking-tight">{sug.title}</span>
                                                    <ChevronRight className="w-3 h-3 text-purple-500 group-hover:translate-x-1 transition-transform" />
                                                </div>
                                                <p className="text-[11px] text-gray-400 line-clamp-2 leading-relaxed">{sug.hypothesis}</p>
                                            </button>
                                        ))}
                                    </div>
                                ) : !loadingSuggestions && selectedSources.size > 0 && (
                                    <p className="text-[9px] text-gray-600 italic">Haz clic en "Obtener Sugerencias" para que la IA diseñe hipótesis basadas en tus archivos.</p>
                                )}
                            </div>

                            {/* Contexto de Datos (Documentos) */}
                            <div className="space-y-4 p-6 bg-purple-600/5 border border-purple-500/10 rounded-2xl">
                                <div className="flex items-center justify-between mb-2">
                                    <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest flex items-center gap-2">
                                        <FileText className="w-3 h-3 text-purple-400" /> Selección de Contexto Factual
                                    </label>
                                    <span className="text-[9px] font-bold text-purple-500/50 uppercase tracking-tighter">
                                        {selectedSources.size} de {allHistoricalSources.length} Archivos Disponibles
                                    </span>
                                </div>
                                
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-48 overflow-y-auto pr-2 custom-scrollbar">
                                    {allHistoricalSources.length > 0 ? (
                                        allHistoricalSources.map((src, i) => {
                                            const isSelected = selectedSources.has(src.id);
                                            const isCurrentSession = dataSources.some(ds => ds.id === src.id);
                                            return (
                                                <button 
                                                    key={src.id} 
                                                    onClick={() => toggleSource(src.id)}
                                                    className={`flex items-center justify-between gap-2 px-4 py-3 rounded-xl border transition-all text-left ${
                                                        isSelected 
                                                        ? 'bg-purple-600/20 border-purple-500/50 text-white' 
                                                        : 'bg-black/20 border-white/5 text-gray-600 grayscale opacity-60 hover:opacity-100 shadow-inner'
                                                    }`}
                                                >
                                                    <div className="flex items-center gap-3">
                                                        <div className={`w-2 h-2 rounded-full shadow-[0_0_8px_rgba(168,85,247,0.5)] ${isSelected ? 'bg-purple-500' : 'bg-gray-700'}`}></div>
                                                        <div className="flex flex-col">
                                                            <span className="text-[10px] font-bold tracking-tight truncate max-w-[150px]">{src.name}</span>
                                                            <span className="text-[8px] text-gray-500 font-medium">
                                                                {new Date(src.created_at).toLocaleDateString()}
                                                            </span>
                                                        </div>
                                                    </div>
                                                    {isCurrentSession && (
                                                        <span className="text-[7px] font-black bg-purple-500/20 text-purple-400 px-1.5 py-0.5 rounded uppercase tracking-tighter">Sesión Activa</span>
                                                    )}
                                                </button>
                                            );
                                        })
                                    ) : (
                                        <div className="col-span-full py-8 text-center border border-dashed border-white/5 rounded-2xl bg-black/10">
                                            <p className="text-[10px] text-gray-500 italic">No hay documentos en tu biblioteca. Sube archivos en el Chat para comenzar a construir tu historial.</p>
                                        </div>
                                    )}
                                </div>
                                {allHistoricalSources.length > 0 && (
                                    <p className="text-[9px] text-gray-600 mt-2 italic">
                                        * Los archivos marcados como "Sesión Activa" ya están en memoria. Los históricos se cargarán automáticamente para el debate.
                                    </p>
                                )}
                            </div>
                            <button 
                                onClick={handleStart}
                                disabled={loading || !title.trim() || !hypothesis.trim() || selectedSources.size === 0}
                                className={`w-full py-5 rounded-2xl font-black uppercase tracking-[0.2em] shadow-2xl transition-all flex items-center justify-center gap-3 ${
                                    (!loading && title.trim() && hypothesis.trim() && selectedSources.size > 0)
                                    ? 'bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white shadow-purple-600/20' 
                                    : 'bg-gray-800 text-gray-500 cursor-not-allowed opacity-50 shadow-none'
                                }`}
                            >
                                {loading ? (
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                ) : (
                                    <>
                                        <Sparkles className="w-5 h-5" />
                                        {dataSources.length > 0 ? "Iniciar Debate de Agentes" : "Sube documentos para simular"}
                                    </>
                                )}
                            </button>
                            
                            {dataSources.length === 0 && (
                                <div className="p-4 bg-amber-500/5 border border-amber-500/20 rounded-2xl flex items-start gap-3">
                                    <AlertCircle className="w-4 h-4 text-amber-500 mt-0.5" />
                                    <div>
                                        <p className="text-[10px] font-black text-amber-500 uppercase tracking-widest mb-1">Simulador Bloqueado</p>
                                        <p className="text-[9px] text-amber-500/60 leading-relaxed font-medium">
                                            Para garantizar que la simulación sea realista y basada en tu negocio, debes cargar al menos un archivo (CSV, Excel o SQL) en la pestaña de Chat antes de comenzar.
                                        </p>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                    {activeSim && (
                        <div className="flex flex-col h-full">
                            <div className="grid grid-cols-12 gap-8 h-full">
                                {/* Columna Izquierda: Debate (8/12) */}
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
                                                <div className="text-sm text-gray-300 leading-relaxed font-medium">
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

                                {/* Columna Derecha: Reporte (5/12) - Sticky */}
                                <div className="col-span-12 lg:col-span-5 h-fit lg:sticky lg:top-0">
                                    {activeSim.result_report ? (
                                        <div className="bg-gradient-to-br from-purple-900/20 to-indigo-900/10 border border-purple-500/20 rounded-3xl p-8 shadow-2xl shadow-purple-900/20 animate-in fade-in slide-in-from-right-8 duration-700">
                                            <div className="flex items-center justify-between mb-8">
                                                <div className="flex items-center gap-3">
                                                    <div className="p-2 bg-purple-500/20 rounded-lg">
                                                        <Activity className="w-4 h-4 text-purple-400" />
                                                    </div>
                                                    <h2 className="text-[10px] font-black text-purple-400 uppercase tracking-[0.3em]">Veredicto Estratégico</h2>
                                                </div>
                                                <a 
                                                    href={getSimulationPdfUrl(activeSim.id, userId)} 
                                                    target="_blank"
                                                    className="p-2 hover:bg-white/5 rounded-lg text-purple-400 transition-all"
                                                    title="Descargar PDF"
                                                >
                                                    <Download className="w-4 h-4" />
                                                </a>
                                            </div>
                                            <div className="markdown-content prose prose-invert prose-sm prose-purple max-w-none">
                                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                    {activeSim.result_report}
                                                </ReactMarkdown>
                                            </div>
                                            
                                            <div className="mt-8 pt-8 border-t border-purple-500/10 flex items-center justify-between">
                                                <div className="flex flex-col">
                                                    <span className="text-[8px] text-gray-500 font-black uppercase tracking-widest">Motor Utilizado</span>
                                                    <span className="text-[10px] text-purple-300 font-bold uppercase tracking-tight">{activeSim.provider}</span>
                                                </div>
                                                <div className="flex flex-col items-end">
                                                    <span className="text-[8px] text-gray-500 font-black uppercase tracking-widest">Estado</span>
                                                    <span className="text-[10px] text-green-400 font-bold uppercase tracking-tight">Consolidado</span>
                                                </div>
                                            </div>
                                        </div>
                                    ) : polling ? (
                                        <div className="bg-white/[0.02] border border-dashed border-white/10 rounded-3xl p-12 text-center space-y-4">
                                            <Loader2 className="w-8 h-8 text-white/10 animate-spin mx-auto" />
                                            <p className="text-[10px] font-black text-gray-500 uppercase tracking-[0.2em]">Esperando Síntesis Final</p>
                                            <p className="text-[9px] text-gray-600 max-w-[200px] mx-auto italic">El estratega está procesando las 3 rondas de debate para emitir el veredicto final.</p>
                                        </div>
                                    ) : null}
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
