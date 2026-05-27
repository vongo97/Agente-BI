'use client';

import React, { useState, useEffect } from 'react';
import { useDashboard } from '@/context/DashboardContext';
import { generateVisualSummary } from '@/lib/api';
import { MermaidPreview } from './MermaidPreview';
import { Sparkles, Brain, RefreshCw, AlertCircle, FileText, ChevronDown, Zap, Info } from 'lucide-react';

// Formato de salida esperado de la API
interface VisualSummaryResult {
    title: string;
    summary: string[];
    key_points: string[];
    visual_type: 'flowchart' | 'mindmap' | 'timeline' | 'comparison' | 'architecture';
    mermaid: string;
    confidence: 'low' | 'medium' | 'high';
}

const EMPTY_CHAT_MESSAGE = 'No hay mensajes del asistente en el chat actual. Sube un dataset, realiza una pregunta en el chat, o selecciona "Texto Manual" para escribir aqui.';

function isVisualSummaryResult(value: unknown): value is VisualSummaryResult {
    if (!value || typeof value !== 'object') return false;

    const candidate = value as Partial<VisualSummaryResult>;
    return (
        typeof candidate.title === 'string' &&
        Array.isArray(candidate.summary) &&
        Array.isArray(candidate.key_points) &&
        typeof candidate.visual_type === 'string' &&
        typeof candidate.mermaid === 'string' &&
        typeof candidate.confidence === 'string'
    );
}

function getErrorMessage(error: unknown) {
    return error instanceof Error ? error.message : "Error al procesar el resumen visual. Intenta nuevamente.";
}

export function VisualSummaryView() {
    const { messages, apiKey, mistralKey, aiProvider, setSidebarOpen, userId } = useDashboard();
    
    // Estados principales
    const [inputText, setInputText] = useState<string>('');
    const [sourceType, setSourceType] = useState<'chat' | 'manual'>('chat');
    const [visualType, setVisualType] = useState<string>('auto'); // auto, flowchart, mindmap, timeline, comparison, architecture
    const [generationMode, setGenerationMode] = useState<'rapido' | 'calidad'>('rapido');
    
    const [loading, setLoading] = useState<boolean>(false);
    const [loadingMessage, setLoadingMessage] = useState<string>('');
    const [error, setError] = useState<string | null>(null);
    const [result, setResult] = useState<VisualSummaryResult | null>(null);
    
    // Notificaciones locales
    const [showQualityAlert, setShowQualityAlert] = useState<boolean>(false);

    // Intentar autocompletar el texto del chat actual si está seleccionado
    useEffect(() => {
        if (sourceType === 'chat') {
            const lastAssistantMessages = messages
                .filter(m => m.role === 'assistant')
                .map(m => m.content)
                .join('\n\n');
            
            // Limpiar marcas markdown pesadas
            const cleanText = lastAssistantMessages
                .replace(/```[\s\S]*?```/g, '') // Quitar bloques de código
                .replace(/[#*`]/g, '') // Quitar formato
                .trim();

            setInputText(cleanText || EMPTY_CHAT_MESSAGE);
        }
    }, [sourceType, messages]);

    // Generar un hash simple para usar de clave en la caché
    const getCacheKey = (text: string, type: string, mode: string) => {
        const normalizedText = text.trim().slice(0, 1000).toLowerCase();
        // Generar un hash numérico simple (Fowler-Noll-Vo 1a alternativo o similar)
        let hash = 0;
        for (let i = 0; i < normalizedText.length; i++) {
            hash = (hash << 5) - hash + normalizedText.charCodeAt(i);
            hash |= 0;
        }
        return `vektra-vs-cache-${hash}-${type}-${mode}`;
    };

    const handleGenerate = async () => {
        if (!inputText.trim() || loading) return;
        if (inputText === EMPTY_CHAT_MESSAGE) {
            setError("No hay contenido del chat para resumir. Usa Texto Manual o genera primero una respuesta en el chat.");
            return;
        }

        const cacheKey = getCacheKey(inputText, visualType, generationMode);
        
        // 1. Verificar Caché local
        const cached = localStorage.getItem(cacheKey);
        if (cached) {
            try {
                const parsed = JSON.parse(cached);
                if (isVisualSummaryResult(parsed)) {
                    setResult(parsed);
                    setError(null);
                    return;
                }
                localStorage.removeItem(cacheKey);
            } catch {
                localStorage.removeItem(cacheKey); // Caché corrupta, la removemos
            }
        }

        setLoading(true);
        setError(null);
        
        // Mensajes dinámicos de carga
        if (generationMode === 'calidad') {
            setLoadingMessage("🧠 Pipeline Calidad: Iniciando análisis semántico del texto...");
            setShowQualityAlert(true);
        } else {
            setLoadingMessage("🔄 Pipeline Rápido: Sintetizando visualización en una llamada...");
        }

        // Simular cambio de mensajes de carga para dinamizar la interfaz
        const timer1 = setTimeout(() => {
            if (generationMode === 'calidad') {
                setLoadingMessage("🎨 Pipeline Calidad: Planificando estructura visual...");
            } else {
                setLoadingMessage("🧩 Generando diagrama Mermaid...");
            }
        }, 1500);

        const timer2 = setTimeout(() => {
            setLoadingMessage("✨ Validando consistencia del JSON y Mermaid...");
        }, 3500);

        try {
            const apiVisualType = visualType === 'auto' ? undefined : visualType;
            const res = await generateVisualSummary(
                inputText,
                apiKey,
                userId,
                aiProvider,
                mistralKey,
                apiVisualType,
                generationMode
            );

            // Guardar en caché
            if (!isVisualSummaryResult(res)) {
                throw new Error("La respuesta del servidor no tiene el formato esperado para el resumen visual.");
            }

            localStorage.setItem(cacheKey, JSON.stringify(res));
            
            setResult(res);
            setError(null);
        } catch (err: unknown) {
            console.error(err);
            setError(getErrorMessage(err));
        } finally {
            clearTimeout(timer1);
            clearTimeout(timer2);
            setLoading(false);
            setLoadingMessage("");
        }
    };

    const handleReset = () => {
        setResult(null);
        setError(null);
        if (sourceType === 'manual') {
            setInputText('');
        }
    };

    return (
        <div className="flex flex-col h-screen flex-1 bg-[var(--bg-primary)] overflow-hidden border-l border-[var(--border-color)]">
            {/* Header */}
            <header className="px-6 py-5 border-b border-[var(--border-color)] flex items-center justify-between bg-black/5">
                <div className="flex items-center gap-3">
                    <button
                        onClick={() => setSidebarOpen(true)}
                        className="lg:hidden p-2 text-gray-500 hover:text-white"
                    >
                        <ChevronDown className="w-5 h-5 -rotate-90" />
                    </button>
                    <div>
                        <div className="flex items-center gap-2">
                            <h2 className="text-lg font-black tracking-tight text-white italic">Resumen Visual</h2>
                            <span className="text-[9px] bg-blue-500/20 text-blue-400 py-0.5 px-2 rounded-full font-bold uppercase tracking-wider animate-pulse">Experimental</span>
                        </div>
                        <p className="text-[10px] text-gray-500 font-medium">Convierte ideas complejas y chats en diagramas estilo Napkin AI</p>
                    </div>
                </div>
            </header>

            {/* Layout Principal */}
            <div className="flex-1 overflow-y-auto p-6 lg:p-8 space-y-6 lg:space-y-0 lg:grid lg:grid-cols-12 lg:gap-8 h-full custom-scrollbar">
                {/* Columna Izquierda: Configuración e Inputs */}
                <div className="lg:col-span-5 flex flex-col space-y-6">
                    {/* Selector de Fuente */}
                    <div className="bg-[var(--bg-secondary)] border border-[var(--border-color)] p-6 rounded-3xl space-y-4 shadow-xl">
                        <div className="flex items-center justify-between">
                            <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest flex items-center gap-2">
                                <FileText className="w-3.5 h-3.5" /> Fuente de Contenido
                            </label>
                            <div className="flex bg-black/30 p-1 rounded-xl border border-white/5">
                                <button
                                    onClick={() => setSourceType('chat')}
                                    className={`px-3 py-1 text-[9px] font-black uppercase tracking-wider rounded-lg transition-all ${sourceType === 'chat' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'}`}
                                >
                                    Chat Activo
                                </button>
                                <button
                                    onClick={() => setSourceType('manual')}
                                    className={`px-3 py-1 text-[9px] font-black uppercase tracking-wider rounded-lg transition-all ${sourceType === 'manual' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'}`}
                                >
                                    Texto Manual
                                </button>
                            </div>
                        </div>

                        <div className="relative">
                            <textarea
                                value={inputText}
                                onChange={(e) => {
                                    if (sourceType === 'manual') setInputText(e.target.value);
                                }}
                                disabled={sourceType === 'chat'}
                                placeholder="Escribe o pega aquí el contenido que deseas estructurar visualmente..."
                                className="w-full min-h-[160px] max-h-[220px] bg-black/40 border border-white/5 rounded-2xl p-4 text-xs text-gray-300 focus:outline-none focus:border-blue-500/50 disabled:opacity-70 disabled:cursor-not-allowed custom-scrollbar leading-relaxed"
                            />
                            {sourceType === 'chat' && (
                                <div className="absolute top-2 right-2 bg-blue-500/10 border border-blue-500/20 text-blue-400 py-0.5 px-2 rounded-lg text-[8px] font-black uppercase tracking-wider">
                                    Sincronizado
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Parámetros de Generación */}
                    <div className="bg-[var(--bg-secondary)] border border-[var(--border-color)] p-6 rounded-3xl space-y-6 shadow-xl">
                        <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest flex items-center gap-2">
                            <Brain className="w-3.5 h-3.5" /> Parámetros del Motor LLM
                        </label>

                        {/* Selector Tipo Visual */}
                        <div className="space-y-2">
                            <div className="flex justify-between items-center">
                                <span className="text-[10px] font-bold text-gray-400 uppercase">Tipo Visual Recomendado</span>
                                <span className="text-[8px] text-gray-500 italic">Forzar formato</span>
                            </div>
                            <select
                                value={visualType}
                                onChange={(e) => setVisualType(e.target.value)}
                                className="w-full bg-black border border-white/10 rounded-xl px-4 py-3 text-xs text-white focus:outline-none focus:border-blue-500/50 cursor-pointer"
                            >
                                <option value="auto">Auto-detectar (Recomendado)</option>
                                <option value="flowchart">Flowchart (Pasos y Decisiones)</option>
                                <option value="mindmap">Mindmap (Conceptos e Ideas)</option>
                                <option value="timeline">Timeline (Cronologías y Fechas)</option>
                                <option value="comparison">Comparison (Pros y Contras)</option>
                                <option value="architecture">Architecture (Componentes y Redes)</option>
                            </select>
                        </div>

                        {/* Selector Modo Dual */}
                        <div className="space-y-3">
                            <span className="text-[10px] font-bold text-gray-400 uppercase block">Modo de Procesamiento</span>
                            <div className="grid grid-cols-2 gap-3">
                                <button
                                    onClick={() => setGenerationMode('rapido')}
                                    className={`flex flex-col items-start p-3 border rounded-2xl text-left transition-all ${generationMode === 'rapido' ? 'bg-blue-600/10 border-blue-500/40 text-white' : 'bg-black/20 border-white/5 text-gray-500 hover:text-gray-300'}`}
                                >
                                    <div className="flex items-center gap-1 mb-1">
                                        <Zap className="w-3.5 h-3.5 text-yellow-400" />
                                        <span className="text-[10px] font-black uppercase tracking-wider">Rápido</span>
                                    </div>
                                    <span className="text-[8px] text-gray-500 font-medium leading-normal">Una llamada rápida. Menor costo y respuesta directa.</span>
                                </button>

                                <button
                                    onClick={() => {
                                        setGenerationMode('calidad');
                                        setShowQualityAlert(true);
                                    }}
                                    className={`flex flex-col items-start p-3 border rounded-2xl text-left transition-all relative overflow-hidden ${generationMode === 'calidad' ? 'bg-indigo-600/10 border-indigo-500/40 text-white' : 'bg-black/20 border-white/5 text-gray-500 hover:text-gray-300'}`}
                                >
                                    <div className="flex items-center gap-1 mb-1">
                                        <Brain className="w-3.5 h-3.5 text-purple-400" />
                                        <span className="text-[10px] font-black uppercase tracking-wider">Calidad (F1)</span>
                                    </div>
                                    <span className="text-[8px] text-gray-500 font-medium leading-normal">Optimizado. Deja listo el pipeline. Fallback seguro.</span>
                                </button>
                            </div>

                            {/* Alertas explicativas de Modo Calidad */}
                            {showQualityAlert && generationMode === 'calidad' && (
                                <div className="p-3 bg-indigo-500/10 border border-indigo-500/20 rounded-xl flex gap-2.5 items-start animate-in fade-in slide-in-from-top-1">
                                    <Info className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                                    <div className="space-y-1">
                                        <p className="text-[9px] text-indigo-200 font-bold uppercase tracking-wider">Arquitectura Dual Activada</p>
                                        <p className="text-[8px] text-gray-400 leading-relaxed">El Modo Calidad está en fase experimental. Para Fase 1, ejecutaremos un fallback transparente al motor rápido optimizado con validación extendida.</p>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Botones de acción */}
                        <div className="pt-2 flex gap-3">
                            <button
                                onClick={handleGenerate}
                                disabled={loading || !inputText.trim() || inputText === EMPTY_CHAT_MESSAGE}
                                className="flex-1 py-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:from-blue-800 disabled:to-indigo-800 disabled:opacity-50 disabled:cursor-not-allowed text-white text-[10px] font-black uppercase tracking-widest rounded-2xl shadow-lg shadow-blue-500/15 flex items-center justify-center gap-2 transition-all hover:scale-[1.02]"
                            >
                                {loading ? (
                                    <>
                                        <RefreshCw className="w-4 h-4 animate-spin" />
                                        <span>Procesando...</span>
                                    </>
                                ) : (
                                    <>
                                        <Sparkles className="w-4 h-4" />
                                        <span>Generar Resumen Visual</span>
                                    </>
                                )}
                            </button>

                            {result && (
                                <button
                                    onClick={handleReset}
                                    className="px-4 py-4 bg-[var(--bg-tertiary)] border border-[var(--border-color)] hover:bg-white/5 text-gray-400 hover:text-white rounded-2xl transition-all"
                                    title="Limpiar"
                                >
                                    <RefreshCw className="w-4 h-4" />
                                </button>
                            )}
                        </div>

                        {/* Estado Carga */}
                        {loading && (
                            <div className="p-4 bg-blue-600/5 border border-blue-500/15 rounded-2xl flex items-center gap-3 animate-pulse">
                                <LoaderIcon />
                                <span className="text-[10px] text-blue-400 font-black uppercase tracking-wider">{loadingMessage || "Analizando contenido..."}</span>
                            </div>
                        )}

                        {/* Estado Error */}
                        {error && (
                            <div className="p-4 bg-red-600/10 border border-red-500/20 rounded-2xl flex gap-3 items-start animate-in shake duration-500">
                                <AlertCircle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                                <div className="space-y-1">
                                    <p className="text-[9px] text-red-400 font-bold uppercase tracking-wider">Error del Sistema</p>
                                    <p className="text-[9px] text-gray-400 leading-normal">{error}</p>
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                {/* Columna Derecha: Previsualización de Diagrama */}
                <div className="lg:col-span-7 flex flex-col h-full space-y-6">
                    {result ? (
                        <div className="flex-1 flex flex-col space-y-6 h-full animate-in fade-in duration-500">
                            {/* Información del Resumen */}
                            <div className="bg-[var(--bg-secondary)] border border-[var(--border-color)] p-6 rounded-3xl space-y-4 shadow-xl">
                                <div className="flex justify-between items-start gap-4">
                                    <h3 className="text-md font-bold text-white tracking-tight">{result.title}</h3>
                                    <div className="flex gap-2">
                                        <span className={`text-[8px] py-1 px-2.5 rounded-full font-black uppercase tracking-wider ${
                                            result.confidence === 'high' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                                            result.confidence === 'medium' ? 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20' :
                                            'bg-red-500/10 text-red-400 border border-red-500/20'
                                        }`}>
                                            Confianza: {result.confidence}
                                        </span>
                                        <span className="text-[8px] bg-blue-500/10 text-blue-400 border border-blue-500/20 py-1 px-2.5 rounded-full font-black uppercase tracking-wider">
                                            {result.visual_type}
                                        </span>
                                    </div>
                                </div>

                                <div className="grid md:grid-cols-2 gap-4 pt-2 border-t border-[var(--border-color)]">
                                    <div className="space-y-2">
                                        <span className="text-[9px] font-black text-gray-500 uppercase tracking-widest">Resumen Ejecutivo</span>
                                        <ul className="space-y-1.5">
                                            {result.summary.map((s, i) => (
                                                <li key={i} className="text-[11px] text-gray-300 leading-relaxed flex gap-2">
                                                    <span className="text-blue-500 mt-1 shrink-0">•</span>
                                                    <span>{s}</span>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>

                                    <div className="space-y-2">
                                        <span className="text-[9px] font-black text-gray-500 uppercase tracking-widest">Ideas Clave</span>
                                        <ul className="space-y-1.5">
                                            {result.key_points.map((k, i) => (
                                                <li key={i} className="text-[11px] text-gray-300 leading-relaxed flex gap-2">
                                                    <span className="text-indigo-500 mt-1 shrink-0">▪</span>
                                                    <span>{k}</span>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                </div>
                            </div>

                            {/* Renderizador de Mermaid */}
                            <div className="flex-1 min-h-[400px]">
                                <MermaidPreview code={result.mermaid} />
                            </div>
                        </div>
                    ) : (
                        <div className="flex-1 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-3xl flex flex-col items-center justify-center text-center p-8 min-h-[450px] shadow-xl">
                            <div className="relative mb-6">
                                <div className="absolute inset-0 bg-blue-600/10 blur-3xl rounded-full animate-pulse"></div>
                                <div className="w-16 h-16 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-2xl flex items-center justify-center relative shadow-2xl">
                                    <Brain className="w-8 h-8 text-white" />
                                </div>
                            </div>
                            <div className="space-y-3 max-w-sm">
                                <h3 className="text-md font-bold text-white uppercase tracking-wider">Capa Napkin AI Activa</h3>
                                <p className="text-xs text-gray-500 leading-relaxed">Genera resúmenes ejecutivos e ideas estructuradas y dibújalas automáticamente con diagramas dinámicos de Mermaid.js.</p>
                            </div>
                            <div className="mt-8 grid grid-cols-3 gap-3 w-full max-w-md">
                                <div className="p-3 bg-black/10 rounded-xl border border-white/5">
                                    <span className="text-[8px] font-black text-blue-400 uppercase tracking-wider block mb-1">1. Analiza</span>
                                    <span className="text-[8px] text-gray-600 leading-normal block">Procesa el contexto semántico del chat actual.</span>
                                </div>
                                <div className="p-3 bg-black/10 rounded-xl border border-white/5">
                                    <span className="text-[8px] font-black text-indigo-400 uppercase tracking-wider block mb-1">2. Estructura</span>
                                    <span className="text-[8px] text-gray-600 leading-normal block">Extrae ideas clave y diseña un mapa de nodos.</span>
                                </div>
                                <div className="p-3 bg-black/10 rounded-xl border border-white/5">
                                    <span className="text-[8px] font-black text-purple-400 uppercase tracking-wider block mb-1">3. Renderiza</span>
                                    <span className="text-[8px] text-gray-600 leading-normal block">Mermaid dibuja un diagrama interactivo al instante.</span>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

function LoaderIcon() {
    return (
        <div className="flex gap-1 shrink-0">
            <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
            <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
            <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce"></span>
        </div>
    );
}
