'use client';

import { useState } from "react";
import { Settings, Key, Cpu, Shield, Save, CheckCircle2, AlertCircle, Sparkles, Menu, Palette, Sliders, Activity, Eye, EyeOff, FileText, Columns } from "lucide-react";
import { useDashboard } from "@/context/DashboardContext";
import { validateApiKey } from "@/lib/api";

type TabType = "ai" | "security" | "appearance";

export function SettingsView() {
    const { 
        apiKey, setApiKey, 
        mistralKey, setMistralKey, 
        groqKey, setGroqKey, 
        aiProvider, setAiProvider, 
        autoSuggestionsEnabled, setAutoSuggestionsEnabled, 
        setSidebarOpen,
        temperature, setTemperature,
        anomalySensitivity, setAnomalySensitivity,
        magicCleanStrategy, setMagicCleanStrategy,
        currencyFormat, setCurrencyFormat,
        dateFormat, setDateFormat,
        brandColor, setBrandColor,
        reportOrgName, setReportOrgName,
        reportFooterText, setReportFooterText,
        pdfOrientation, setPdfOrientation,
        pdfIncludeDataTable, setPdfIncludeDataTable,
        chartTheme, setChartTheme
    } = useDashboard();

    const [status, setStatus] = useState<"idle" | "saving" | "success" | "error">("idle");
    const [msg, setMsg] = useState("");
    const [activeTab, setActiveTab] = useState<TabType>("ai");
    
    // States for toggling visibility of API keys
    const [showGeminiKey, setShowGeminiKey] = useState(false);
    const [showMistralKey, setShowMistralKey] = useState(false);
    const [showGroqKey, setShowGroqKey] = useState(false);

    const handleSave = async () => {
        setStatus("saving");
        try {
            // Validar Gemini
            if (apiKey && apiKey.length > 10 && !apiKey.includes("...")) {
                const res = await validateApiKey(apiKey, "gemini");
                if (!res.valid) {
                    throw new Error(res.error || "API Key de Gemini rechazada por el servidor.");
                }
            }
            
            // Validar Mistral (opcional)
            if (mistralKey && mistralKey.length > 10 && !mistralKey.includes("...")) {
                const res = await validateApiKey(mistralKey, "mistral");
                if (!res.valid) {
                    throw new Error(res.error || "API Key de Mistral rechazada por el servidor.");
                }
            }
            
            // Validar Groq (opcional)
            if (groqKey && groqKey.length > 10 && !groqKey.includes("...")) {
                const res = await validateApiKey(groqKey, "groq");
                if (!res.valid) {
                    throw new Error(res.error || "API Key de Groq rechazada por el servidor.");
                }
            }

            setStatus("success");
            setMsg("Configuración guardada correctamente");
            setTimeout(() => setStatus("idle"), 3000);
        } catch (err) {
            const error = err as Error;
            setStatus("error");
            setMsg(error.message || "Error al validar llaves");
        }
    };

    return (
        <div className="flex-1 bg-[var(--bi-canvas)] p-4 sm:p-8 lg:p-12 overflow-y-auto custom-scrollbar">
            <div className="max-w-5xl mx-auto space-y-6 lg:space-y-8 pb-12">
                {/* Header Section */}
                <header className="space-y-4">
                    <div className="flex items-center gap-3 lg:gap-4">
                        <button
                            onClick={() => setSidebarOpen(true)}
                            className="lg:hidden p-2 rounded-md text-[var(--bi-text-3)] hover:text-[var(--bi-text-1)] hover:bg-[var(--bi-surface-1)] active:bg-[var(--bi-surface-2)] transition-all duration-200 cursor-pointer"
                            aria-label="Abrir menú"
                        >
                            <Menu className="w-5 h-5" />
                        </button>
                        <div className="p-3 bg-[var(--bi-blue-dim)] border border-[var(--bi-blue-border)] rounded-xl hidden sm:block backdrop-blur-sm">
                            <Settings className="w-5 h-5 text-[var(--bi-blue)]" />
                        </div>
                        <div>
                            <h1 className="text-2xl font-bold text-[var(--bi-text-1)] tracking-tight">Ajustes del Sistema</h1>
                            <p className="text-xs text-[var(--bi-text-3)] font-medium mt-1">Configura motores, seguridad y apariencia de Vektra BI.</p>
                        </div>
                    </div>
                </header>

                {/* Tabs Navigation */}
                <div className="flex overflow-x-auto custom-scrollbar space-x-2 border-b border-[var(--bi-border)] pb-2">
                    <button 
                        onClick={() => setActiveTab("ai")}
                        className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs font-semibold transition-all whitespace-nowrap ${activeTab === 'ai' ? 'bg-[var(--bi-surface-2)] text-[var(--bi-text-1)] border border-[var(--bi-border)] shadow-sm' : 'text-[var(--bi-text-3)] hover:text-[var(--bi-text-2)] hover:bg-[var(--bi-surface-1)]'}`}
                    >
                        <Cpu className="w-4 h-4" /> Inteligencia Artificial
                    </button>
                    <button 
                        onClick={() => setActiveTab("security")}
                        className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs font-semibold transition-all whitespace-nowrap ${activeTab === 'security' ? 'bg-[var(--bi-surface-2)] text-[var(--bi-text-1)] border border-[var(--bi-border)] shadow-sm' : 'text-[var(--bi-text-3)] hover:text-[var(--bi-text-2)] hover:bg-[var(--bi-surface-1)]'}`}
                    >
                        <Key className="w-4 h-4" /> Seguridad y Llaves
                    </button>
                    <button 
                        onClick={() => setActiveTab("appearance")}
                        className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs font-semibold transition-all whitespace-nowrap ${activeTab === 'appearance' ? 'bg-[var(--bi-surface-2)] text-[var(--bi-text-1)] border border-[var(--bi-border)] shadow-sm' : 'text-[var(--bi-text-3)] hover:text-[var(--bi-text-2)] hover:bg-[var(--bi-surface-1)]'}`}
                    >
                        <Palette className="w-4 h-4" /> Personalización y Reportes
                    </button>
                </div>

                {/* Main Content Area */}
                <div className="grid grid-cols-1 gap-6 lg:gap-8 min-h-[50vh]">
                    
                    {/* --- TAB: AI & ANALYSIS --- */}
                    {activeTab === "ai" && (
                        <div className="space-y-6 lg:space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                            <div className="bg-[var(--bi-surface-0)] border border-[var(--bi-border)] rounded-xl p-6 lg:p-8 backdrop-blur-md shadow-sm">
                                <div className="flex items-center gap-3 border-b border-[var(--bi-border)] pb-4 lg:pb-6 mb-6 lg:mb-8">
                                    <Cpu className="w-5 h-5 text-[var(--bi-blue)]" />
                                    <h2 className="text-sm font-semibold text-[var(--bi-text-1)] uppercase tracking-widest">Motor Analítico Principal</h2>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                    {[
                                        { id: 'gemini', name: 'Google Gemini', desc: 'Rendimiento Extremo (Flash 3)', activeClass: 'border-[var(--bi-blue-border)] bg-[var(--bi-blue-dim)] text-[var(--bi-blue)] ring-1 ring-[var(--bi-blue-border)] shadow-[0_0_15px_rgba(45,212,191,0.1)]' },
                                        { id: 'mistral', name: 'Mistral AI', desc: 'Precisión Estratégica (Large)', activeClass: 'border-[var(--bi-teal-border)] bg-[var(--bi-teal-dim)] text-[var(--bi-teal)] ring-1 ring-[var(--bi-teal-border)] shadow-[0_0_15px_rgba(45,212,191,0.1)]' },
                                        { id: 'groq', name: 'Groq Llama 3.3', desc: 'Velocidad Extrema (70B)', activeClass: 'border-[var(--sim-border)] bg-[var(--sim-accent-soft)] text-[var(--sim-accent)] ring-1 ring-[var(--sim-border)] shadow-[0_0_15px_rgba(244,114,182,0.1)]' }
                                    ].map((p) => {
                                        const isActive = aiProvider === p.id;
                                        return (
                                            <button
                                                key={p.id}
                                                onClick={() => setAiProvider(p.id as 'gemini' | 'mistral' | 'groq')}
                                                className={`p-5 rounded-xl border text-left transition-all duration-300 ${
                                                    isActive 
                                                    ? p.activeClass 
                                                    : 'bg-[var(--bi-surface-1)] border-[var(--bi-border)] text-[var(--bi-text-2)] hover:border-[var(--bi-border-strong)] hover:bg-[var(--bi-surface-2)]'
                                                }`}
                                            >
                                                <p className="text-xs font-bold text-[var(--bi-text-1)] mb-1 uppercase tracking-tight">{p.name}</p>
                                                <p className="text-[10px] text-[var(--bi-text-3)] font-medium leading-normal">{p.desc}</p>
                                            </button>
                                        );
                                    })}
                                </div>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 lg:gap-8">
                                {/* Parameters */}
                                <div className="bg-[var(--bi-surface-0)] border border-[var(--bi-border)] rounded-xl p-6 lg:p-8 backdrop-blur-md shadow-sm space-y-6">
                                    <div className="flex items-center gap-3 border-b border-[var(--bi-border)] pb-4">
                                        <Sliders className="w-5 h-5 text-[var(--bi-purple)]" />
                                        <h2 className="text-sm font-semibold text-[var(--bi-text-1)] uppercase tracking-widest">Parámetros del Modelo</h2>
                                    </div>
                                    
                                    <div className="space-y-4">
                                        <div className="flex justify-between items-center">
                                            <label className="text-xs font-semibold text-[var(--bi-text-2)] uppercase tracking-wider">Temperatura (Creatividad)</label>
                                            <span className="text-xs font-mono text-[var(--bi-purple)] bg-[var(--bi-surface-1)] px-2 py-1 rounded border border-[var(--bi-border)]">{temperature.toFixed(2)}</span>
                                        </div>
                                        <input 
                                            type="range" 
                                            min="0" max="1" step="0.05"
                                            value={temperature}
                                            onChange={(e) => setTemperature(parseFloat(e.target.value))}
                                            className="w-full accent-[var(--bi-purple)] cursor-pointer"
                                        />
                                        <p className="text-[10px] text-[var(--bi-text-3)]">Valores bajos son más analíticos, valores altos son más creativos y exploratorios.</p>
                                    </div>

                                    <div className="space-y-4 pt-4 border-t border-[var(--bi-border)]">
                                        <div className="flex justify-between items-center">
                                            <label className="text-xs font-semibold text-[var(--bi-text-2)] uppercase tracking-wider">Sensibilidad Anomalías (Z-Score)</label>
                                            <span className="text-xs font-mono text-[var(--bi-purple)] bg-[var(--bi-surface-1)] px-2 py-1 rounded border border-[var(--bi-border)]">{anomalySensitivity.toFixed(1)}σ</span>
                                        </div>
                                        <input 
                                            type="range" 
                                            min="1" max="5" step="0.1"
                                            value={anomalySensitivity}
                                            onChange={(e) => setAnomalySensitivity(parseFloat(e.target.value))}
                                            className="w-full accent-[var(--bi-purple)] cursor-pointer"
                                        />
                                        <p className="text-[10px] text-[var(--bi-text-3)]">Desviaciones estándar. Valores bajos detectan más anomalías, valores altos son más estrictos.</p>
                                    </div>
                                </div>

                                {/* Automation */}
                                <div className="bg-[var(--bi-surface-0)] border border-[var(--bi-border)] rounded-xl p-6 lg:p-8 backdrop-blur-md shadow-sm space-y-6">
                                    <div className="flex items-center gap-3 border-b border-[var(--bi-border)] pb-4">
                                        <Sparkles className="w-5 h-5 text-[var(--bi-teal)]" />
                                        <h2 className="text-sm font-semibold text-[var(--bi-text-1)] uppercase tracking-widest">Automatización</h2>
                                    </div>

                                    <div className="flex items-center justify-between p-4 bg-[var(--bi-surface-1)] border border-[var(--bi-border)] rounded-xl">
                                        <div>
                                            <p className="text-xs font-semibold text-[var(--bi-text-1)] uppercase tracking-tight">Sugerencias Auto.</p>
                                            <p className="text-[10px] text-[var(--bi-text-3)] mt-1">Sugerir preguntas analíticas.</p>
                                        </div>
                                        <button 
                                            onClick={() => setAutoSuggestionsEnabled(!autoSuggestionsEnabled)}
                                            className={`w-12 h-6 rounded-full transition-all relative ${autoSuggestionsEnabled ? 'bg-[var(--bi-teal)]' : 'bg-[var(--bi-surface-3)]'}`}
                                        >
                                            <div className={`absolute top-1 w-4 h-4 bg-[var(--bi-canvas)] rounded-full transition-all ${autoSuggestionsEnabled ? 'left-7' : 'left-1'}`}></div>
                                        </button>
                                    </div>

                                    <div className="space-y-3 pt-2">
                                        <label className="text-xs font-semibold text-[var(--bi-text-2)] uppercase tracking-wider">Estrategia "Magic Clean"</label>
                                        <select 
                                            value={magicCleanStrategy}
                                            onChange={(e) => setMagicCleanStrategy(e.target.value)}
                                            className="w-full bg-[var(--bi-surface-1)] border border-[var(--bi-border)] rounded-lg px-4 py-3 text-xs text-[var(--bi-text-1)] focus:outline-none focus:border-[var(--bi-teal-border)] transition-all cursor-pointer"
                                        >
                                            <option value="remove">Eliminar nulos/atípicos</option>
                                            <option value="mean">Imputar con la media (Promedio)</option>
                                            <option value="median">Imputar con la mediana</option>
                                            <option value="zero">Rellenar con ceros</option>
                                        </select>
                                        <p className="text-[10px] text-[var(--bi-text-3)] mt-2">Define cómo el asistente de IA tratará los datos sucios por defecto.</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* --- TAB: SECURITY --- */}
                    {activeTab === "security" && (
                        <div className="space-y-6 lg:space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                            <div className="bg-[var(--bi-surface-0)] border border-[var(--bi-border)] rounded-xl p-6 lg:p-8 backdrop-blur-md shadow-sm space-y-6 lg:space-y-8">
                                <div className="flex items-center gap-3 border-b border-[var(--bi-border)] pb-4 lg:pb-6">
                                    <Shield className="w-5 h-5 text-[var(--bi-green)]" />
                                    <h2 className="text-sm font-semibold text-[var(--bi-text-1)] uppercase tracking-widest">Credenciales y API Keys</h2>
                                </div>

                                <div className="space-y-6 lg:space-y-8">
                                    <div className="space-y-2">
                                        <label className="text-xs font-semibold text-[var(--bi-text-3)] uppercase tracking-widest ml-1 flex justify-between">
                                            <span>Gemini API Key (Recomendado)</span>
                                            {apiKey && apiKey.length > 5 && <span className="text-[var(--bi-green)] flex items-center gap-1"><CheckCircle2 className="w-3 h-3"/> Configurada</span>}
                                        </label>
                                        <div className="relative">
                                            <input
                                                type={showGeminiKey ? "text" : "password"}
                                                value={apiKey}
                                                onChange={(e) => setApiKey(e.target.value)}
                                                className="w-full bg-[var(--bi-surface-1)] border border-[var(--bi-border)] rounded-xl px-4 py-3 pr-12 text-xs text-[var(--bi-text-1)] focus:outline-none focus:border-[var(--bi-green-border)] focus:ring-1 focus:ring-[var(--bi-green-border)] transition-all font-mono"
                                                placeholder="AIzaSy..."
                                            />
                                            <button 
                                                onClick={() => setShowGeminiKey(!showGeminiKey)}
                                                className="absolute right-4 top-1/2 -translate-y-1/2 text-[var(--bi-text-3)] hover:text-[var(--bi-text-1)] transition-colors"
                                            >
                                                {showGeminiKey ? <EyeOff className="w-4 h-4"/> : <Eye className="w-4 h-4"/>}
                                            </button>
                                        </div>
                                    </div>

                                    <div className="space-y-2">
                                        <label className="text-xs font-semibold text-[var(--bi-text-3)] uppercase tracking-widest ml-1 flex justify-between">
                                            <span>Mistral API Key</span>
                                            {mistralKey && mistralKey.length > 5 && <span className="text-[var(--bi-teal)] flex items-center gap-1"><CheckCircle2 className="w-3 h-3"/> Configurada</span>}
                                        </label>
                                        <div className="relative">
                                            <input
                                                type={showMistralKey ? "text" : "password"}
                                                value={mistralKey}
                                                onChange={(e) => setMistralKey(e.target.value)}
                                                className="w-full bg-[var(--bi-surface-1)] border border-[var(--bi-border)] rounded-xl px-4 py-3 pr-12 text-xs text-[var(--bi-text-1)] focus:outline-none focus:border-[var(--bi-teal-border)] focus:ring-1 focus:ring-[var(--bi-teal-border)] transition-all font-mono"
                                                placeholder="your-mistral-key..."
                                            />
                                            <button 
                                                onClick={() => setShowMistralKey(!showMistralKey)}
                                                className="absolute right-4 top-1/2 -translate-y-1/2 text-[var(--bi-text-3)] hover:text-[var(--bi-text-1)] transition-colors"
                                            >
                                                {showMistralKey ? <EyeOff className="w-4 h-4"/> : <Eye className="w-4 h-4"/>}
                                            </button>
                                        </div>
                                    </div>

                                    <div className="space-y-2">
                                        <label className="text-xs font-semibold text-[var(--bi-text-3)] uppercase tracking-widest ml-1 flex justify-between">
                                            <span>Groq API Key</span>
                                            {groqKey && groqKey.length > 5 && <span className="text-[var(--sim-accent)] flex items-center gap-1"><CheckCircle2 className="w-3 h-3"/> Configurada</span>}
                                        </label>
                                        <div className="relative">
                                            <input
                                                type={showGroqKey ? "text" : "password"}
                                                value={groqKey}
                                                onChange={(e) => setGroqKey(e.target.value)}
                                                className="w-full bg-[var(--bi-surface-1)] border border-[var(--bi-border)] rounded-xl px-4 py-3 pr-12 text-xs text-[var(--bi-text-1)] focus:outline-none focus:border-[var(--sim-border)] focus:ring-1 focus:ring-[var(--sim-border)] transition-all font-mono"
                                                placeholder="gsk_..."
                                            />
                                            <button 
                                                onClick={() => setShowGroqKey(!showGroqKey)}
                                                className="absolute right-4 top-1/2 -translate-y-1/2 text-[var(--bi-text-3)] hover:text-[var(--bi-text-1)] transition-colors"
                                            >
                                                {showGroqKey ? <EyeOff className="w-4 h-4"/> : <Eye className="w-4 h-4"/>}
                                            </button>
                                        </div>
                                    </div>
                                </div>
                                <div className="mt-4 p-4 rounded-lg bg-[var(--bi-surface-1)] border border-[var(--bi-border)] text-[11px] text-[var(--bi-text-3)] flex items-start gap-3">
                                    <Shield className="w-4 h-4 text-[var(--bi-green)] shrink-0 mt-0.5"/>
                                    <p>Las llaves se encriptan utilizando AES-256 en el backend y nunca se muestran en texto plano al refrescar la página. Tu seguridad está garantizada por Vektra Engine.</p>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* --- TAB: APPEARANCE --- */}
                    {activeTab === "appearance" && (
                        <div className="space-y-6 lg:space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                            {/* Card 1: Identidad Visual y Marca */}
                            <div className="bg-[var(--bi-surface-0)] border border-[var(--bi-border)] rounded-xl p-6 lg:p-8 backdrop-blur-md shadow-sm space-y-6">
                                <div className="flex items-center gap-3 border-b border-[var(--bi-border)] pb-4">
                                    <Palette className="w-5 h-5 text-[var(--bi-orange)]" />
                                    <h2 className="text-sm font-semibold text-[var(--bi-text-1)] uppercase tracking-widest">Identidad Visual y Marca</h2>
                                </div>
                                
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                    <div className="space-y-4">
                                        <label className="text-xs font-semibold text-[var(--bi-text-2)] uppercase tracking-wider block">Color de Marca (Acento)</label>
                                        <div className="flex items-center gap-4">
                                            <input 
                                                type="color" 
                                                value={brandColor}
                                                onChange={(e) => setBrandColor(e.target.value)}
                                                className="w-12 h-12 rounded-lg cursor-pointer bg-transparent border-0 p-0"
                                            />
                                            <input 
                                                type="text" 
                                                value={brandColor}
                                                onChange={(e) => setBrandColor(e.target.value)}
                                                className="flex-1 bg-[var(--bi-surface-1)] border border-[var(--bi-border)] rounded-lg px-4 py-2.5 text-xs text-[var(--bi-text-1)] focus:outline-none focus:border-[var(--bi-orange)] transition-all font-mono"
                                            />
                                        </div>
                                        <p className="text-[10px] text-[var(--bi-text-3)] font-medium">Este color se usará en portadas, tarjetas destacadas y acentos de los reportes PDF.</p>
                                    </div>

                                    <div className="space-y-4">
                                        <label className="text-xs font-semibold text-[var(--bi-text-2)] uppercase tracking-wider block">Nombre de Organización</label>
                                        <input 
                                            type="text" 
                                            value={reportOrgName}
                                            onChange={(e) => setReportOrgName(e.target.value)}
                                            placeholder="Ej: Vektra Analytics"
                                            className="w-full bg-[var(--bi-surface-1)] border border-[var(--bi-border)] rounded-lg px-4 py-2.5 text-xs text-[var(--bi-text-1)] focus:outline-none focus:border-[var(--bi-orange)] transition-all"
                                        />
                                        <p className="text-[10px] text-[var(--bi-text-3)] font-medium">Se imprimirá en la esquina superior izquierda de cada página del reporte.</p>
                                    </div>
                                </div>
                            </div>

                            {/* Card 2: Ajustes de Reportes y Gráficos */}
                            <div className="bg-[var(--bi-surface-0)] border border-[var(--bi-border)] rounded-xl p-6 lg:p-8 backdrop-blur-md shadow-sm space-y-6">
                                <div className="flex items-center gap-3 border-b border-[var(--bi-border)] pb-4">
                                    <Sliders className="w-5 h-5 text-[var(--bi-blue)]" />
                                    <h2 className="text-sm font-semibold text-[var(--bi-text-1)] uppercase tracking-widest">Configuración de Reportes y Visualizaciones</h2>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                    {/* Subcolumna 1 */}
                                    <div className="space-y-6">
                                        <div className="space-y-2">
                                            <label className="text-xs font-semibold text-[var(--bi-text-2)] uppercase tracking-wider block">Orientación de Reporte PDF</label>
                                            <div className="grid grid-cols-2 gap-2 bg-[var(--bi-surface-1)] p-1 rounded-xl border border-[var(--bi-border)]">
                                                <button
                                                    onClick={() => setPdfOrientation("portrait")}
                                                    className={`flex items-center justify-center gap-2 py-2.5 px-3 text-xs font-semibold rounded-lg transition-all cursor-pointer ${pdfOrientation === "portrait" ? "bg-[var(--bi-surface-3)] text-[var(--bi-text-1)] border border-[var(--bi-border)] shadow-sm" : "text-[var(--bi-text-3)] hover:text-[var(--bi-text-2)]"}`}
                                                >
                                                    <FileText className="w-3.5 h-3.5" /> Vertical (Portrait)
                                                </button>
                                                <button
                                                    onClick={() => setPdfOrientation("landscape")}
                                                    className={`flex items-center justify-center gap-2 py-2.5 px-3 text-xs font-semibold rounded-lg transition-all cursor-pointer ${pdfOrientation === "landscape" ? "bg-[var(--bi-surface-3)] text-[var(--bi-text-1)] border border-[var(--bi-border)] shadow-sm" : "text-[var(--bi-text-3)] hover:text-[var(--bi-text-2)]"}`}
                                                >
                                                    <Columns className="w-3.5 h-3.5 rotate-90" /> Horizontal (Landscape)
                                                </button>
                                            </div>
                                        </div>

                                        <div className="flex items-center justify-between p-4 bg-[var(--bi-surface-1)] border border-[var(--bi-border)] rounded-xl">
                                            <div>
                                                <p className="text-xs font-semibold text-[var(--bi-text-1)] uppercase tracking-tight">Anexar Tabla de Datos</p>
                                                <p className="text-[10px] text-[var(--bi-text-3)] mt-1">Incluir datos tabulares crudos en el reporte.</p>
                                            </div>
                                            <button 
                                                onClick={() => setPdfIncludeDataTable(!pdfIncludeDataTable)}
                                                className={`w-12 h-6 rounded-full transition-all relative cursor-pointer ${pdfIncludeDataTable ? 'bg-[var(--bi-teal)]' : 'bg-[var(--bi-surface-3)]'}`}
                                            >
                                                <div className={`absolute top-1 w-4 h-4 bg-[var(--bi-canvas)] rounded-full transition-all ${pdfIncludeDataTable ? 'left-7' : 'left-1'}`}></div>
                                            </button>
                                        </div>
                                    </div>

                                    {/* Subcolumna 2 */}
                                    <div className="space-y-6">
                                        <div className="space-y-2">
                                            <label className="text-xs font-semibold text-[var(--bi-text-2)] uppercase tracking-wider block">Tema estético de Gráficos</label>
                                            <select 
                                                value={chartTheme}
                                                onChange={(e) => setChartTheme(e.target.value)}
                                                className="w-full bg-[var(--bi-surface-1)] border border-[var(--bi-border)] rounded-lg px-3 py-2.5 text-xs text-[var(--bi-text-1)] focus:outline-none focus:border-[var(--bi-orange)] transition-all cursor-pointer"
                                            >
                                                <option value="neon">🌟 Neón (Vektra Original)</option>
                                                <option value="minimalist">📄 Minimalista (Clásico/Impresión)</option>
                                                <option value="dark_glass">🕶️ Dark Glass (Gris Translúcido)</option>
                                                <option value="vibrant">🎨 Vibrante (Contraste Activo)</option>
                                            </select>
                                        </div>

                                        <div className="space-y-2">
                                            <label className="text-xs font-semibold text-[var(--bi-text-2)] uppercase tracking-wider block">Pie de página del Reporte</label>
                                            <input 
                                                type="text" 
                                                value={reportFooterText}
                                                onChange={(e) => setReportFooterText(e.target.value)}
                                                placeholder="Ej: Confidencial - Solo uso interno"
                                                className="w-full bg-[var(--bi-surface-1)] border border-[var(--bi-border)] rounded-lg px-4 py-2.5 text-xs text-[var(--bi-text-1)] focus:outline-none focus:border-[var(--bi-orange)] transition-all"
                                            />
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Card 3: Formatos Regionales */}
                            <div className="bg-[var(--bi-surface-0)] border border-[var(--bi-border)] rounded-xl p-6 lg:p-8 backdrop-blur-md shadow-sm space-y-6">
                                <div className="flex items-center gap-3 border-b border-[var(--bi-border)] pb-4">
                                    <Activity className="w-5 h-5 text-[var(--bi-teal)]" />
                                    <h2 className="text-sm font-semibold text-[var(--bi-text-1)] uppercase tracking-widest">Formatos Regionales</h2>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                    <div className="space-y-2">
                                        <label className="text-xs font-semibold text-[var(--bi-text-2)] uppercase tracking-wider block">Formato de Moneda</label>
                                        <select 
                                            value={currencyFormat}
                                            onChange={(e) => setCurrencyFormat(e.target.value)}
                                            className="w-full bg-[var(--bi-surface-1)] border border-[var(--bi-border)] rounded-lg px-3 py-2.5 text-xs text-[var(--bi-text-1)] focus:outline-none transition-all cursor-pointer"
                                        >
                                            <option value="USD">Dólares (USD)</option>
                                            <option value="EUR">Euros (EUR)</option>
                                            <option value="MXN">Pesos Mexicanos (MXN)</option>
                                            <option value="COP">Pesos Colombianos (COP)</option>
                                            <option value="ARS">Pesos Argentinos (ARS)</option>
                                        </select>
                                    </div>

                                    <div className="space-y-2">
                                        <label className="text-xs font-semibold text-[var(--bi-text-2)] uppercase tracking-wider block">Formato de Fechas</label>
                                        <select 
                                            value={dateFormat}
                                            onChange={(e) => setDateFormat(e.target.value)}
                                            className="w-full bg-[var(--bi-surface-1)] border border-[var(--bi-border)] rounded-lg px-3 py-2.5 text-xs text-[var(--bi-text-1)] focus:outline-none transition-all cursor-pointer"
                                        >
                                            <option value="DD/MM/YYYY">DD/MM/YYYY</option>
                                            <option value="MM/DD/YYYY">MM/DD/YYYY</option>
                                            <option value="YYYY-MM-DD">YYYY-MM-DD (ISO)</option>
                                        </select>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer Save Area */}
                <div className="flex items-center justify-between pt-6 lg:pt-8 border-t border-[var(--bi-border)] mt-8 pb-4">
                    <div className="flex items-center gap-3">
                        {status === 'success' && <div className="flex items-center gap-2 text-[var(--bi-green)] text-xs font-semibold uppercase tracking-widest animate-in fade-in slide-in-from-left-2"><CheckCircle2 className="w-5 h-5" /> {msg}</div>}
                        {status === 'error' && <div className="flex items-center gap-2 text-[var(--bi-red)] text-xs font-semibold uppercase tracking-widest animate-in fade-in slide-in-from-left-2"><AlertCircle className="w-5 h-5" /> {msg}</div>}
                    </div>
                    <button
                        onClick={handleSave}
                        disabled={status === 'saving'}
                        className="flex items-center gap-2 px-8 py-3.5 bg-[var(--bi-blue)] hover:bg-[#3B82F6] text-white rounded-xl text-xs font-bold uppercase tracking-wider transition-all disabled:opacity-50 cursor-pointer shadow-lg shadow-[var(--bi-blue-border)]/20 hover:shadow-[var(--bi-blue-border)]/40 hover:-translate-y-0.5 active:translate-y-0"
                    >
                        {status === 'saving' ? (
                            <span className="flex items-center gap-2"><Activity className="w-4 h-4 animate-spin"/> Validando...</span>
                        ) : (
                            <><Save className="w-4 h-4" /> Guardar Cambios</>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}
