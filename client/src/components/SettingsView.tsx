'use client';

import { useState } from "react";
import { Settings, Key, Cpu, Shield, Save, CheckCircle2, AlertCircle, Sparkles } from "lucide-react";
import { useDashboard } from "@/context/DashboardContext";
import { validateApiKey } from "@/lib/api";

export function SettingsView() {
    const { apiKey, setApiKey, mistralKey, setMistralKey, aiProvider, setAiProvider, autoSuggestionsEnabled, setAutoSuggestionsEnabled } = useDashboard();
    const [status, setStatus] = useState<"idle" | "saving" | "success" | "error">("idle");
    const [msg, setMsg] = useState("");

    const handleSave = async () => {
        setStatus("saving");
        try {
            // Validar Gemini
            if (apiKey && apiKey.length > 10) {
                const res = await validateApiKey(apiKey, "gemini");
                if (!res.valid) {
                    throw new Error(res.error || "API Key de Gemini rechazada por el servidor.");
                }
            }
            
            // Validar Mistral (opcional)
            if (mistralKey && mistralKey.length > 10) {
                const res = await validateApiKey(mistralKey, "mistral");
                if (!res.valid) {
                    throw new Error(res.error || "API Key de Mistral rechazada por el servidor.");
                }
            }

            setStatus("success");
            setMsg("Configuración guardada correctamente");
            setTimeout(() => setStatus("idle"), 3000);
        } catch (err: any) {
            setStatus("error");
            setMsg(err.message || "Error al validar llaves");
        }
    };


    return (
        <div className="flex-1 bg-[var(--bg-primary)] p-12 overflow-y-auto custom-scrollbar">
            <div className="max-w-3xl mx-auto space-y-12">
                <header className="space-y-4">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-blue-600 rounded-2xl shadow-xl shadow-blue-600/20">
                            <Settings className="w-6 h-6 text-white" />
                        </div>
                        <div>
                            <h1 className="text-3xl font-black text-white tracking-tight">Configuración del Sistema</h1>
                            <p className="text-[10px] text-blue-400 font-black uppercase tracking-widest">Motor de IA • Seguridad • Conexiones</p>
                        </div>
                    </div>
                </header>

                <div className="grid grid-cols-1 gap-8">
                    {/* Tarjeta de Proveedor */}
                    <div className="bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-3xl p-8 space-y-8">
                        <div className="flex items-center gap-3 border-b border-[var(--border-color)] pb-6">
                            <Cpu className="w-5 h-5 text-blue-500" />
                            <h2 className="text-[10px] font-black text-white uppercase tracking-widest">Cerebro Analítico Principal</h2>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            {[
                                { id: 'gemini', name: 'Google Gemini', desc: 'Rendimiento Extremo (Flash 3)', color: 'blue' },
                                { id: 'mistral', name: 'Mistral AI', desc: 'Precisión Estratégica (Large)', color: 'orange' },
                                { id: 'hybrid', name: 'Motor Híbrido', desc: 'Orquestación Inteligente', color: 'purple' }
                            ].map((p) => (
                                <button
                                    key={p.id}
                                    onClick={() => setAiProvider(p.id as any)}
                                    className={`p-6 rounded-2xl border text-left transition-all ${aiProvider === p.id 
                                        ? `bg-${p.color}-600/10 border-${p.color}-500/50 ring-2 ring-${p.color}-500/20` 
                                        : 'bg-white/[0.02] border-white/5 hover:border-white/10'}`}
                                >
                                    <p className="text-xs font-black text-white mb-1 uppercase tracking-tighter">{p.name}</p>
                                    <p className="text-[9px] text-gray-500 font-medium">{p.desc}</p>
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Tarjeta de Preferencias */}
                    <div className="bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-3xl p-8 space-y-8">
                        <div className="flex items-center gap-3 border-b border-[var(--border-color)] pb-6">
                            <Sparkles className="w-5 h-5 text-purple-500" />
                            <h2 className="text-[10px] font-black text-white uppercase tracking-widest">Experiencia y Automatización</h2>
                        </div>

                        <div className="flex items-center justify-between p-6 bg-white/[0.02] border border-white/5 rounded-2xl">
                            <div>
                                <p className="text-xs font-black text-white uppercase tracking-tighter">Sugerencias Automáticas</p>
                                <p className="text-[9px] text-gray-500 font-medium">Generar preguntas de análisis inmediatamente al subir archivos.</p>
                            </div>
                            <button 
                                onClick={() => setAutoSuggestionsEnabled(!autoSuggestionsEnabled)}
                                className={`w-12 h-6 rounded-full transition-all relative ${autoSuggestionsEnabled ? 'bg-blue-600' : 'bg-gray-800'}`}
                            >
                                <div className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-all ${autoSuggestionsEnabled ? 'left-7' : 'left-1'}`}></div>
                            </button>
                        </div>
                    </div>

                    {/* Tarjeta de Seguridad (API Keys) */}
                    <div className="bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-3xl p-8 space-y-8">
                        <div className="flex items-center gap-3 border-b border-[var(--border-color)] pb-6">
                            <Key className="w-5 h-5 text-emerald-500" />
                            <h2 className="text-[10px] font-black text-white uppercase tracking-widest">Llaves de Acceso (Encriptadas)</h2>
                        </div>

                        <div className="space-y-6">
                            <div className="space-y-3">
                                <label className="text-[9px] font-black text-gray-500 uppercase tracking-widest ml-1">Gemini API Key</label>
                                <div className="relative">
                                    <input
                                        type="password"
                                        value={apiKey}
                                        onChange={(e) => setApiKey(e.target.value)}
                                        className="w-full bg-black border border-white/5 rounded-2xl px-6 py-4 text-xs text-white focus:outline-none focus:border-blue-500/50 transition-all font-mono"
                                        placeholder="AIzaSy..."
                                    />
                                    <div className="absolute right-4 top-1/2 -translate-y-1/2">
                                        <Shield className="w-4 h-4 text-gray-700" />
                                    </div>
                                </div>
                            </div>

                            <div className="space-y-3">
                                <label className="text-[9px] font-black text-gray-500 uppercase tracking-widest ml-1">Mistral API Key (Opcional)</label>
                                <input
                                    type="password"
                                    value={mistralKey}
                                    onChange={(e) => setMistralKey(e.target.value)}
                                    className="w-full bg-black border border-white/5 rounded-2xl px-6 py-4 text-xs text-white focus:outline-none focus:border-orange-500/50 transition-all font-mono"
                                    placeholder="your-mistral-key..."
                                />
                            </div>
                        </div>
                    </div>
                </div>

                <div className="flex items-center justify-between pt-8 border-t border-[var(--border-color)]">
                    <div className="flex items-center gap-3">
                        {status === 'success' && <div className="flex items-center gap-2 text-emerald-500 text-[10px] font-black uppercase tracking-widest animate-in fade-in slide-in-from-left-2"><CheckCircle2 className="w-4 h-4" /> {msg}</div>}
                        {status === 'error' && <div className="flex items-center gap-2 text-red-500 text-[10px] font-black uppercase tracking-widest animate-in fade-in slide-in-from-left-2"><AlertCircle className="w-4 h-4" /> {msg}</div>}
                    </div>
                    <button
                        onClick={handleSave}
                        disabled={status === 'saving'}
                        className="flex items-center gap-2 px-8 py-4 bg-white text-black hover:bg-gray-200 rounded-2xl text-[10px] font-black uppercase tracking-[0.2em] transition-all shadow-2xl shadow-white/10 disabled:opacity-50"
                    >
                        {status === 'saving' ? 'Validando...' : <><Save className="w-4 h-4" /> Guardar Cambios</>}
                    </button>
                </div>
            </div>
        </div>
    );
}
