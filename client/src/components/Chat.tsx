'use client';

import { useState, useRef, useEffect } from "react";
import { useSession } from "next-auth/react";
import { Send, Bot, User, Loader2, BarChart3, ChevronRight, Share2, Sparkles, Menu, PlusCircle, Pin, Download, FileDown } from "lucide-react";
import { analyzeData, pinToDashboard, exportChartAsPng, getPdfExportUrl } from "@/lib/api";
import { useDashboard, Message } from "@/context/DashboardContext";
import dynamic from "next/dynamic";

// Importación dinámica de Plotly para evitar errores de SSR
const Plot = dynamic(() => import("react-plotly.js"), {
    ssr: false,
    loading: () => (
        <div className="h-[400px] w-full bg-white/[0.02] animate-pulse rounded-xl flex items-center justify-center">
            <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />
        </div>
    )
}) as any;

export function Chat() {
    const { data: session } = useSession();
    const { apiKey, dataSource, setSidebarOpen, messages, setMessages, activeChatId, setActiveChatId } = useDashboard();
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);

    const userId = session?.user?.email || "default_user";

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim() || loading) return;
        if (!dataSource) {
            alert("Por favor, sube una fuente de datos primero.");
            return;
        }

        const userMsg: Message = { role: 'user', content: input };
        setMessages(prev => [...prev, userMsg]);
        setInput("");
        setLoading(true);

        try {
            const res = await analyzeData(input, apiKey, userId, activeChatId || undefined);

            const assistantMsg: Message = {
                id: res.message_id,
                role: 'assistant',
                content: res.analysis || "He procesado tu solicitud.",
                fig: res.figure
            };
            setMessages(prev => [...prev, assistantMsg]);

            if (!activeChatId && res.chat_id) {
                setActiveChatId(res.chat_id);
            }
        } catch (error) {
            setMessages(prev => [...prev, { role: 'assistant', content: "Lo siento, hubo un error al procesar tu análisis." }]);
        } finally {
            setLoading(false);
        }
    };

    const handleNewChat = () => {
        setMessages([]);
        setActiveChatId(null);
    };

    const handlePin = async (messageId: number) => {
        if (!activeChatId) return;
        try {
            await pinToDashboard(userId, activeChatId, messageId);
            alert("¡Anclado al panel de control! 📌");
        } catch (error) {
            alert("Error al anclar");
        }
    };

    const handleExportPng = async (fig: any, name: string) => {
        try {
            const blob = await exportChartAsPng(fig);
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `bi_chart_${name.slice(0, 10)}.png`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
        } catch (error) {
            alert("Error al exportar imagen");
        }
    };

    return (
        <div className="flex flex-col h-screen flex-1 bg-black overflow-hidden border-l border-white/5">
            <header className="h-16 border-b border-white/5 flex items-center justify-between px-4 lg:px-8 bg-black/40 backdrop-blur-xl sticky top-0 z-10 w-full">
                <div className="flex items-center gap-3">
                    <button onClick={() => setSidebarOpen(true)} className="lg:hidden p-2 text-gray-500 hover:text-white">
                        <Menu className="w-5 h-5" />
                    </button>
                    <div className="relative hidden xs:block">
                        <Bot className="w-5 h-5 text-blue-500" />
                        <span className="absolute -top-1 -right-1 w-2 h-2 bg-green-500 rounded-full border-2 border-black"></span>
                    </div>
                    <h2 className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em] flex items-center gap-2 truncate">Analista AI</h2>
                </div>
                <div className="flex items-center gap-2 lg:gap-4">
                    {activeChatId && (
                        <a href={getPdfExportUrl(activeChatId, userId)} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 px-3 py-1.5 bg-white/[0.05] hover:bg-white/[0.1] rounded-full border border-white/10 text-[10px] font-bold text-gray-400 hover:text-white transition-all uppercase tracking-tighter">
                            <FileDown className="w-3.5 h-3.5" /> Reporte PDF
                        </a>
                    )}
                    <button onClick={handleNewChat} className="flex items-center gap-2 px-3 py-1.5 bg-white/[0.05] hover:bg-white/[0.1] rounded-full border border-white/10 text-[10px] font-bold text-gray-400 hover:text-white transition-all uppercase tracking-tighter">
                        <PlusCircle className="w-3.5 h-3.5" /> Nuevo Chat
                    </button>
                    <div className="hidden sm:block h-4 w-px bg-white/10"></div>
                    <div className="flex items-center gap-2 bg-blue-600/10 px-2 lg:px-3 py-1.5 rounded-full border border-blue-600/20">
                        <Sparkles className="w-3 h-3 text-blue-500" />
                        <span className="text-[8px] lg:text-[10px] font-bold text-blue-400 uppercase tracking-tighter">Gemini 2.5 Flash</span>
                    </div>
                </div>
            </header>

            <div className="flex-1 overflow-y-auto p-4 lg:p-8 lg:px-20 space-y-8 lg:space-y-12 custom-scrollbar" ref={scrollRef}>
                {messages.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-center max-w-xl mx-auto space-y-8 animate-in fade-in zoom-in duration-700">
                        <div className="relative">
                            <div className="absolute inset-0 bg-blue-600/20 blur-3xl rounded-full"></div>
                            <div className="w-20 h-20 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-3xl flex items-center justify-center relative shadow-2xl shadow-blue-500/20 rotate-3 transition-transform">
                                <BarChart3 className="w-10 h-10 text-white" />
                            </div>
                        </div>
                        <div className="space-y-4">
                            <h3 className="text-3xl font-black text-white tracking-tight italic">¿Qué vamos a descubrir hoy?</h3>
                            <p className="text-gray-500 text-sm leading-relaxed max-w-sm mx-auto">Transforma datos fríos en decisiones estratégicas.</p>
                        </div>
                    </div>
                ) : (
                    messages.map((msg, i) => (
                        <div key={i} className={`flex gap-6 animate-in slide-in-from-bottom-4 duration-500 ${msg.role === 'user' ? 'justify-end' : ''}`}>
                            {msg.role === 'assistant' && (
                                <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-blue-600 to-blue-800 flex items-center justify-center flex-shrink-0 shadow-lg shadow-blue-900/40">
                                    <Bot className="w-6 h-6 text-white" />
                                </div>
                            )}
                            <div className={`max-w-[85%] space-y-6 ${msg.role === 'user' ? 'text-right' : ''}`}>
                                <div className={`inline-block px-6 py-4 rounded-3xl text-sm leading-relaxed shadow-2xl ${msg.role === 'user' ? 'bg-blue-600 text-white rounded-tr-none' : 'bg-[#111] text-gray-200 border border-white/5 rounded-tl-none font-medium'}`}>
                                    {msg.content}
                                </div>
                                {msg.fig && (
                                    <div className="bg-[#0a0a0a] border border-white/5 rounded-3xl p-6 shadow-2xl overflow-hidden group">
                                        <div className="flex items-center justify-between mb-6">
                                            <div className="flex items-center gap-2">
                                                <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                                                <span className="text-[10px] font-black text-gray-600 uppercase tracking-[0.2em]">Visualización Dinámica</span>
                                            </div>
                                        </div>
                                        <div className="mt-6 border border-white/5 rounded-2xl overflow-hidden bg-black/40 relative group/chart">
                                            <div className="absolute top-4 right-4 z-10 opacity-0 group-hover/chart:opacity-100 transition-opacity flex gap-2">
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
                                                    font: { color: '#888' },
                                                    margin: { t: 30, b: 30, l: 30, r: 30 },
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
                            </div>
                            {msg.role === 'user' && (
                                <div className="w-10 h-10 rounded-2xl bg-[#111] border border-white/10 flex items-center justify-center flex-shrink-0 shadow-xl">
                                    <User className="w-6 h-6 text-gray-400" />
                                </div>
                            )}
                        </div>
                    ))
                )}
                {loading && (
                    <div className="flex gap-6 animate-pulse">
                        <div className="w-10 h-10 rounded-2xl bg-blue-600 flex items-center justify-center">
                            <Bot className="w-6 h-6 text-white" />
                        </div>
                        <div className="bg-[#111] border border-white/5 rounded-3xl rounded-tl-none px-6 py-4 flex items-center gap-4">
                            <div className="flex gap-1">
                                <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                                <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                                <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce"></span>
                            </div>
                            <span className="text-xs text-gray-500 font-bold uppercase tracking-widest italic">IA Analizando...</span>
                        </div>
                    </div>
                )}
            </div>

            <div className="p-4 lg:p-8 pb-8 lg:pb-12 bg-gradient-to-t from-black via-black to-transparent">
                <div className="max-w-4xl mx-auto relative group">
                    <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-2xl blur opacity-20 group-hover:opacity-40 transition duration-1000 group-focus-within:opacity-50"></div>
                    <input
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                        placeholder={dataSource ? "Escribe tu pregunta estratégica..." : "Suba un archivo para comenzar..."}
                        disabled={!dataSource || loading}
                        className="relative w-full bg-[#0a0a0a] border border-white/10 rounded-2xl px-6 py-5 pr-16 text-sm text-white placeholder:text-gray-700 focus:outline-none focus:border-blue-500/50 transition-all shadow-3xl disabled:opacity-50 disabled:cursor-not-allowed"
                    />
                    <button
                        onClick={handleSend}
                        disabled={loading || !input.trim() || !dataSource}
                        className="absolute right-3 top-1/2 -translate-y-1/2 p-3 bg-blue-600 text-white rounded-xl hover:bg-blue-500 transition-all disabled:bg-gray-800 disabled:text-gray-600"
                    >
                        <Send className="w-5 h-5" />
                    </button>
                </div>
                <p className="mt-4 text-[9px] text-gray-800 font-black uppercase tracking-[0.2em] text-center">Precision BI Logic Engine • 2026</p>
            </div>
        </div>
    );
}
