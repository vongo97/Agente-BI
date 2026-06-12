import { Send, Loader2 } from "lucide-react";

interface ChatInputProps {
    input: string;
    setInput: (val: string) => void;
    handleSend: () => void;
    loading: boolean;
    dataSourcesCount: number;
}

export function ChatInput({
    input,
    setInput,
    handleSend,
    loading,
    dataSourcesCount,
}: ChatInputProps) {
    const hasData = dataSourcesCount > 0;
    const canSend = hasData && !loading && input.trim().length > 0;

    return (
        <div className="px-4 py-3 lg:px-8 lg:py-4 border-t border-[var(--bi-border)] bg-[var(--bi-canvas)] flex-shrink-0">
            <div className="max-w-4xl mx-auto flex items-end gap-2">
                <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                            e.preventDefault();
                            if (canSend) handleSend();
                        }
                    }}
                    rows={2}
                    placeholder={
                        hasData
                            ? "Escribe tu pregunta sobre los datos… (Enter para enviar, Shift+Enter para nueva línea)"
                            : "Sube un archivo de datos para comenzar el análisis"
                    }
                    disabled={!hasData || loading}
                    className="
                        flex-1 resize-none custom-scrollbar
                        bg-[var(--bi-surface-0)] border border-[var(--bi-border)]
                        rounded-lg px-4 py-2.5 text-sm text-[var(--bi-text-1)]
                        placeholder:text-[var(--bi-text-3)]
                        focus:outline-none focus:border-[var(--bi-teal-border)]
                        transition-colors
                        disabled:opacity-40 disabled:cursor-not-allowed
                    "
                />
                <button
                    onClick={handleSend}
                    disabled={!canSend}
                    title="Enviar consulta"
                    className="
                        flex-shrink-0 p-3 rounded-lg
                        bg-[var(--bi-teal)] text-[var(--bi-canvas)]
                        hover:bg-[var(--bi-teal-hover)]
                        disabled:bg-[var(--bi-surface-3)] disabled:text-[var(--bi-text-3)]
                        transition-colors cursor-pointer disabled:cursor-not-allowed
                    "
                >
                    {loading
                        ? <Loader2 className="w-4 h-4 animate-spin" />
                        : <Send className="w-4 h-4" />
                    }
                </button>
            </div>
            <p className="mt-2 text-[10px] text-[var(--bi-text-3)] text-center font-medium">
                Vektra BI · Precision Analysis Engine
            </p>
        </div>
    );
}
