import { Bot, User, ShieldAlert, Download, Pin } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import dynamic from "next/dynamic";
import { Loader2 } from "lucide-react";
import AutoDashGrid from "../AutoDashGrid";
import { Message } from "@/context/DashboardContext";

const Plot = dynamic(() => import("react-plotly.js"), {
    ssr: false,
    loading: () => (
        <div className="h-[360px] w-full shimmer-skeleton rounded-lg border border-[var(--bi-border)]" />
    ),
}) as React.ComponentType<{
    data: Record<string, unknown>[];
    layout: Record<string, unknown>;
    useResizeHandler?: boolean;
    style?: React.CSSProperties;
    config?: Record<string, unknown>;
}>;

interface PlotlyFigure {
    data: Record<string, unknown>[];
    layout: Record<string, unknown> & {
        showlegend?: boolean;
        xaxis?: Record<string, unknown>;
        yaxis?: Record<string, unknown>;
    };
}

interface MessageItemProps {
    msg: Message;
    userId: string;
    handleExportPng: (fig: unknown, content: string) => void;
    handlePin: (id: number) => void;
    handleSendAsQuery?: (queryText: string) => void;
}

const getCTAs = (content: string) => {
    const text = content.toLowerCase();
    const ctas: string[] = [];
    if (text.includes("venta") || text.includes("sale") || text.includes("ingreso") || text.includes("revenue")) {
        ctas.push("Simular ROI de ventas", "Ver tendencia de ventas");
    }
    if (text.includes("anomal") || text.includes("outlier") || text.includes("desviaci") || text.includes("atípico")) {
        ctas.push("Analizar distribución", "Magic Clean (Limpiar)");
    }
    if (text.includes("cliente") || text.includes("usuario") || text.includes("customer")) {
        ctas.push("Segmentación de clientes", "Ver tasa de retención");
    }
    if (ctas.length < 2) {
        ctas.push("Detectar anomalías", "Analizar distribución");
    }
    return ctas.slice(0, 2);
};

const isAnomaly = (content: string) =>
    content.includes("⚠️") || content.includes("Auditor de Datos");

export function MessageItem({ msg, userId, handleExportPng, handlePin, handleSendAsQuery }: MessageItemProps) {
    const isUser = msg.role === "user";
    const isAssistant = msg.role === "assistant";
    const anomaly = isAssistant && isAnomaly(msg.content);

    return (
        <div className={`flex gap-3 animate-in slide-in-from-bottom-2 duration-300 ${isUser ? "justify-end" : "items-start"}`}>
            {/* Avatar — assistant */}
            {isAssistant && (
                <div className="w-7 h-7 rounded-md bg-[var(--bi-teal-dim)] border border-[var(--bi-teal-border)] flex items-center justify-center flex-shrink-0 mt-0.5">
                    <Bot className="w-4 h-4 text-[var(--bi-teal)]" />
                </div>
            )}

            <div className={`min-w-0 space-y-2 ${isUser ? "max-w-[75%]" : "max-w-[80%] flex-1"}`}>
                {/* Bubble */}
                <div
                    className={`
                        px-4 py-3 rounded-lg text-sm leading-relaxed
                        ${isUser
                            ? "bg-[var(--bi-surface-1)] border border-[var(--bi-border-strong)] border-r-2 border-r-[var(--bi-teal)] text-[var(--bi-text-1)] ml-auto w-fit shadow-md"
                            : anomaly
                                ? "bg-[var(--bi-amber-dim)] border border-[var(--bi-amber)]/25 text-[var(--bi-text-1)]"
                                : "bg-[var(--bi-surface-0)] border border-[var(--bi-border)] text-[var(--bi-text-1)] shadow-sm"
                        }
                    `}
                >
                    {/* Anomaly badge */}
                    {anomaly && (
                        <div className="flex items-center gap-1.5 mb-2 text-[var(--bi-amber)]">
                            <ShieldAlert className="w-3.5 h-3.5 flex-shrink-0" />
                            <span className="text-[10px] font-semibold uppercase tracking-wider">
                                Anomalía detectada
                            </span>
                        </div>
                    )}

                    <div className="markdown-content prose prose-sm max-w-none">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {msg.content}
                        </ReactMarkdown>
                    </div>

                    {isAssistant && handleSendAsQuery && (
                        <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-[var(--bi-border)]">
                            {getCTAs(msg.content).map((cta, idx) => (
                                <button
                                    key={idx}
                                    onClick={() => handleSendAsQuery(cta)}
                                    className="px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-[var(--bi-teal)] bg-[var(--bi-teal-dim)] border border-[var(--bi-teal-border)] hover:bg-[var(--bi-teal)] hover:text-black rounded transition-all cursor-pointer inline-flex items-center gap-1"
                                >
                                    <span>{cta}</span>
                                </button>
                            ))}
                        </div>
                    )}
                </div>

                {/* Chart */}
                {(() => {
                    const fig = msg.fig as PlotlyFigure | undefined;
                    return fig ? (
                        <div className="bg-[var(--bi-surface-0)] border border-[var(--bi-border)] rounded-lg overflow-hidden shadow-md">
                            {/* Chart toolbar */}
                            <div className="flex items-center justify-between px-3 py-2 border-b border-[var(--bi-border)] bg-[var(--bi-surface-0)]/50">
                                <span className="text-[10px] font-semibold text-[var(--bi-text-3)] uppercase tracking-wider flex items-center gap-1.5">
                                    <span className="w-1.5 h-1.5 rounded-full bg-[var(--bi-teal)]" />
                                    Visualización
                                </span>
                                <div className="flex items-center gap-1">
                                    <button
                                        onClick={() => handleExportPng(fig, msg.content)}
                                        title="Descargar PNG"
                                        className="p-1.5 rounded text-[var(--bi-text-3)] hover:text-[var(--bi-text-1)] hover:bg-[var(--bi-surface-2)] transition-colors cursor-pointer"
                                    >
                                        <Download className="w-3.5 h-3.5" />
                                    </button>
                                    {msg.id && (
                                        <button
                                            onClick={() => handlePin(msg.id!)}
                                            title="Anclar al panel"
                                            className="p-1.5 rounded text-[var(--bi-text-3)] hover:text-[var(--bi-teal)] hover:bg-[var(--bi-surface-2)] transition-colors cursor-pointer"
                                        >
                                            <Pin className="w-3.5 h-3.5" />
                                        </button>
                                    )}
                                </div>
                            </div>

                            {/* Plot */}
                            <div className="p-2">
                                <Plot
                                    data={fig.data}
                                    layout={{
                                        ...fig.layout,
                                        autosize: true,
                                        paper_bgcolor: "rgba(0,0,0,0)",
                                        plot_bgcolor: "rgba(0,0,0,0)",
                                        font: {
                                            color: "var(--bi-text-2)",
                                            family: "Inter, sans-serif",
                                            size: 11,
                                        },
                                        margin: { t: 32, b: 36, l: 48, r: 16 },
                                        showlegend: fig.layout.showlegend ?? false,
                                        xaxis: {
                                            ...(fig.layout.xaxis || {}),
                                            gridcolor: "var(--bi-border)",
                                            zerolinecolor: "var(--bi-border)",
                                        },
                                        yaxis: {
                                            ...(fig.layout.yaxis || {}),
                                            gridcolor: "var(--bi-border)",
                                            zerolinecolor: "var(--bi-border)",
                                        },
                                    }}
                                    useResizeHandler
                                    style={{ width: "100%", minHeight: "320px" }}
                                    config={{ responsive: true, displayModeBar: false }}
                                />
                            </div>
                        </div>
                    ) : null;
                })()}

                {msg.dashboardData && (
                    <AutoDashGrid
                        items={msg.dashboardData.charts}
                        metrics={msg.dashboardData.metrics}
                        userId={userId}
                    />
                )}
            </div>

            {/* Avatar — user */}
            {isUser && (
                <div className="w-7 h-7 rounded-md bg-[var(--bi-surface-1)] border border-[var(--bi-border)] flex items-center justify-center flex-shrink-0 mt-0.5">
                    <User className="w-3.5 h-3.5 text-[var(--bi-text-2)]" />
                </div>
            )}
        </div>
    );
}
