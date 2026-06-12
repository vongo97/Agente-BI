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
        <div className="max-w-2xl mx-auto space-y-6 py-6 lg:py-8">
            {/* Selector de Motor */}
            <div className="space-y-3">
                <label className="text-[10px] font-semibold text-[var(--bi-text-3)] uppercase tracking-widest">Motor de Inteligencia</label>
                <div className="grid grid-cols-3 gap-3">
                    {[
                        { id: 'gemini', label: 'Gemini 3.1', icon: <Sparkles className="w-3 h-3" /> },
                        { id: 'mistral', label: 'Mistral Large', icon: <Brain className="w-3 h-3" /> },
                        { id: 'hybrid', label: 'Híbrido (Dual)', icon: <Activity className="w-3 h-3" /> }
                    ].map((p) => (
                        <button
                            key={p.id}
                            onClick={() => setAiProvider(p.id as any)}
                            className={`flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg border text-[10px] font-semibold uppercase tracking-wider transition-all cursor-pointer ${
                                aiProvider === p.id 
                                ? 'bg-[var(--sim-accent-soft)] border-[var(--sim-accent)] text-[var(--bi-text-1)] ring-1 ring-[var(--sim-accent)] shadow-lg shadow-[var(--sim-accent-soft)]' 
                                : 'bg-[var(--bi-surface-1)] border-[var(--bi-border)] text-[var(--bi-text-2)] hover:border-[var(--bi-border-strong)]'
                            }`}
                        >
                            {p.icon} {p.label}
                        </button>
                    ))}
                </div>
            </div>

            <div className="space-y-3">
                <label className="text-[10px] font-semibold text-[var(--bi-text-3)] uppercase tracking-widest">Título del Escenario</label>
                <input 
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="Ej: Impacto de la Devaluación en el Sector Agro"
                    className="w-full bg-[var(--bi-surface-0)] border border-[var(--bi-border)] rounded-lg px-4 py-3 text-xs text-[var(--bi-text-1)] focus:outline-none focus:border-[var(--sim-border)] transition-all font-medium"
                />
            </div>
            <div className="space-y-3">
                <label className="text-[10px] font-semibold text-[var(--bi-text-3)] uppercase tracking-widest">Hipótesis a Debatir</label>
                <textarea 
                    value={hypothesis}
                    onChange={(e) => setHypothesis(e.target.value)}
                    placeholder="¿Qué pasaría si...? Define la trayectoria que quieres que los agentes analicen."
                    rows={4}
                    className="w-full bg-[var(--bi-surface-0)] border border-[var(--bi-border)] rounded-lg px-4 py-3 text-xs text-[var(--bi-text-1)] focus:outline-none focus:border-[var(--sim-border)] transition-all resize-none leading-relaxed"
                />
            </div>

            {/* Sugerencias de IA */}
            <div className="space-y-3">
                <div className="flex items-center justify-between">
                    <label className="text-[10px] font-semibold text-[var(--sim-accent)] uppercase tracking-widest flex items-center gap-2">
                        <Sparkles className="w-3 h-3" /> Escenarios Sugeridos
                    </label>
                    <button 
                        onClick={fetchSuggestions}
                        disabled={loadingSuggestions || selectedSources.size === 0}
                        className="text-[9px] font-semibold text-[var(--sim-accent)] bg-[var(--sim-accent-soft)] hover:bg-[var(--sim-accent)]/20 border border-[var(--sim-border)] px-3 py-1 rounded-full transition-all disabled:opacity-30 cursor-pointer"
                    >
                        {loadingSuggestions ? 'Generando...' : 'Obtener Sugerencias'}
                    </button>
                </div>
                
                {suggestions.length > 0 ? (
                    <div className="grid grid-cols-1 gap-3 animate-in fade-in duration-300">
                        {suggestions.map((sug, i) => (
                            <button 
                                key={i}
                                onClick={() => applySuggestion(sug)}
                                className="group text-left p-4 bg-[var(--sim-accent-soft)]/50 border border-[var(--sim-border)]/50 rounded-lg hover:border-[var(--sim-border)] hover:bg-[var(--sim-accent-soft)] transition-all cursor-pointer"
                            >
                                <div className="flex items-center justify-between mb-1">
                                    <span className="text-[10px] font-semibold text-[var(--sim-accent)] uppercase tracking-tight">{sug.title}</span>
                                    <ChevronRight className="w-3 h-3 text-[var(--sim-accent)] group-hover:translate-x-1 transition-transform" />
                                </div>
                                <p className="text-[11px] text-[var(--bi-text-2)] line-clamp-2 leading-relaxed">{sug.hypothesis}</p>
                            </button>
                        ))}
                    </div>
                ) : !loadingSuggestions && selectedSources.size > 0 && (
                    <p className="text-[9px] text-[var(--bi-text-3)] italic">Haz clic en &quot;Obtener Sugerencias&quot; para que la IA diseñe hipótesis basadas en tus archivos.</p>
                )}
            </div>

            {/* Contexto de Datos (Documentos) */}
            <div className="space-y-4 p-5 bg-[var(--sim-accent-soft)]/20 border border-[var(--sim-border)]/40 rounded-lg">
                <div className="flex items-center justify-between mb-1">
                    <label className="text-[10px] font-semibold text-[var(--bi-text-2)] uppercase tracking-widest flex items-center gap-2">
                        <FileText className="w-3.5 h-3.5 text-[var(--sim-accent)]" /> Selección de Contexto Factual
                    </label>
                    <span className="text-[9px] font-bold text-[var(--sim-accent)]/70 uppercase tracking-tighter">
                        {selectedSources.size} de {allHistoricalSources.length} Archivos
                    </span>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-48 overflow-y-auto pr-2 custom-scrollbar">
                    {allHistoricalSources.length > 0 ? (
                        allHistoricalSources.map((src) => {
                            const isSelected = selectedSources.has(src.id);
                            const isCurrentSession = dataSources.some(ds => ds.id === src.id);
                            return (
                                <button 
                                    key={src.id} 
                                    onClick={() => toggleSource(src.id)}
                                    className={`flex items-center justify-between gap-2 px-3.5 py-3 rounded-lg border transition-all text-left cursor-pointer ${
                                        isSelected 
                                        ? 'bg-[var(--sim-accent-soft)] border-[var(--sim-accent)] text-[var(--bi-text-1)]' 
                                        : 'bg-[var(--bi-canvas)] border-[var(--bi-border)] text-[var(--bi-text-3)] hover:border-[var(--bi-border-strong)]'
                                    }`}
                                >
                                    <div className="flex items-center gap-3">
                                        <div className={`w-2 h-2 rounded-full ${isSelected ? 'bg-[var(--sim-accent)] shadow-[0_0_8px_rgba(168,85,247,0.4)]' : 'bg-[var(--bi-border-strong)]'}`}></div>
                                        <div className="flex flex-col">
                                            <span className="text-[10px] font-semibold tracking-tight truncate max-w-[140px] text-[var(--bi-text-1)]">{src.name}</span>
                                            <span className="text-[8px] text-[var(--bi-text-3)] font-medium">
                                                {new Date(src.created_at).toLocaleDateString()}
                                            </span>
                                        </div>
                                    </div>
                                    {isCurrentSession && (
                                        <span className="text-[7px] font-bold bg-[var(--sim-accent-soft)] text-[var(--sim-accent)] border border-[var(--sim-border)] px-1.5 py-0.5 rounded uppercase tracking-wider flex-shrink-0">Activa</span>
                                    )}
                                </button>
                            );
                        })
                    ) : (
                        <div className="col-span-full py-8 text-center border border-dashed border-[var(--bi-border)] rounded-lg bg-[var(--bi-canvas)]/30">
                            <p className="text-[10px] text-[var(--bi-text-3)] italic">No hay documentos en tu biblioteca. Sube archivos en el Chat para comenzar a construir tu historial.</p>
                        </div>
                    )}
                </div>
            </div>

            <button 
                onClick={handleStart}
                disabled={loading || !title.trim() || !hypothesis.trim() || selectedSources.size === 0}
                className={`w-full py-4 rounded-lg font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-2 cursor-pointer ${
                    (!loading && title.trim() && hypothesis.trim() && selectedSources.size > 0)
                    ? 'bg-[var(--sim-accent)] hover:bg-[var(--sim-accent-hover)] text-white shadow-lg shadow-[var(--sim-accent-soft)]' 
                    : 'bg-[var(--bi-surface-3)] text-[var(--bi-text-3)] cursor-not-allowed opacity-50'
                }`}
            >
                {loading ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                    <>
                        <Sparkles className="w-4 h-4" />
                        {dataSources.length > 0 ? "Iniciar Debate de Agentes" : "Sube documentos para simular"}
                    </>
                )}
            </button>
            
            {dataSources.length === 0 && (
                <div className="p-4 bg-[var(--bi-amber-dim)] border border-[var(--bi-amber)]/20 rounded-lg flex items-start gap-3">
                    <AlertCircle className="w-4 h-4 text-[var(--bi-amber)] mt-0.5" />
                    <div>
                        <p className="text-[10px] font-semibold text-[var(--bi-amber)] uppercase tracking-wider mb-0.5">Simulador Bloqueado</p>
                        <p className="text-[9px] text-[var(--bi-text-2)] leading-relaxed font-medium">
                            Para garantizar que la simulación sea realista y basada en tu negocio, debes cargar al menos un archivo (CSV, Excel o SQL) en la pestaña de Chat antes de comenzar.
                        </p>
                    </div>
                </div>
            )}
        </div>
    );
}
