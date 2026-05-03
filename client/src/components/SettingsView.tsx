'use client';

import { useDashboard } from "@/context/DashboardContext";
import { useSession } from "next-auth/react";
import { useState } from "react";
import { 
    Settings, 
    User, 
    Zap, 
    ShieldCheck, 
    Info, 
    ToggleLeft, 
    ToggleRight, 
    Key,
    Database,
    Sparkles,
    CheckCircle2,
    AlertCircle,
    Cpu,
    Moon,
    Sun,
    Globe
} from "lucide-react";
import { validateApiKey } from "@/lib/api";

export function SettingsView() {
    const { data: session } = useSession();
    const { 
        showAiSuggestions, 
        setShowAiSuggestions,
        aiProvider,
        setAiProvider,
        apiKey,
        setApiKey,
        mistralKey,
        setMistralKey
    } = useDashboard();

    const [geminiStatus, setGeminiStatus] = useState<"idle" | "success" | "error">("idle");
    const [mistralStatus, setMistralStatus] = useState<"idle" | "success" | "error">("idle");

    const handleGeminiChange = async (val: string) => {
        setApiKey(val);
        if (val.length > 20) {
            try {
                const res = await validateApiKey(val, "gemini");
                setGeminiStatus(res.valid ? "success" : "error");
            } catch {
                setGeminiStatus("error");
            }
        } else {
            setGeminiStatus("idle");
        }
    };

    const handleMistralChange = async (val: string) => {
        setMistralKey(val);
        if (val.length > 20) {
            try {
                const res = await validateApiKey(val, "mistral");
                setMistralStatus(res.valid ? "success" : "error");
            } catch {
                setMistralStatus("error");
            }
        } else {
            setMistralStatus("idle");
        }
    };

    return (
        <div className="flex-1 bg-[var(--bg-primary)] overflow-y-auto custom-scrollbar p-6 lg:p-12 animate-in fade-in duration-500">
            <div className="max-w-5xl mx-auto space-y-10">
                
                {/* Header Estratégico */}
                <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 border-b border-[var(--border-color)] pb-8">
                    <div className="space-y-2">
                        <div className="flex items-center gap-3">
                            <div className="p-2.5 bg-blue-600 rounded-xl shadow-lg shadow-blue-600/20">
                                <Settings className="w-5 h-5 text-white" />
                            </div>
                            <h1 className="text-2xl font-black text-[var(--text-primary)] tracking-tight uppercase">Centro de Control</h1>
                        </div>
                        <p className="text-sm text-[var(--text-tertiary)] font-medium">Configura los motores de inferencia y la identidad de tu consultoría.</p>
                    </div>
                    
                    <div className="flex items-center gap-4 bg-[var(--bg-secondary)] p-1.5 rounded-2xl border border-[var(--border-color)]">
                        <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-500/10 rounded-xl border border-emerald-500/20">
                            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                            <span className="text-[10px] font-black text-emerald-500 uppercase tracking-widest">Sistema Online</span>
                        </div>
                        <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-500/10 rounded-xl border border-blue-500/20">
                            <Globe className="w-3.5 h-3.5 text-blue-400" />
                            <span className="text-[10px] font-black text-blue-400 uppercase tracking-widest">v2.5 Stable</span>
                        </div>
                    </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    
                    {/* Columna Izquierda: Perfil y Preferencias Generales */}
                    <div className="lg:col-span-1 space-y-8">
                        {/* Perfil Mini */}
                        <section className="bg-gradient-to-br from-blue-600 to-blue-800 rounded-[2rem] p-6 text-white shadow-2xl relative overflow-hidden group">
                            <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:scale-110 transition-transform duration-700">
                                <User className="w-24 h-24" />
                            </div>
                            <div className="relative z-10 space-y-4">
                                <img 
                                    src={session?.user?.image || ""} 
                                    alt="Profile" 
                                    className="w-16 h-16 rounded-2xl border-2 border-white/30 shadow-lg"
                                />
                                <div>
                                    <h2 className="text-lg font-black leading-tight truncate">{session?.user?.name}</h2>
                                    <p className="text-[10px] text-white/60 font-bold uppercase tracking-widest">Consultor Estratégico</p>
                                </div>
                                <div className="pt-2 flex flex-wrap gap-2">
                                    <span className="bg-white/10 text-[9px] font-black uppercase tracking-widest px-2 py-1 rounded-lg border border-white/10 backdrop-blur-md">Vektra Pro</span>
                                    <span className="bg-white/10 text-[9px] font-black uppercase tracking-widest px-2 py-1 rounded-lg border border-white/10 backdrop-blur-md">Admin</span>
                                </div>
                            </div>
                        </section>

                        {/* Temas y UX */}
                        <section className="bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-[2rem] p-6 space-y-6">
                            <h3 className="text-[10px] font-black text-[var(--text-tertiary)] uppercase tracking-[0.2em] flex items-center gap-2">
                                <Sun className="w-3 h-3" /> Interfaz & UX
                            </h3>
                            
                            <div className="space-y-4">
                                <div className="flex items-center justify-between p-3 bg-[var(--bg-primary)] rounded-xl border border-[var(--border-color)] group hover:border-blue-500/30 transition-all cursor-pointer" onClick={() => setShowAiSuggestions(!showAiSuggestions)}>
                                    <div className="flex items-center gap-3">
                                        <div className="p-2 bg-blue-500/10 rounded-lg">
                                            <Sparkles className="w-4 h-4 text-blue-400" />
                                        </div>
                                        <div>
                                            <p className="text-xs font-bold text-[var(--text-primary)]">Sugerencias IA</p>
                                            <p className="text-[9px] text-[var(--text-tertiary)]">Análisis predictivo</p>
                                        </div>
                                    </div>
                                    {showAiSuggestions ? <ToggleRight className="text-blue-500" /> : <ToggleLeft className="text-[var(--text-tertiary)]" />}
                                </div>

                                <div className="flex items-center justify-between p-3 bg-[var(--bg-primary)] rounded-xl border border-[var(--border-color)] opacity-50 cursor-not-allowed">
                                    <div className="flex items-center gap-3">
                                        <div className="p-2 bg-gray-500/10 rounded-lg">
                                            <Moon className="w-4 h-4 text-gray-400" />
                                        </div>
                                        <div>
                                            <p className="text-xs font-bold text-[var(--text-primary)]">Tema Automático</p>
                                            <p className="text-[9px] text-[var(--text-tertiary)]">Sincronizado con sistema</p>
                                        </div>
                                    </div>
                                    <ToggleRight className="text-gray-400" />
                                </div>
                            </div>
                        </section>
                    </div>

                    {/* Columna Derecha: Configuración de Motores de IA */}
                    <div className="lg:col-span-2 space-y-8">
                        <section className="bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-[2rem] p-8 space-y-8">
                            <div className="flex items-center justify-between">
                                <h3 className="text-[10px] font-black text-[var(--text-tertiary)] uppercase tracking-[0.2em] flex items-center gap-2">
                                    <Cpu className="w-3.5 h-3.5" /> Motores de Inferencia (Swarm Engine)
                                </h3>
                                <div className="flex items-center gap-1.5 px-2 py-1 bg-blue-600/10 rounded-lg border border-blue-500/20">
                                    <Zap className="w-3 h-3 text-blue-400" />
                                    <span className="text-[9px] font-black text-blue-400 uppercase tracking-widest">Optimizado</span>
                                </div>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                {[
                                    { id: 'gemini', label: 'Gemini 1.5 Flash', desc: 'Ingeniería & Datos', color: 'blue' },
                                    { id: 'mistral', label: 'Mistral Large', desc: 'Estrategia & Razonamiento', color: 'purple' },
                                    { id: 'hybrid', label: 'Dual (Enjambre)', desc: 'Máxima Precisión', color: 'indigo' },
                                ].map((item) => (
                                    <button
                                        key={item.id}
                                        onClick={() => setAiProvider(item.id as any)}
                                        className={`p-4 rounded-2xl border text-left transition-all ${
                                            aiProvider === item.id 
                                            ? `bg-${item.color}-600/10 border-${item.color}-500/50 ring-4 ring-${item.color}-500/5` 
                                            : 'bg-[var(--bg-primary)] border-[var(--border-color)] hover:border-gray-500/30'
                                        }`}
                                    >
                                        <p className={`text-[10px] font-black uppercase tracking-widest mb-1 ${aiProvider === item.id ? `text-${item.color}-400` : 'text-[var(--text-tertiary)]'}`}>
                                            {item.label}
                                        </p>
                                        <p className="text-[9px] text-[var(--text-tertiary)] font-medium leading-tight">{item.desc}</p>
                                    </button>
                                ))}
                            </div>

                            <div className="space-y-6 pt-4">
                                {/* Gemini Key */}
                                <div className="space-y-3">
                                    <label className="text-[10px] font-black text-[var(--text-primary)] uppercase tracking-widest flex items-center gap-2">
                                        <Key className="w-3 h-3 text-blue-500" /> Google API Key
                                    </label>
                                    <div className="relative">
                                        <input
                                            type="password"
                                            value={apiKey}
                                            onChange={(e) => handleGeminiChange(e.target.value)}
                                            placeholder="Ingresa tu clave de Gemini..."
                                            className="w-full bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-2xl px-5 py-4 text-sm text-[var(--text-primary)] placeholder-[var(--text-tertiary)] focus:outline-none focus:ring-4 focus:ring-blue-600/5 focus:border-blue-500/50 transition-all"
                                        />
                                        <div className="absolute right-4 top-1/2 -translate-y-1/2">
                                            {geminiStatus === "success" && <CheckCircle2 className="w-5 h-5 text-emerald-500" />}
                                            {geminiStatus === "error" && <AlertCircle className="w-5 h-5 text-red-500" />}
                                        </div>
                                    </div>
                                </div>

                                {/* Mistral Key */}
                                <div className="space-y-3">
                                    <label className="text-[10px] font-black text-[var(--text-primary)] uppercase tracking-widest flex items-center gap-2">
                                        <Key className="w-3 h-3 text-purple-500" /> Mistral API Key
                                    </label>
                                    <div className="relative">
                                        <input
                                            type="password"
                                            value={mistralKey}
                                            onChange={(e) => handleMistralChange(e.target.value)}
                                            placeholder="Ingresa tu clave de Mistral..."
                                            className="w-full bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-2xl px-5 py-4 text-sm text-[var(--text-primary)] placeholder-[var(--text-tertiary)] focus:outline-none focus:ring-4 focus:ring-purple-600/5 focus:border-purple-500/50 transition-all"
                                        />
                                        <div className="absolute right-4 top-1/2 -translate-y-1/2">
                                            {mistralStatus === "success" && <CheckCircle2 className="w-5 h-5 text-emerald-500" />}
                                            {mistralStatus === "error" && <AlertCircle className="w-5 h-5 text-red-500" />}
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div className="p-4 bg-orange-500/5 rounded-2xl border border-orange-500/10 flex items-start gap-4">
                                <Info className="w-4 h-4 text-orange-400 mt-0.5" />
                                <div className="space-y-1">
                                    <p className="text-[11px] font-bold text-orange-300">Nota sobre Privacidad</p>
                                    <p className="text-[9px] text-orange-400/80 leading-relaxed">
                                        Tus llaves API se almacenan localmente en tu sesión y se envían de forma segura para cada consulta. 
                                        Nunca se guardan de forma permanente en nuestros servidores de base de datos.
                                    </p>
                                </div>
                            </div>
                        </section>
                    </div>
                </div>

                {/* Footer de Seguridad */}
                <div className="pt-10 border-t border-[var(--border-color)] flex flex-col md:flex-row items-center justify-between gap-6 opacity-30 group-hover:opacity-60 transition-opacity">
                    <div className="flex items-center gap-8">
                        <div className="flex items-center gap-2">
                            <ShieldCheck className="w-4 h-4" />
                            <span className="text-[9px] font-black uppercase tracking-[0.2em]">Cifrado AES-256</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <Database className="w-4 h-4" />
                            <span className="text-[9px] font-black uppercase tracking-[0.2em]">Almacenamiento Seguro</span>
                        </div>
                    </div>
                    <p className="text-[9px] font-bold text-[var(--text-tertiary)] uppercase tracking-widest">Vektra BI Estratégico • 2026</p>
                </div>

            </div>
        </div>
    );
}
