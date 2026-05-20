import { Send } from "lucide-react";

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
    dataSourcesCount
}: ChatInputProps) {
    return (
        <div className="p-4 lg:p-8 pb-8 lg:pb-12 bg-gradient-to-t from-[var(--bg-primary)] via-[var(--bg-primary)] to-transparent">
            <div className="max-w-4xl mx-auto relative group">
                <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-2xl blur opacity-20 group-hover:opacity-40 transition duration-1000 group-focus-within:opacity-50"></div>
                <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            handleSend();
                        }
                    }}
                    rows={2}
                    placeholder={dataSourcesCount > 0 ? "Escribe tu pregunta estratégica (Shift+Enter para nueva línea)..." : "Suba un archivo para comenzar..."}
                    disabled={dataSourcesCount === 0 || loading}
                    className="relative w-full resize-none custom-scrollbar bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-2xl px-6 py-4 pr-16 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:outline-none focus:border-blue-500/50 transition-all shadow-3xl disabled:opacity-50 disabled:cursor-not-allowed"
                />
                <button
                    onClick={handleSend}
                    disabled={loading || !input.trim() || dataSourcesCount === 0}
                    className="absolute right-3 top-1/2 -translate-y-1/2 p-3 bg-blue-600 text-white rounded-xl hover:bg-blue-500 transition-all disabled:bg-gray-800 disabled:text-gray-600"
                >
                    <Send className="w-5 h-5" />
                </button>
            </div>
            <p className="mt-4 text-[9px] text-gray-800 font-black uppercase tracking-[0.2em] text-center">Precision BI Logic Engine • 2026</p>
        </div>
    );
}
