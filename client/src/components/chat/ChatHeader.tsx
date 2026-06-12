import { Menu, Bot, Sparkles, LayoutDashboard, FileText, FileDown, Plus, Loader2 } from "lucide-react";
import { exportPdf } from "@/lib/api";
import { useState } from "react";

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

const PROVIDER_LABELS: Record<string, string> = {
    gemini: "Gemini 2.5",
    mistral: "Mistral Large",
    hybrid: "Dual Mode",
};

const PROVIDER_COLORS: Record<string, string> = {
    gemini: "text-[var(--bi-blue)]",
    mistral: "text-[var(--bi-teal)]",
    hybrid: "text-[var(--bi-amber)]",
};

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
    aiProvider,
}: ChatHeaderProps) {
    const [downloadingPdf, setDownloadingPdf] = useState(false);

    const handleDownloadPdf = async () => {
        if (!activeChatId) return;
        setDownloadingPdf(true);
        try {
            const blob = await exportPdf(activeChatId, userId);
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `reporte_chat_${activeChatId}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();
        } catch (err) {
            console.error("Error al descargar PDF:", err);
            alert("Error al descargar el PDF.");
        } finally {
            setDownloadingPdf(false);
        }
    };

    const providerLabel = PROVIDER_LABELS[aiProvider] ?? aiProvider;
    const providerColor = PROVIDER_COLORS[aiProvider] ?? "text-[var(--bi-teal)]";

    return (
        <header className="h-12 border-b border-[var(--bi-border)] flex items-center justify-between px-3 lg:px-5 bg-[var(--bi-surface-0)] sticky top-0 z-10 w-full flex-shrink-0">
            {/* Left: identity */}
            <div className="flex items-center gap-2.5 min-w-0">
                <button
                    onClick={() => setSidebarOpen(true)}
                    className="lg:hidden p-1.5 rounded-md text-[var(--bi-text-3)] hover:text-[var(--bi-text-1)] hover:bg-[var(--bi-surface-1)] transition-colors cursor-pointer"
                    aria-label="Abrir menú"
                >
                    <Menu className="w-4 h-4" />
                </button>
                <div className="flex items-center gap-1.5">
                    <div className="relative">
                        <Bot className="w-4 h-4 text-[var(--bi-teal)]" />
                        <span className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 bg-[var(--bi-green)] rounded-full" />
                    </div>
                    <span className="text-xs font-semibold text-[var(--bi-text-2)] hidden sm:block">
                        Analista BI
                    </span>
                </div>
                {/* Provider badge */}
                <div className="hidden sm:flex items-center gap-1 px-2 py-0.5 rounded border border-[var(--bi-border)] bg-[var(--bi-surface-1)]">
                    <Sparkles className={`w-2.5 h-2.5 ${providerColor}`} />
                    <span className={`text-[10px] font-semibold ${providerColor}`}>{providerLabel}</span>
                </div>
            </div>

            {/* Right: toolbar actions */}
            <div className="flex items-center gap-1">
                {dataSources.length > 0 && (
                    <>
                        <ToolbarButton
                            onClick={handleCleanData}
                            disabled={cleaningData}
                            title="Magic Clean — limpia y normaliza el dataset con IA"
                            icon={cleaningData ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                            label="Magic Clean"
                        />
                        <ToolbarButton
                            onClick={handleAutoDash}
                            disabled={loadingAutoDash}
                            title="Auto-Dashboard — genera panel automático con métricas clave"
                            icon={loadingAutoDash ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <LayoutDashboard className="w-3.5 h-3.5" />}
                            label="Auto Dash"
                        />
                    </>
                )}

                {messages.length > 0 && (
                    <ToolbarButton
                        onClick={() => setReportBuilderOpen(true)}
                        title="Generar informe ejecutivo desde esta conversación"
                        icon={<FileText className="w-3.5 h-3.5" />}
                        label="Informe"
                        highlight
                    />
                )}

                {activeChatId && (
                    <ToolbarButton
                        onClick={handleDownloadPdf}
                        disabled={downloadingPdf}
                        title="Exportar conversación como PDF"
                        icon={downloadingPdf ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileDown className="w-3.5 h-3.5" />}
                        label="PDF"
                    />
                )}

                <div className="w-px h-4 bg-[var(--bi-border)] mx-1" />

                <button
                    onClick={handleNewChat}
                    title="Iniciar nueva conversación"
                    className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-[10px] font-semibold text-[var(--bi-text-2)] hover:text-[var(--bi-text-1)] hover:bg-[var(--bi-surface-1)] border border-[var(--bi-border)] transition-colors cursor-pointer"
                >
                    <Plus className="w-3.5 h-3.5" />
                    <span className="hidden sm:inline">Nuevo</span>
                </button>
            </div>
        </header>
    );
}

interface ToolbarButtonProps {
    onClick: () => void;
    disabled?: boolean;
    title: string;
    icon: React.ReactNode;
    label: string;
    highlight?: boolean;
}

function ToolbarButton({ onClick, disabled, title, icon, label, highlight }: ToolbarButtonProps) {
    return (
        <button
            onClick={onClick}
            disabled={disabled}
            title={title}
            className={`
                flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-[10px] font-semibold transition-colors cursor-pointer
                disabled:opacity-40 disabled:cursor-not-allowed
                ${highlight
                    ? "text-[var(--bi-teal)] bg-[var(--bi-teal-dim)] border border-[var(--bi-teal-border)] hover:bg-[var(--bi-teal-dim)]/20"
                    : "text-[var(--bi-text-2)] hover:text-[var(--bi-text-1)] hover:bg-[var(--bi-surface-2)] border border-[var(--bi-border)]"
                }
            `}
        >
            {icon}
            <span className="hidden md:inline">{label}</span>
        </button>
    );
}
