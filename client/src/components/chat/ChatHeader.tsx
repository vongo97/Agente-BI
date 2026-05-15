import { Menu, Bot, Sparkles, LayoutDashboard, FileText, FileDown, PlusCircle, Loader2 } from "lucide-react";
import { getPdfExportUrl } from "@/lib/api";

interface ChatHeaderProps {
    setSidebarOpen: (open: boolean) => void;
    dataSources: any[];
    cleaningData: boolean;
    handleCleanData: () => void;
    loadingAutoDash: boolean;
    handleAutoDash: () => void;
    messages: any[];
    setReportBuilderOpen: (open: boolean) => void;
    activeChatId: number | null;
    userId: string;
    handleNewChat: () => void;
    aiProvider: string;
}

export function ChatHeader({
    setSidebarOpen,
    dataSources,
    cleaningData,
    handleCleanData,
    loadingAutoDash,
    handleAutoDash,
    messages,
    setReportBuilderOpen,
    activeChatId,
    userId,
    handleNewChat,
    aiProvider
}: ChatHeaderProps) {
    return (
        <header className="h-16 border-b border-[var(--border-color)] flex items-center justify-between px-4 lg:px-8 bg-[var(--bg-primary)]/80 backdrop-blur-xl sticky top-0 z-10 w-full">
            <div className="flex items-center gap-3">
                <button onClick={() => setSidebarOpen(true)} className="lg:hidden p-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)]">
                    <Menu className="w-5 h-5" />
                </button>
                <div className="relative hidden xs:block">
                    <Bot className="w-5 h-5 text-blue-500" />
                    <span className="absolute -top-1 -right-1 w-2 h-2 bg-green-500 rounded-full border-2 border-[var(--bg-primary)]"></span>
                </div>
                <h2 className="text-[10px] font-black text-[var(--text-tertiary)] uppercase tracking-[0.2em] flex items-center gap-2 truncate">Analista AI</h2>
            </div>
            <div className="flex items-center gap-2 lg:gap-4">
                {dataSources.length > 0 && (
                    <div className="flex items-center gap-2">
                        <button
                            onClick={handleCleanData}
                            disabled={cleaningData}
                            title="Limpiar datos con IA"
                            className={`px-4 py-2 flex items-center gap-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${cleaningData
                                ? 'bg-blue-600/20 text-blue-400 cursor-not-allowed'
                                : 'bg-[var(--bg-secondary)] hover:bg-[var(--bg-tertiary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] border border-[var(--border-color)] shadow-xl shadow-blue-900/10'
                                }`}
                        >
                            {cleaningData ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3 text-blue-500" />}
                            <span className="hidden sm:inline">{cleaningData ? 'Limpiando...' : 'Magic Clean'}</span>
                        </button>

                        <button
                            onClick={handleAutoDash}
                            disabled={loadingAutoDash}
                            className={`px-4 py-2 flex items-center gap-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${loadingAutoDash
                                ? 'bg-purple-600/20 text-purple-400 cursor-not-allowed'
                                : 'bg-[var(--bg-secondary)] hover:bg-[var(--bg-tertiary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] border border-[var(--border-color)]'
                                }`}
                        >
                            {loadingAutoDash ? <Loader2 className="w-3 h-3 animate-spin" /> : <LayoutDashboard className="w-3 h-3 text-purple-500" />}
                            <span className="hidden sm:inline">{loadingAutoDash ? 'Diseñando...' : 'Auto Dash'}</span>
                        </button>
                    </div>
                )}
                {messages.length > 0 && (
                    <button
                        onClick={() => setReportBuilderOpen(true)}
                        className="flex items-center gap-2 px-3 py-1.5 bg-blue-600/20 hover:bg-blue-600/30 rounded-full border border-blue-500/20 text-[10px] font-bold text-blue-400 hover:text-blue-300 transition-all uppercase tracking-tighter"
                    >
                        <FileText className="w-3.5 h-3.5" /> Generar Reporte Pro
                    </button>
                )}
                {activeChatId && (
                    <a href={getPdfExportUrl(activeChatId, userId)} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 px-3 py-1.5 bg-[var(--bg-secondary)] hover:bg-[var(--bg-tertiary)] rounded-full border border-[var(--border-color)] text-[10px] font-bold text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-all uppercase tracking-tighter">
                        <FileDown className="w-3.5 h-3.5" /> PDF Simple
                    </a>
                )}
                <button onClick={handleNewChat} className="flex items-center gap-2 px-3 py-1.5 bg-[var(--bg-secondary)] hover:bg-[var(--bg-tertiary)] rounded-full border border-[var(--border-color)] text-[10px] font-bold text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-all uppercase tracking-tighter">
                    <PlusCircle className="w-3.5 h-3.5" /> Nuevo Chat
                </button>
                <div className="hidden sm:block h-4 w-px bg-[var(--border-color)]"></div>
                <div className={`flex items-center gap-2 px-2 lg:px-3 py-1.5 rounded-full border transition-colors ${aiProvider === 'mistral' ? 'bg-purple-600/10 border-purple-600/20' :
                    aiProvider === 'hybrid' ? 'bg-gradient-to-r from-blue-600/10 to-purple-600/10 border-indigo-500/20' :
                        'bg-blue-600/10 border-blue-600/20'
                    }`}>
                    <Sparkles className={`w-3 h-3 ${aiProvider === 'mistral' ? 'text-purple-500' : aiProvider === 'hybrid' ? 'text-indigo-400' : 'text-blue-500'}`} />
                    <span className={`text-[8px] lg:text-[10px] font-bold uppercase tracking-tighter ${aiProvider === 'mistral' ? 'text-purple-400' :
                        aiProvider === 'hybrid' ? 'text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-400' :
                            'text-blue-400'
                        }`}>
                        {aiProvider === 'mistral' ? 'Mistral Large' : aiProvider === 'hybrid' ? 'Cerebro Dual' : 'Gemini 2.5 Flash'}
                    </span>
                </div>
            </div>
        </header>
    );
}
