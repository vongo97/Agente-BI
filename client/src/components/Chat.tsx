'use client';

import { useState, useRef, useEffect, useCallback } from "react";
import { useSession } from "next-auth/react";
import { Bot, BarChart3, Database, TrendingUp, Search } from "lucide-react";
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

    const fetchSuggestions = useCallback(async () => {
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
    }, [apiKey, dataSources, userId, activeChatId, aiProvider, mistralKey, setLoadingSuggestions, setSuggestions]);

    useEffect(() => {
        const canFetch = dataSources.length > 0 && apiKey && showAiSuggestions;
        if (canFetch && (messages.length === 0 || autoSuggestionsEnabled)) {
            fetchSuggestions();
        } else if (dataSources.length === 0 || !showAiSuggestions) {
            if (suggestions.length > 0) setSuggestions([]);
        }
    }, [dataSources.length, apiKey, showAiSuggestions, autoSuggestionsEnabled, messages.length, suggestions.length, fetchSuggestions, setSuggestions]);

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

        if (aiProvider === 'mistral') setLoadingMessage("✍️ Redactando diagnóstico de negocio...");
        else if (aiProvider === 'groq') setLoadingMessage("⚡ Ejecutando debate ultraveloz...");
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
        } catch (error) {
            const err = error as Error;
            setMessages(prev => [...prev, { 
                role: 'assistant', 
                content: `⚠️ Error interno: ${err.message || "Fallo en el procesamiento."}` 
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
            const newMessage: Message = { 
                role: 'assistant',
                content: `### 🚀 Auto-Dashboard Generado\n\nHe diseñado ${charts.length} gráficos estratégicos y ${metrics.length} métricas clave.`,
                id: Date.now(),
                dashboardData: { metrics, charts }
            };
            setMessages(prev => [...prev, newMessage]);
        } catch (err) {
            const error = err as Error;
            alert("Error generando dashboard: " + (error.message || "Desconocido"));
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
        } catch (err) {
            const error = err as Error;
            alert("Error en la limpieza de datos: " + (error.message || "Desconocido"));
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
            console.error("Error pinning item:", error);
            alert("Error al anclar");
        }
    };

    const handleExportPng = async (fig: unknown, name: string) => {
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
            console.error("Error exporting png:", error);
            alert("Error al exportar imagen");
        }
    };

    return (
        <div className="flex flex-col h-screen flex-1 bg-[var(--bi-canvas)] overflow-hidden border-l border-[var(--bi-border)]">
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

            <div className="flex-1 overflow-y-auto px-4 py-5 lg:px-8 space-y-5 custom-scrollbar" ref={scrollRef}>
                {messages.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center gap-8 animate-in fade-in duration-500">
                        {/* Empty state — workspace style */}
                        <div className="text-center max-w-sm">
                            <div className="inline-flex items-center justify-center w-12 h-12 rounded-lg bg-[var(--bi-surface-0)] border border-[var(--bi-border)] mb-4">
                                <BarChart3 className="w-5 h-5 text-[var(--bi-teal)]" />
                            </div>
                            <h2 className="text-base font-semibold text-[var(--bi-text-1)] mb-1">
                                Analista BI listo
                            </h2>
                            <p className="text-sm text-[var(--bi-text-2)] leading-relaxed">
                                {dataSources.length === 0
                                    ? "Sube un archivo CSV o Excel desde la barra lateral para comenzar el análisis."
                                    : "Haz una pregunta sobre tus datos. Puedes pedir gráficos, métricas, resúmenes o comparativas."}
                            </p>
                        </div>

                        {/* Capability hints */}
                        {dataSources.length > 0 && (
                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 w-full max-w-lg">
                                {[
                                    { icon: TrendingUp, label: "Tendencias", hint: "Evolución de métricas clave" },
                                    { icon: Search, label: "Segmentación", hint: "Análisis por categoría o período" },
                                    { icon: Database, label: "Resumen", hint: "KPIs y estadísticas del dataset" },
                                ].map(({ icon: Icon, label, hint }) => (
                                    <div
                                        key={label}
                                        className="flex flex-col gap-1 px-3 py-2.5 rounded-lg border border-[var(--bi-border)] bg-[var(--bi-surface-0)]"
                                    >
                                        <div className="flex items-center gap-1.5 text-[var(--bi-text-2)]">
                                            <Icon className="w-3.5 h-3.5 text-[var(--bi-teal)]" />
                                            <span className="text-xs font-semibold">{label}</span>
                                        </div>
                                        <p className="text-[10px] text-[var(--bi-text-3)] leading-snug">{hint}</p>
                                    </div>
                                ))}
                            </div>
                        )}

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
                            handleSendAsQuery={handleSendAsQuery}
                        />
                    ))
                )}

                {/* Loading indicator — inline, compact */}
                {loading && (
                    <div className="flex items-start gap-3">
                        <div className="w-7 h-7 rounded-md bg-[var(--bi-teal-dim)] border border-[var(--bi-teal-border)] flex items-center justify-center flex-shrink-0 mt-0.5">
                            <Bot className="w-4 h-4 text-[var(--bi-teal)]" />
                        </div>
                        <div className="flex items-center gap-3 px-4 py-2.5 rounded-lg bg-[var(--bi-surface-0)] border border-[var(--bi-border)]">
                            <div className="flex gap-0.5">
                                <span className="w-1 h-1 bg-[var(--bi-teal)] rounded-full animate-bounce [animation-delay:-0.3s]" />
                                <span className="w-1 h-1 bg-[var(--bi-teal)] rounded-full animate-bounce [animation-delay:-0.15s]" />
                                <span className="w-1 h-1 bg-[var(--bi-teal)] rounded-full animate-bounce" />
                            </div>
                            <span className="text-xs text-[var(--bi-text-2)]">
                                {loadingMessage || "Analizando…"}
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
