import { Sparkles, Loader2, ArrowRight, RefreshCw } from "lucide-react";

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
    fetchSuggestions,
}: ChatSuggestionsProps) {
    if (!showAiSuggestions) return null;

    return (
        <div className="w-full max-w-lg animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-semibold text-[var(--bi-text-3)] uppercase tracking-wider flex items-center gap-1.5">
                    <Sparkles className="w-3 h-3 text-[var(--bi-teal)]" />
                    Preguntas sugeridas
                </span>
                {!loadingSuggestions && (
                    <button
                        onClick={fetchSuggestions}
                        title="Regenerar sugerencias"
                        className="p-1 rounded text-[var(--bi-text-3)] hover:text-[var(--bi-text-1)] hover:bg-[var(--bi-surface-2)] transition-colors cursor-pointer"
                    >
                        <RefreshCw className="w-3 h-3" />
                    </button>
                )}
            </div>

            {loadingSuggestions ? (
                <div className="flex items-center gap-2 text-[var(--bi-text-3)] py-3">
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-[var(--bi-teal)]" />
                    <span className="text-xs">Generando sugerencias…</span>
                </div>
            ) : suggestions.length > 0 ? (
                <div className="space-y-1.5">
                    {suggestions.map((sug, idx) => (
                        <button
                            key={idx}
                            onClick={() => {
                                setInput(sug);
                                setTimeout(() => handleSendAsQuery(sug), 80);
                            }}
                            className="
                                group w-full flex items-center justify-between
                                px-3 py-2.5 rounded-lg text-left text-xs
                                text-[var(--bi-text-2)] hover:text-[var(--bi-text-1)]
                                bg-[var(--bi-surface-0)] border border-[var(--bi-border)]
                                hover:border-[var(--bi-teal-border)] hover:bg-[var(--bi-surface-1)]
                                transition-all cursor-pointer
                            "
                        >
                            <span className="flex-1 pr-3 leading-snug">{sug}</span>
                            <ArrowRight className="w-3.5 h-3.5 text-[var(--bi-text-3)] group-hover:text-[var(--bi-teal)] transition-colors flex-shrink-0" />
                        </button>
                    ))}
                </div>
            ) : (
                <button
                    onClick={fetchSuggestions}
                    className="
                        flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold
                        text-[var(--bi-teal)] border border-[var(--bi-teal-border)]
                        hover:bg-[var(--bi-teal-dim)] transition-colors cursor-pointer
                    "
                >
                    <Sparkles className="w-3.5 h-3.5" />
                    Sugerir análisis sobre mis datos
                </button>
            )}
        </div>
    );
}
