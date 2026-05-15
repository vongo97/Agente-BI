import { Bot, User, ShieldAlert, Download, Pin } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import dynamic from "next/dynamic";
import { Loader2 } from "lucide-react";
import AutoDashGrid from '../AutoDashGrid';
import { Message } from "@/context/DashboardContext";

const Plot = dynamic(() => import("react-plotly.js"), {
    ssr: false,
    loading: () => (
        <div className="h-[400px] w-full bg-white/[0.02] animate-pulse rounded-xl flex items-center justify-center">
            <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />
        </div>
    )
}) as any;

interface MessageItemProps {
    msg: Message;
    userId: string;
    handleExportPng: (fig: any, content: string) => void;
    handlePin: (id: number) => void;
}

export function MessageItem({ msg, userId, handleExportPng, handlePin }: MessageItemProps) {
    return (
        <div className={`flex gap-6 animate-in slide-in-from-bottom-4 duration-500 ${msg.role === 'user' ? 'justify-end' : ''}`}>
            {msg.role === 'assistant' && (
                <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-blue-600 to-blue-800 flex items-center justify-center flex-shrink-0 shadow-lg shadow-blue-900/40">
                    <Bot className="w-6 h-6 text-white" />
                </div>
            )}
            <div className={`max-w-[85%] space-y-4 ${msg.role === 'user' ? 'text-right' : ''}`}>
                <div className={`inline-block px-6 py-4 rounded-3xl text-sm leading-relaxed shadow-2xl relative overflow-hidden ${msg.role === 'user'
                    ? 'bg-blue-600 text-white rounded-tr-none'
                    : msg.content.includes("⚠️") || msg.content.includes("Auditor de Datos")
                        ? 'bg-orange-500/5 text-orange-100 border-2 border-orange-500/20 rounded-tl-none font-medium'
                        : 'bg-[var(--bg-tertiary)] text-[var(--text-primary)] border border-[var(--border-color)] rounded-tl-none font-medium'
                    }`}>
                    {(msg.content.includes("⚠️") || msg.content.includes("Auditor de Datos")) && msg.role === 'assistant' && (
                        <div className="flex items-center gap-2 mb-2 text-orange-400">
                            <ShieldAlert className="w-4 h-4" />
                            <span className="text-[10px] font-black uppercase tracking-widest">Alerta de Anomalía Detectada</span>
                        </div>
                    )}
                    {msg.role === 'assistant' && (msg.content.includes("⚠️") || msg.content.includes("Auditor de Datos")) && (
                        <div className="absolute top-0 right-0 w-24 h-24 bg-orange-500/10 blur-3xl -z-10 animate-pulse" />
                    )}
                    <div className="markdown-content prose prose-invert prose-sm max-w-none
                    prose-headings:text-white prose-headings:font-bold prose-headings:mt-4 prose-headings:mb-2
                    prose-p:mb-4 prose-p:leading-relaxed
                    prose-li:mb-2 prose-ul:list-disc prose-ul:ml-4 prose-ol:list-decimal prose-ol:ml-4">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {msg.content}
                        </ReactMarkdown>
                    </div>
                </div>
                {msg.fig && (
                    <div className="bg-[#0a0a0a] border border-white/5 rounded-3xl p-6 shadow-2xl overflow-hidden group">
                        <div className="flex items-center justify-between mb-6">
                            <div className="flex items-center gap-2">
                                <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                                <span className="text-[10px] font-black text-gray-600 uppercase tracking-[0.2em]">Visualización Dinámica</span>
                            </div>
                        </div>
                        <div className="mt-4 p-5 bg-white/[0.03] border border-white/10 rounded-2xl flex flex-col items-center justify-center min-h-[300px] group/plot relative">
                            <div className="absolute top-4 right-4 z-10 opacity-0 group-hover/plot:opacity-100 transition-opacity flex gap-2">
                                <button onClick={() => handleExportPng(msg.fig, msg.content)} className="p-2 bg-blue-600/90 hover:bg-blue-600 rounded-lg text-white shadow-xl transition-all" title="Descargar PNG">
                                    <Download className="w-4 h-4" />
                                </button>
                                {msg.id && (
                                    <button onClick={() => handlePin(msg.id!)} className="p-2 bg-indigo-600/90 hover:bg-indigo-600 rounded-lg text-white shadow-xl transition-all" title="Anclar al Panel">
                                        <Pin className="w-4 h-4" />
                                    </button>
                                )}
                            </div>
                            <Plot
                                data={msg.fig.data}
                                layout={{
                                    ...msg.fig.layout,
                                    autosize: true,
                                    paper_bgcolor: 'rgba(0,0,0,0)',
                                    plot_bgcolor: 'rgba(0,0,0,0)',
                                    font: {
                                        color: '#aaa',
                                        family: 'Inter, sans-serif',
                                        size: 10
                                    },
                                    margin: { t: 40, b: 40, l: 50, r: 20 },
                                    showlegend: msg.fig.layout.showlegend ?? false,
                                    xaxis: { ...msg.fig.layout.xaxis, gridcolor: '#111', zerolinecolor: '#222' },
                                    yaxis: { ...msg.fig.layout.yaxis, gridcolor: '#111', zerolinecolor: '#222' }
                                }}
                                useResizeHandler={true}
                                style={{ width: "100%", height: "100%", minHeight: "340px" }}
                                config={{ responsive: true, displayModeBar: false }}
                            />
                        </div>
                    </div>
                )}
                {(msg as any).dashboardData && (
                    <AutoDashGrid 
                        items={(msg as any).dashboardData.charts} 
                        metrics={(msg as any).dashboardData.metrics}
                        userId={userId} 
                    />
                )}
            </div>
            {msg.role === 'user' && (
                <div className="w-10 h-10 rounded-2xl bg-[var(--bg-tertiary)] border border-[var(--border-color)] flex items-center justify-center flex-shrink-0 shadow-xl">
                    <User className="w-6 h-6 text-[var(--text-secondary)]" />
                </div>
            )}
        </div>
    );
}
