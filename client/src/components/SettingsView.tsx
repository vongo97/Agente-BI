'use client';

import { useState } from "react";
import { Settings, Key, Cpu, Shield, Save, CheckCircle2, AlertCircle, Sparkles, Menu } from "lucide-react";
import { useDashboard } from "@/context/DashboardContext";
import { validateApiKey } from "@/lib/api";

export function SettingsView() {
    const { apiKey, setApiKey, mistralKey, setMistralKey, aiProvider, setAiProvider, autoSuggestionsEnabled, setAutoSuggestionsEnabled, setSidebarOpen } = useDashboard();
    const [status, setStatus] = useState<"idle" | "saving" | "success" | "error">("idle");
    const [msg, setMsg] = useState("");

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
        <div className="flex-1 bg-[var(--bi-canvas)] p-8 lg:p-12 overflow-y-auto custom-scrollbar">
            <div className="max-w-3xl mx-auto space-y-8 lg:space-y-12">
                <header className="space-y-4">
                    <div className="flex items-center gap-3 lg:gap-4">
                        <button
                            onClick={() => setSidebarOpen(true)}
                            className="lg:hidden p-2 rounded-md text-[var(--bi-text-3)] hover:text-[var(--bi-text-1)] hover:bg-[var(--bi-surface-1)] active:bg-[var(--bi-surface-2)] transition-all duration-200 cursor-pointer"
                            aria-label="Abrir menú"
                        >
                            <Menu className="w-5 h-5" />
                        </button>
                        <div className="p-3 bg-[var(--bi-blue-dim)] border border-[var(--bi-blue-border)] rounded-lg hidden sm:block">
                            <Settings className="w-5 h-5 text-[var(--bi-blue)]" />
                        </div>
                        <div>
                            <h1 className="text-xl font-bold text-[var(--bi-text-1)] tracking-tight">Configuración del Sistema</h1>
                            <p className="text-[10px] text-[var(--bi-blue)] font-semibold uppercase tracking-widest">Motor de IA • Seguridad • Conexiones</p>
                        </div>
                    </div>
                </header>

                <div className="grid grid-cols-1 gap-6 lg:gap-8">
                    {/* Tarjeta de Proveedor */}
                    <div className="bg-[var(--bi-surface-0)] border border-[var(--bi-border)] rounded-lg p-6 lg:p-8 space-y-6 lg:space-y-8">
                        <div className="flex items-center gap-3 border-b border-[var(--bi-border)] pb-4 lg:pb-6">
                            <Cpu className="w-4 h-4 text-[var(--bi-blue)]" />
                            <h2 className="text-[10px] font-semibold text-[var(--bi-text-1)] uppercase tracking-widest">Cerebro Analítico Principal</h2>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            {[
                                { id: 'gemini', name: 'Google Gemini', desc: 'Rendimiento Extremo (Flash 3)', activeClass: 'border-[var(--bi-blue-border)] bg-[var(--bi-blue-dim)] text-[var(--bi-blue)] ring-1 ring-[var(--bi-blue-border)]' },
                                { id: 'mistral', name: 'Mistral AI', desc: 'Precisión Estratégica (Large)', activeClass: 'border-[var(--bi-teal-border)] bg-[var(--bi-teal-dim)] text-[var(--bi-teal)] ring-1 ring-[var(--bi-teal-border)]' },
                                { id: 'hybrid', name: 'Motor Híbrido', desc: 'Orquestación Inteligente', activeClass: 'border-[var(--bi-amber-dim)] bg-[var(--bi-amber-dim)] text-[var(--bi-amber)] ring-1 ring-[var(--bi-amber-dim)]' }
                            ].map((p) => {
                                const isActive = aiProvider === p.id;
                                return (
                                    <button
                                        key={p.id}
                                        onClick={() => setAiProvider(p.id as 'gemini' | 'mistral' | 'hybrid')}
                                        className={`p-5 rounded-lg border text-left transition-all ${
                                            isActive 
                                            ? p.activeClass 
                                            : 'bg-[var(--bi-surface-1)] border-[var(--bi-border)] text-[var(--bi-text-2)] hover:border-[var(--bi-border-strong)]'
                                        }`}
                                    >
                                        <p className="text-xs font-semibold text-[var(--bi-text-1)] mb-1 uppercase tracking-tight">{p.name}</p>
                                        <p className="text-[9px] text-[var(--bi-text-2)] font-medium leading-normal">{p.desc}</p>
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    {/* Tarjeta de Preferencias */}
                    <div className="bg-[var(--bi-surface-0)] border border-[var(--bi-border)] rounded-lg p-6 lg:p-8 space-y-6 lg:space-y-8">
                        <div className="flex items-center gap-3 border-b border-[var(--bi-border)] pb-4 lg:pb-6">
                            <Sparkles className="w-4 h-4 text-[var(--bi-teal)]" />
                            <h2 className="text-[10px] font-semibold text-[var(--bi-text-1)] uppercase tracking-widest">Experiencia y Automatización</h2>
                        </div>

                        <div className="flex items-center justify-between p-4 lg:p-6 bg-[var(--bi-surface-1)] border border-[var(--bi-border)] rounded-lg">
                            <div>
                                <p className="text-xs font-semibold text-[var(--bi-text-1)] uppercase tracking-tight">Sugerencias Automáticas</p>
                                <p className="text-[9px] text-[var(--bi-text-2)] font-medium">Generar preguntas de análisis inmediatamente al subir archivos.</p>
                            </div>
                            <button 
                                onClick={() => setAutoSuggestionsEnabled(!autoSuggestionsEnabled)}
                                className={`w-10 h-5 rounded-full transition-all relative ${autoSuggestionsEnabled ? 'bg-[var(--bi-blue)]' : 'bg-[var(--bi-surface-3)]'}`}
                            >
                                <div className={`absolute top-0.5 w-4 h-4 bg-[var(--bi-canvas)] rounded-full transition-all ${autoSuggestionsEnabled ? 'left-5.5' : 'left-0.5'}`}></div>
                            </button>
                        </div>
                    </div>

                    {/* Tarjeta de Seguridad (API Keys) */}
                    <div className="bg-[var(--bi-surface-0)] border border-[var(--bi-border)] rounded-lg p-6 lg:p-8 space-y-6 lg:space-y-8">
                        <div className="flex items-center gap-3 border-b border-[var(--bi-border)] pb-4 lg:pb-6">
                            <Key className="w-4 h-4 text-[var(--bi-green)]" />
                            <h2 className="text-[10px] font-semibold text-[var(--bi-text-1)] uppercase tracking-widest">Llaves de Acceso (Encriptadas)</h2>
                        </div>

                        <div className="space-y-4 lg:space-y-6">
                            <div className="space-y-2">
                                <label className="text-[9px] font-semibold text-[var(--bi-text-3)] uppercase tracking-widest ml-1">Gemini API Key</label>
                                <div className="relative">
                                    <input
                                        type="password"
                                        value={apiKey}
                                        onChange={(e) => setApiKey(e.target.value)}
                                        className="w-full bg-[var(--bi-canvas)] border border-[var(--bi-border)] rounded-lg px-4 py-3 text-xs text-[var(--bi-text-1)] focus:outline-none focus:border-[var(--bi-blue-border)] transition-all font-mono"
                                        placeholder="AIzaSy..."
                                    />
                                    <div className="absolute right-4 top-1/2 -translate-y-1/2">
                                        <Shield className="w-4 h-4 text-[var(--bi-text-3)]" />
                                    </div>
                                </div>
                            </div>

                            <div className="space-y-2">
                                <label className="text-[9px] font-semibold text-[var(--bi-text-3)] uppercase tracking-widest ml-1">Mistral API Key (Opcional)</label>
                                <input
                                    type="password"
                                    value={mistralKey}
                                    onChange={(e) => setMistralKey(e.target.value)}
                                    className="w-full bg-[var(--bi-canvas)] border border-[var(--bi-border)] rounded-lg px-4 py-3 text-xs text-[var(--bi-text-1)] focus:outline-none focus:border-[var(--bi-teal-border)] transition-all font-mono"
                                    placeholder="your-mistral-key..."
                                />
                            </div>
                        </div>
                    </div>
                </div>

                <div className="flex items-center justify-between pt-6 lg:pt-8 border-t border-[var(--bi-border)]">
                    <div className="flex items-center gap-3">
                        {status === 'success' && <div className="flex items-center gap-2 text-[var(--bi-green)] text-[10px] font-semibold uppercase tracking-widest animate-in fade-in slide-in-from-left-2"><CheckCircle2 className="w-4 h-4" /> {msg}</div>}
                        {status === 'error' && <div className="flex items-center gap-2 text-[var(--bi-red)] text-[10px] font-semibold uppercase tracking-widest animate-in fade-in slide-in-from-left-2"><AlertCircle className="w-4 h-4" /> {msg}</div>}
                    </div>
                    <button
                        onClick={handleSave}
                        disabled={status === 'saving'}
                        className="flex items-center gap-2 px-6 py-3 bg-[var(--bi-teal)] hover:bg-[var(--bi-teal-hover)] text-black rounded-lg text-xs font-semibold uppercase tracking-wider transition-all disabled:opacity-50 cursor-pointer"
                    >
                        {status === 'saving' ? 'Validando...' : <><Save className="w-4 h-4" /> Guardar Cambios</>}
                    </button>
                </div>
            </div>
        </div>
    );
}
