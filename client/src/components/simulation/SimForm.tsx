import { Sparkles, Brain, Activity, ChevronRight, FileText, AlertCircle, Loader2, Zap, Layers, Cpu } from "lucide-react";
import { DataSource } from "@/types/shared";

interface SimFormProps {
    aiProvider: string;
    setAiProvider: (p: 'gemini' | 'mistral' | 'groq') => void;
    title: string;
    setTitle: (t: string) => void;
    hypothesis: string;
    setHypothesis: (h: string) => void;
    suggestions: { title: string; hypothesis: string }[];
    fetchSuggestions: () => void;
    loadingSuggestions: boolean;
    applySuggestion: (s: { title: string; hypothesis: string }) => void;
    allHistoricalSources: DataSource[];
    selectedSources: Set<number>;
    toggleSource: (id: number) => void;
    dataSources: DataSource[];
    handleStart: () => void;
    loading: boolean;
    numRounds: number;
    setNumRounds: (r: number) => void;
}

export function SimForm({
    aiProvider, setAiProvider, title, setTitle, hypothesis, setHypothesis,
    suggestions, fetchSuggestions, loadingSuggestions, applySuggestion,
    allHistoricalSources, selectedSources, toggleSource, dataSources,
    handleStart, loading, numRounds, setNumRounds
}: SimFormProps) {
    return (
        <div className="max-w-6xl mx-auto py-2 lg:py-4">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
                
                {/* COLUMNA IZQUIERDA: Configuración del Debate */}
                <div className="lg:col-span-7 space-y-6 bg-[var(--bi-surface-0)] border border-[var(--bi-border)] rounded-xl p-6 lg:p-8 shadow-xl">
                    <div className="pb-4 border-b border-[var(--bi-border)]">
                        <h2 className="text-xs font-bold text-[var(--module-simulation-accent)] uppercase tracking-wider flex items-center gap-2">
                            <Brain className="w-4 h-4" /> Configuración de Escenario
                        </h2>
                        <p className="text-[10px] text-[var(--bi-text-3)] uppercase tracking-widest mt-1">Define el contexto intelectual del debate</p>
                    </div>

                    {/* Selector de Motor */}
                    <div className="space-y-3">
                        <label className="text-[10px] font-semibold text-[var(--bi-text-2)] uppercase tracking-widest flex items-center gap-1.5">
                            Motor de Inteligencia
                        </label>
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                            {[
                                { id: 'gemini', label: 'Gemini 3.1', desc: 'Rápido y analítico', icon: <Sparkles className="w-3.5 h-3.5" /> },
                                { id: 'mistral', label: 'Mistral Large', desc: 'Precisión semántica', icon: <Brain className="w-3.5 h-3.5" /> },
                                { id: 'groq', label: 'Groq Llama 3.3', desc: 'Debate ultraveloz', icon: <Sparkles className="w-3.5 h-3.5" /> }
                            ].map((p) => (
                                <button
                                    key={p.id}
                                    type="button"
                                    onClick={() => setAiProvider(p.id as 'gemini' | 'mistral' | 'groq')}
                                    className={`flex flex-col items-center justify-center gap-1.5 px-3 py-3 rounded-lg border text-center transition-all duration-200 cursor-pointer ${
                                        aiProvider === p.id 
                                        ? 'bg-[var(--module-simulation-accent-soft)] border-[var(--module-simulation-accent)] text-[var(--bi-text-1)] ring-1 ring-[var(--module-simulation-accent)] shadow-lg shadow-[rgba(168,85,247,0.15)]' 
                                        : 'bg-[var(--bi-surface-1)] border-[var(--bi-border)] text-[var(--bi-text-2)] hover:border-[var(--bi-border-strong)] hover:bg-[var(--bi-surface-2)]'
                                    }`}
                                >
                                    <div className={`flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider ${aiProvider === p.id ? 'text-[var(--module-simulation-accent)]' : ''}`}>
                                        {p.icon} {p.label}
                                    </div>
                                    <span className="text-[8px] text-[var(--bi-text-3)] font-medium">{p.desc}</span>
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Selector de Rondas */}
                    <div className="space-y-3">
                        <label className="text-[10px] font-semibold text-[var(--bi-text-2)] uppercase tracking-widest">
                            Profundidad del Análisis
                        </label>
                        <div className="grid grid-cols-3 gap-3">
                            {[
                                { id: 2, label: 'Rápido', desc: '2 Rondas express', icon: <Zap className="w-3.5 h-3.5" /> },
                                { id: 3, label: 'Estándar', desc: '3 Rondas balanceadas', icon: <Layers className="w-3.5 h-3.5" /> },
                                { id: 5, label: 'Profundo', desc: '5 Rondas exhaustivas', icon: <Cpu className="w-3.5 h-3.5" /> }
                            ].map((r) => (
                                <button
                                    key={r.id}
                                    type="button"
                                    onClick={() => setNumRounds(r.id)}
                                    className={`flex flex-col items-center justify-center gap-1.5 px-3 py-3 rounded-lg border text-center transition-all duration-200 cursor-pointer ${
                                        numRounds === r.id 
                                        ? 'bg-[var(--module-simulation-accent-soft)] border-[var(--module-simulation-accent)] text-[var(--bi-text-1)] ring-1 ring-[var(--module-simulation-accent)] shadow-lg shadow-[rgba(168,85,247,0.15)]' 
                                        : 'bg-[var(--bi-surface-1)] border-[var(--bi-border)] text-[var(--bi-text-2)] hover:border-[var(--bi-border-strong)] hover:bg-[var(--bi-surface-2)]'
                                    }`}
                                >
                                    <div className={`flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider ${numRounds === r.id ? 'text-[var(--module-simulation-accent)]' : ''}`}>
                                        {r.icon} {r.label}
                                    </div>
                                    <span className="text-[8px] text-[var(--bi-text-3)] font-medium">{r.desc}</span>
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Título del Escenario */}
                    <div className="space-y-3">
                        <label className="text-[10px] font-semibold text-[var(--bi-text-2)] uppercase tracking-widest">Título del Ensayo</label>
                        <input 
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            placeholder="Ej: Impacto de la Devaluación en el Sector Agro"
                            className="w-full bg-[var(--bi-surface-1)] border border-[var(--bi-border)] rounded-lg px-4 py-3 text-xs text-[var(--bi-text-1)] focus:outline-none focus:border-[var(--module-simulation-accent)] focus:ring-1 focus:ring-[var(--module-simulation-accent)] transition-all font-medium placeholder-[var(--bi-text-3)] focus:shadow-[0_0_12px_rgba(168,85,247,0.1)]"
                        />
                    </div>

                    {/* Hipótesis */}
                    <div className="space-y-3">
                        <label className="text-[10px] font-semibold text-[var(--bi-text-2)] uppercase tracking-widest">Hipótesis a Debatir (Trayectoria)</label>
                        <textarea 
                            value={hypothesis}
                            onChange={(e) => setHypothesis(e.target.value)}
                            placeholder="¿Qué pasaría si...? Define el evento hipotético que quieres que los agentes confronten analíticamente."
                            rows={5}
                            className="w-full bg-[var(--bi-surface-1)] border border-[var(--bi-border)] rounded-lg px-4 py-3 text-xs text-[var(--bi-text-1)] focus:outline-none focus:border-[var(--module-simulation-accent)] focus:ring-1 focus:ring-[var(--module-simulation-accent)] transition-all resize-none leading-relaxed placeholder-[var(--bi-text-3)] focus:shadow-[0_0_12px_rgba(168,85,247,0.1)]"
                        />
                    </div>
                </div>

                {/* COLUMNA DERECHA: Datos de Contexto y Sugerencias */}
                <div className="lg:col-span-5 space-y-6">
                    
                    {/* Contexto Factual (Documentos) */}
                    <div className="bg-[var(--bi-surface-0)] border border-[var(--bi-border)] rounded-xl p-6 shadow-xl space-y-4">
                        <div className="flex items-center justify-between pb-3 border-b border-[var(--bi-border)]">
                            <label className="text-xs font-bold text-[var(--bi-text-1)] uppercase tracking-wider flex items-center gap-2">
                                <FileText className="w-4 h-4 text-[var(--module-simulation-accent)]" /> Cimientos Factuales
                            </label>
                            <span className="text-[8px] font-bold bg-[var(--module-simulation-accent-soft)] text-[var(--module-simulation-accent)] px-2 py-0.5 rounded border border-[var(--module-simulation-border)] uppercase tracking-wider flex-shrink-0">
                                {selectedSources.size} Seleccionado{selectedSources.size !== 1 && 's'}
                            </span>
                        </div>
                        
                        <div className="space-y-2.5 max-h-48 overflow-y-auto pr-1 custom-scrollbar">
                            {allHistoricalSources.length > 0 ? (
                                allHistoricalSources.map((src) => {
                                    const isSelected = src.id !== undefined && selectedSources.has(src.id);
                                    const isCurrentSession = dataSources.some(ds => ds.id === src.id);
                                    return (
                                        <button 
                                            key={src.id} 
                                            type="button"
                                            onClick={() => src.id !== undefined && toggleSource(src.id)}
                                            className={`w-full flex items-center justify-between gap-3 px-3.5 py-3 rounded-lg border transition-all duration-200 text-left cursor-pointer ${
                                                isSelected 
                                                ? 'bg-[var(--module-simulation-accent-soft)] border-[var(--module-simulation-accent)] text-[var(--bi-text-1)]' 
                                                : 'bg-[var(--bi-surface-1)] border-[var(--bi-border)] text-[var(--bi-text-3)] hover:border-[var(--bi-border-strong)] hover:bg-[var(--bi-surface-2)]'
                                            }`}
                                        >
                                            <div className="flex items-center gap-3 truncate">
                                                <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 border transition-all ${
                                                    isSelected 
                                                    ? 'bg-[var(--module-simulation-accent)] border-[var(--module-simulation-accent)] shadow-[0_0_8px_rgba(168,85,247,0.5)]' 
                                                    : 'border-[var(--bi-text-3)] bg-transparent'
                                                }`} />
                                                <div className="flex flex-col truncate">
                                                    <span className="text-[10px] font-bold tracking-tight truncate text-[var(--bi-text-1)]">{src.name}</span>
                                                    <span className="text-[8px] text-[var(--bi-text-3)] font-semibold uppercase tracking-wider mt-0.5">
                                                        {src.created_at ? new Date(src.created_at).toLocaleDateString() : ""}
                                                    </span>
                                                </div>
                                            </div>
                                            {isCurrentSession && (
                                                <span className="text-[7px] font-bold bg-[var(--bi-teal-dim)] text-[var(--bi-teal)] border border-[var(--bi-teal-border)] px-1.5 py-0.5 rounded uppercase tracking-wider flex-shrink-0">Activo</span>
                                            )}
                                        </button>
                                    );
                                })
                            ) : (
                                <div className="py-8 text-center border border-dashed border-[var(--bi-border)] rounded-lg bg-[var(--bi-surface-1)]/30">
                                    <p className="text-[10px] text-[var(--bi-text-3)] italic">No hay documentos en tu biblioteca. Sube archivos en el Chat para comenzar a simular.</p>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Sugerencias de IA */}
                    <div className="bg-[var(--bi-surface-0)] border border-[var(--bi-border)] rounded-xl p-6 shadow-xl space-y-4">
                        <div className="flex items-center justify-between pb-3 border-b border-[var(--bi-border)]">
                            <label className="text-xs font-bold text-[var(--bi-text-1)] uppercase tracking-wider flex items-center gap-2">
                                <Sparkles className="w-4 h-4 text-[var(--module-simulation-accent)]" /> Escenarios Sugeridos
                            </label>
                            <button 
                                type="button"
                                onClick={fetchSuggestions}
                                disabled={loadingSuggestions || selectedSources.size === 0}
                                className="text-[9px] font-bold text-[var(--module-simulation-accent)] bg-[var(--module-simulation-accent-soft)] hover:bg-[var(--module-simulation-accent)]/20 border border-[var(--module-simulation-border)] px-3 py-1 rounded-full transition-all disabled:opacity-30 cursor-pointer"
                            >
                                {loadingSuggestions ? 'Generando...' : 'Obtener Sugerencias'}
                            </button>
                        </div>
                        
                        {suggestions.length > 0 ? (
                            <div className="space-y-3 max-h-56 overflow-y-auto pr-1 custom-scrollbar animate-in fade-in duration-300">
                                {suggestions.map((sug, i) => (
                                    <button 
                                        key={i}
                                        type="button"
                                        onClick={() => applySuggestion(sug)}
                                        className="w-full text-left p-3.5 bg-[var(--module-simulation-accent-soft)]/20 border border-[var(--module-simulation-border)]/40 rounded-lg hover:border-[var(--module-simulation-accent)] hover:bg-[var(--module-simulation-accent-soft)]/45 transition-all duration-200 cursor-pointer group flex flex-col gap-1"
                                    >
                                        <div className="flex items-center justify-between w-full">
                                            <span className="text-[10px] font-bold text-[var(--module-simulation-accent)] uppercase tracking-wide truncate max-w-[90%]">{sug.title}</span>
                                            <ChevronRight className="w-3.5 h-3.5 text-[var(--module-simulation-accent)] group-hover:translate-x-1 transition-transform flex-shrink-0" />
                                        </div>
                                        <p className="text-[11px] text-[var(--bi-text-2)] leading-relaxed font-medium line-clamp-3">{sug.hypothesis}</p>
                                    </button>
                                ))}
                            </div>
                        ) : !loadingSuggestions && selectedSources.size > 0 && (
                            <p className="text-[9px] text-[var(--bi-text-3)] italic text-center py-2">Haz clic en &quot;Obtener Sugerencias&quot; para que la IA diseñe hipótesis a partir de los datos.</p>
                        )}
                    </div>

                    {/* Botón de Lanzamiento */}
                    <div className="space-y-4">
                        <button 
                            type="button"
                            onClick={handleStart}
                            disabled={loading || !title.trim() || !hypothesis.trim() || selectedSources.size === 0}
                            className={`w-full py-4 rounded-xl font-bold uppercase tracking-wider transition-all duration-300 flex items-center justify-center gap-2 cursor-pointer shadow-lg ${
                                (!loading && title.trim() && hypothesis.trim() && selectedSources.size > 0)
                                ? 'bg-[var(--module-simulation-accent)] hover:bg-[var(--module-simulation-accent-hover)] text-white shadow-[0_4px_16px_rgba(168,85,247,0.3)] hover:-translate-y-0.5' 
                                : 'bg-[var(--bi-surface-3)] text-[var(--bi-text-3)] cursor-not-allowed opacity-50 border border-[var(--bi-border)]'
                            }`}
                        >
                            {loading ? (
                                <Loader2 className="w-5 h-5 animate-spin" />
                            ) : (
                                <>
                                    <Sparkles className="w-4 h-4" />
                                    <span>Iniciar Debate de Agentes</span>
                                </>
                            )}
                        </button>
                        
                        {dataSources.length === 0 && (
                            <div className="p-4 bg-[var(--bi-amber-dim)] border border-[var(--bi-amber)]/20 rounded-xl flex items-start gap-3">
                                <AlertCircle className="w-4.5 h-4.5 text-[var(--bi-amber)] mt-0.5 flex-shrink-0" />
                                <div>
                                    <p className="text-[10px] font-bold text-[var(--bi-amber)] uppercase tracking-wider mb-0.5">Simulador Bloqueado</p>
                                    <p className="text-[9px] text-[var(--bi-text-2)] leading-relaxed font-semibold">
                                        Para garantizar que la simulación sea realista y basada en tu negocio, debes cargar al menos un archivo en el Chat antes de comenzar.
                                    </p>
                                </div>
                            </div>
                        )}
                    </div>

                </div>

            </div>
        </div>
    );
}
