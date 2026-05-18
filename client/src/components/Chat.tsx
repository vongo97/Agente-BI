'use client';

import { useState, useRef, useEffect } from "react";
import { useSession } from "next-auth/react";
import { Bot, Loader2, BarChart3 } from "lucide-react";
import { analyzeData, pinToDashboard, exportChartAsPng, generateAutoDashboard, suggestQuestions, cleanData } from "@/lib/api";
import { useDashboard, Message } from "@/context/DashboardContext";
import { ReportBuilder } from "./ReportBuilder";

// Sub-componentes refactorizados
import { ChatHeader } from "./chat/ChatHeader";
import { MessageItem } from "./chat/MessageItem";
import { ChatSuggestions } from "./chat/ChatSuggestions";
import { ChatInput } from "./chat/ChatInput";

export function Chat() {
    const { data: session } = useSession();
    const {
        apiKey,
        mistralKey,
        aiProvider,
        dataSources,
        setSidebarOpen,
        messages,
        setMessages,
        activeChatId,
        setActiveChatId,
        suggestions,
        setSuggestions,
        loadingSuggestions,
        setLoadingSuggestions,
        showAiSuggestions,
        autoSuggestionsEnabled
    } = useDashboard();
    
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [loadingMessage, setLoadingMessage] = useState("");
    const [cleaningData, setCleaningData] = useState(false);
    const [loadingAutoDash, setLoadingAutoDash] = useState(false);
    const [reportBuilderOpen, setReportBuilderOpen] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);

    const userId = session?.user?.email || "default_user";
    const userName = session?.user?.name || userId;

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    useEffect(() => {
        const canFetch = dataSources.length > 0 && apiKey && showAiSuggestions;
        if (canFetch && (messages.length === 0 || autoSuggestionsEnabled)) {
            fetchSuggestions();
        } else if (dataSources.length === 0 || !showAiSuggestions) {
            if (suggestions.length > 0) setSuggestions([]);
        }
    }, [dataSources.length, apiKey, showAiSuggestions, autoSuggestionsEnabled]);

    const fetchSuggestions = async () => {
        if (!apiKey || dataSources.length === 0) return;
        setLoadingSuggestions(true);
        try {
            const mainSourceId = dataSources[dataSources.length - 1].id;
            const res = await suggestQuestions(userId, apiKey, mainSourceId, activeChatId || undefined, aiProvider, mistralKey);
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
        if (dataSources.length === 0) {
            alert("Por favor, sube al menos una fuente de datos primero.");
            return;
        }

        const userMsg: Message = { role: 'user', content: queryText };
        setMessages(prev => [...prev, userMsg]);
        setInput("");
        setLoading(true);

        if (aiProvider === 'hybrid') setLoadingMessage("🔄 Extrayendo inteligencia estratégica...");
        else if (aiProvider === 'mistral') setLoadingMessage("✍️ Redactando diagnóstico de negocio...");
        else setLoadingMessage("🧩 Orquestando hallazgos...");

        try {
            const mainSourceId = dataSources[0].id;
            const res = await analyzeData(queryText, apiKey, userId, activeChatId || undefined, mainSourceId, aiProvider, mistralKey);

            const assistantMsg: Message = {
                id: res.message_id,
                role: 'assistant',
                content: res.analysis || "He procesado tu solicitud.",
                fig: res.figure
            };
            setMessages(prev => [...prev, assistantMsg]);

            if (!activeChatId && res.chat_id) setActiveChatId(res.chat_id);
        } catch (error: any) {
            setMessages(prev => [...prev, { 
                role: 'assistant', 
                content: `⚠️ Error interno: ${error.message || "Fallo en el procesamiento."}` 
            }]);
        } finally {
            setLoading(false);
            setLoadingMessage("");
        }
    };

    const handleAutoDash = async () => {
        if (dataSources.length === 0 || !apiKey) {
            alert("Necesitas datos y API Key.");
            return;
        }
        setLoadingAutoDash(true);
        setLoadingMessage("📊 Analizando tu dataset...");
        try {
            const res = await generateAutoDashboard(apiKey, userId, dataSources[0].id, activeChatId || undefined, aiProvider, mistralKey);
            const { metrics = [], charts = [] } = res;
            const newMessage: any = { 
                role: 'assistant',
                content: `### 🚀 Auto-Dashboard Generado\n\nHe diseñado ${charts.length} gráficos estratégicos y ${metrics.length} métricas clave.`,
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
            const res = await cleanData(userId, apiKey, dataSources[0].id, activeChatId || undefined, aiProvider, mistralKey);
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
            <ChatHeader 
                setSidebarOpen={setSidebarOpen}
                dataSources={dataSources}
                cleaningData={cleaningData}
                handleCleanData={handleCleanData}
                loadingAutoDash={loadingAutoDash}
                handleAutoDash={handleAutoDash}
                messages={messages}
                setReportBuilderOpen={setReportBuilderOpen}
                activeChatId={activeChatId}
                userId={userId}
                handleNewChat={() => { setMessages([]); setActiveChatId(null); }}
                aiProvider={aiProvider}
            />

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

                        <ChatSuggestions 
                            showAiSuggestions={showAiSuggestions}
                            loadingSuggestions={loadingSuggestions}
                            suggestions={suggestions}
                            setInput={setInput}
                            handleSendAsQuery={handleSendAsQuery}
                            fetchSuggestions={fetchSuggestions}
                        />
                    </div>
                ) : (
                    messages.map((msg, i) => (
                        <MessageItem 
                            key={i} 
                            msg={msg} 
                            userId={userId} 
                            handleExportPng={handleExportPng} 
                            handlePin={handlePin} 
                        />
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

            <ChatInput 
                input={input}
                setInput={setInput}
                handleSend={handleSend}
                loading={loading}
                dataSourcesCount={dataSources.length}
            />

            <ReportBuilder
                isOpen={reportBuilderOpen}
                onClose={() => setReportBuilderOpen(false)}
                messages={messages}
                userId={userId}
                userName={userName}
            />
        </div>
    );
}
