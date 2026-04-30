'use client';

import { useState, useRef, useEffect } from "react";
import { useSession } from "next-auth/react";
import { Send, Bot, User, Loader2, BarChart3, ChevronRight, Share2, Sparkles, Menu, PlusCircle, Pin, Download, FileDown, FileText, Radio, ShieldAlert, LayoutDashboard } from "lucide-react";
import { analyzeData, pinToDashboard, exportChartAsPng, getPdfExportUrl, generateAutoDashboard, suggestQuestions, cleanData } from "@/lib/api";
import { useDashboard, Message } from "@/context/DashboardContext";
import { ReportBuilder } from "./ReportBuilder";
import dynamic from "next/dynamic";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import AutoDashGrid from './AutoDashGrid';

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
    const {
        apiKey,
        mistralKey,
        aiProvider,
        dataSource,
        setSidebarOpen,
        messages,
        setMessages,
        activeChatId,
        setActiveChatId,
        setView,
        suggestions,
        setSuggestions,
        loadingSuggestions,
        setLoadingSuggestions,
        showAiSuggestions
    } = useDashboard();
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [loadingMessage, setLoadingMessage] = useState(""); // Nuevo: mensaje de progreso
    const [cleaningData, setCleaningData] = useState(false);
    const [loadingAutoDash, setLoadingAutoDash] = useState(false);
    const [reportBuilderOpen, setReportBuilderOpen] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);

    const userId = session?.user?.email || "default_user";

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    // Cargar sugerencias cuando se conecta una fuente
    useEffect(() => {
        if (dataSource && apiKey && messages.length === 0 && showAiSuggestions) {
            fetchSuggestions();
        } else if (!dataSource || !showAiSuggestions) {
            if (suggestions.length > 0) setSuggestions([]);
        }
    }, [dataSource?.filename, messages.length === 0, apiKey, activeChatId, showAiSuggestions]);

    const fetchSuggestions = async () => {
        if (!apiKey || !dataSource) return;
        setLoadingSuggestions(true);
        try {
            console.log("[DEBUG] Fetching suggestions for:", dataSource.filename, "Chat:", activeChatId);
            const res = await suggestQuestions(userId, apiKey, dataSource?.id, activeChatId || undefined, aiProvider, mistralKey);
            setSuggestions(res.suggestions || []);
        } catch (error) {
            console.error("Error cargando sugerencias:", error);
            setSuggestions([]);
        } finally {
            setLoadingSuggestions(false);
        }
    };

    const handleSend = async () => {
        await handleSendAsQuery(input);
    };

    const handleSendAsQuery = async (queryText: string) => {
        if (!queryText.trim() || loading) return;
        if (!dataSource) {
            alert("Por favor, sube una fuente de datos primero.");
            return;
        }

        const userMsg: Message = { role: 'user', content: queryText };
        setMessages(prev => [...prev, userMsg]);
        setInput("");
        setLoading(true);

        // Mensajes de progreso según el provider
        if (aiProvider === 'hybrid') {
            setLoadingMessage("🔄 Extrayendo inteligencia estratégica...");
        } else if (aiProvider === 'mistral') {
            setLoadingMessage("✍️ Redactando diagnóstico de negocio...");
        } else {
            setLoadingMessage("🧩 Orquestando hallazgos...");
        }

        try {
            // Simular delay para segundo mensaje en modo híbrido
            if (aiProvider === 'hybrid') {
                setTimeout(() => {
                    if (loading) setLoadingMessage("🌿 Refinando conclusiones del Partner...");
                }, 3000);
            }

            const res = await analyzeData(queryText, apiKey, userId, activeChatId || undefined, dataSource?.id, aiProvider, mistralKey);

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
            setLoadingMessage("");
        }
    };

    const handleAutoDash = async () => {
        if (!dataSource || !apiKey) {
            alert("Necesitas datos y API Key.");
            return;
        }
        setLoadingAutoDash(true);
        setLoadingMessage("📊 Analizando tu dataset...");

        setTimeout(() => {
            if (loadingAutoDash) setLoadingMessage("🎨 Diseñando los gráficos más relevantes...");
        }, 2000);

        try {
            const res = await generateAutoDashboard(apiKey, userId, dataSource?.id, activeChatId || undefined, aiProvider, mistralKey);

            const metrics = res.metrics || [];
            const charts = res.charts || [];
            
            const chartCount = charts.length;
            const metricCount = metrics.length;
            
            const countText = chartCount === 1 ? "un gráfico estratégico" :
                chartCount === 2 ? "2 gráficos estratégicos" :
                    `${chartCount} gráficos estratégicos`;

            const metricText = metricCount > 0 ? ` y ${metricCount} métricas clave` : "";

            const newMessage: any = { 
                role: 'assistant',
                content: `### 🚀 Auto-Dashboard Generado\n\nHe diseñado ${countText}${metricText} basándome en la estructura de tus datos.`,
                id: Date.now(),
                dashboardData: { metrics, charts }
            };

            setMessages(prev => [...prev, newMessage]);
        } catch (err: any) {
            alert("Error generando dashboard: " + (err.message || "Desconocido"));
        } finally {
            setLoadingAutoDash(false);
            setLoadingMessage("");
        }
    };

    const handleCleanData = async () => {
        if (!apiKey) {
            alert("Por favor, introduce tu API Key en la barra lateral.");
            return;
        }
        setCleaningData(true);
        try {
            const res = await cleanData(userId, apiKey, dataSource?.id, activeChatId || undefined, aiProvider, mistralKey);

            // Notificar éxito y actualizar columnas si es necesario (el backend ya las actualizó en la sesión)
            const newMessage: Message = {
                role: 'assistant',
                content: `### ✨ Limpieza con IA Completada\n\n${res.summary}\n\n*He actualizado el dataset. Ahora tiene ${res.rows} filas y ${res.columns.length} columnas.*`,
                id: Date.now()
            };

            setMessages(prev => [...prev, newMessage]);
        } catch (err: any) {
            alert("Error en la limpieza de datos: " + (err.message || "Desconocido"));
        } finally {
            setCleaningData(false);
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
        <div className="flex flex-col h-screen flex-1 bg-[var(--bg-primary)] overflow-hidden border-l border-[var(--border-color)]">
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
                    {dataSource && (
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

                        {dataSource && showAiSuggestions && (
                            <div className="grid grid-cols-1 gap-3 w-full max-w-md animate-in fade-in slide-in-from-bottom-8 duration-1000 delay-300">
                                <p className="text-[10px] font-black text-gray-700 uppercase tracking-widest mb-2">Sugerencias de la IA</p>
                                {loadingSuggestions ? (
                                    <div className="flex items-center gap-2 text-gray-700 animate-pulse">
                                        <Loader2 className="w-3 h-3 animate-spin" />
                                        <span className="text-[10px] uppercase font-bold tracking-tighter italic">Generando ideas estratégicas...</span>
                                    </div>
                                ) : (
                                    suggestions.map((sug, idx) => (
                                        <button
                                            key={idx}
                                            onClick={() => {
                                                setInput(sug);
                                                // Pequeño delay para que el usuario vea el texto en el input antes de enviar
                                                setTimeout(() => handleSendAsQuery(sug), 100);
                                            }}
                                            className="group flex items-center justify-between p-4 bg-[var(--bg-secondary)] hover:bg-[var(--bg-tertiary)] border border-[var(--border-color)] hover:border-blue-500/30 rounded-2xl text-left transition-all text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                                        >
                                            <span className="flex-1 pr-4">{sug}</span>
                                            <ChevronRight className="w-4 h-4 text-[var(--text-tertiary)] group-hover:text-blue-500 transition-colors" />
                                        </button>
                                    ))
                                )}
                            </div>
                        )}
                    </div>
                ) : (
                    messages.map((msg, i) => (
                        <div key={i} className={`flex gap-6 animate-in slide-in-from-bottom-4 duration-500 ${msg.role === 'user' ? 'justify-end' : ''}`}>
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
                    ))
                )}
                {loading && (
                    <div className="flex gap-6 animate-pulse">
                        <div className="w-10 h-10 rounded-2xl bg-blue-600 flex items-center justify-center">
                            <Bot className="w-6 h-6 text-white" />
                        </div>
                        <div className="bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-3xl rounded-tl-none px-6 py-4 flex items-center gap-4">
                            <div className="flex gap-1">
                                <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                                <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                                <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce"></span>
                            </div>
                            <span className="text-xs text-gray-500 font-bold uppercase tracking-widest italic">
                                {loadingMessage || "IA Analizando..."}
                            </span>
                        </div>
                    </div>
                )}
            </div>

            <div className="p-4 lg:p-8 pb-8 lg:pb-12 bg-gradient-to-t from-[var(--bg-primary)] via-[var(--bg-primary)] to-transparent">
                <div className="max-w-4xl mx-auto relative group">
                    <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-2xl blur opacity-20 group-hover:opacity-40 transition duration-1000 group-focus-within:opacity-50"></div>
                    <input
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                        placeholder={dataSource ? "Escribe tu pregunta estratégica..." : "Suba un archivo para comenzar..."}
                        disabled={!dataSource || loading}
                        className="relative w-full bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-2xl px-6 py-5 pr-16 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] focus:outline-none focus:border-blue-500/50 transition-all shadow-3xl disabled:opacity-50 disabled:cursor-not-allowed"
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

            <ReportBuilder
                isOpen={reportBuilderOpen}
                onClose={() => setReportBuilderOpen(false)}
                messages={messages}
                userId={userId}
            />

        </div>
    );
}
