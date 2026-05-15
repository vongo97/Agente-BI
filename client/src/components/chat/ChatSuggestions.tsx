import { Sparkles, Loader2, ChevronRight } from "lucide-react";

interface ChatSuggestionsProps {
    showAiSuggestions: boolean;
    loadingSuggestions: boolean;
    suggestions: string[];
    setInput: (val: string) => void;
    handleSendAsQuery: (query: string) => void;
    fetchSuggestions: () => void;
}

export function ChatSuggestions({
    showAiSuggestions,
    loadingSuggestions,
    suggestions,
    setInput,
    handleSendAsQuery,
    fetchSuggestions
}: ChatSuggestionsProps) {
    if (!showAiSuggestions) return null;

    return (
        <div className="grid grid-cols-1 gap-3 w-full max-w-md animate-in fade-in slide-in-from-bottom-8 duration-1000 delay-300">
            <p className="text-[10px] font-black text-gray-700 uppercase tracking-widest mb-2">Sugerencias de la IA</p>
            {loadingSuggestions ? (
                <div className="flex items-center gap-2 text-gray-700 animate-pulse justify-center p-4">
                    <Loader2 className="w-3 h-3 animate-spin" />
                    <span className="text-[10px] uppercase font-bold tracking-tighter italic">Generando ideas estratégicas...</span>
                </div>
            ) : suggestions.length > 0 ? (
                suggestions.map((sug, idx) => (
                    <button
                        key={idx}
                        onClick={() => {
                            setInput(sug);
                            setTimeout(() => handleSendAsQuery(sug), 100);
                        }}
                        className="group flex items-center justify-between p-4 bg-[var(--bg-secondary)] hover:bg-[var(--bg-tertiary)] border border-[var(--border-color)] hover:border-blue-500/30 rounded-2xl text-left transition-all text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                    >
                        <span className="flex-1 pr-4">{sug}</span>
                        <ChevronRight className="w-4 h-4 text-[var(--text-tertiary)] group-hover:text-blue-500 transition-colors" />
                    </button>
                ))
            ) : (
                <button
                    onClick={fetchSuggestions}
                    className="group flex items-center justify-center gap-2 p-4 bg-blue-600/10 hover:bg-blue-600/20 border border-blue-500/20 rounded-2xl transition-all text-xs text-blue-400 font-bold uppercase tracking-widest"
                >
                    <Sparkles className="w-4 h-4" />
                    Sugerir análisis estratégico
                </button>
            )}
        </div>
    );
}
