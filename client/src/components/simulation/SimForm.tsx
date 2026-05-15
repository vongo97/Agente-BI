import { Sparkles, Brain, Activity, ChevronRight, FileText, AlertCircle, Loader2 } from "lucide-react";

interface SimFormProps {
    aiProvider: string;
    setAiProvider: (p: any) => void;
    title: string;
    setTitle: (t: string) => void;
    hypothesis: string;
    setHypothesis: (h: string) => void;
    suggestions: any[];
    fetchSuggestions: () => void;
    loadingSuggestions: boolean;
    applySuggestion: (s: any) => void;
    allHistoricalSources: any[];
    selectedSources: Set<number>;
    toggleSource: (id: number) => void;
    dataSources: any[];
    handleStart: () => void;
    loading: boolean;
}

export function SimForm({
    aiProvider, setAiProvider, title, setTitle, hypothesis, setHypothesis,
    suggestions, fetchSuggestions, loadingSuggestions, applySuggestion,
    allHistoricalSources, selectedSources, toggleSource, dataSources,
    handleStart, loading
}: SimFormProps) {
    return (
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
    );
}
