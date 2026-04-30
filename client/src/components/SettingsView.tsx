'use client';

import { useDashboard } from "@/context/DashboardContext";
import { useSession } from "next-auth/react";
import { 
    Settings, 
    User, 
    Zap, 
    CreditCard, 
    ShieldCheck, 
    Info, 
    ToggleLeft, 
    ToggleRight, 
    ArrowRight,
    Key,
    Database,
    Sparkles
} from "lucide-react";

export function SettingsView() {
    const { data: session } = useSession();
    const { 
        showAiSuggestions, 
        setShowAiSuggestions,
        aiProvider,
        setAiProvider,
        apiKey,
        mistralKey
    } = useDashboard();

    return (
        <div className="flex-1 bg-[var(--bg-primary)] overflow-y-auto custom-scrollbar p-8 lg:p-12">
            <div className="max-w-4xl mx-auto space-y-12">
                
                {/* Header */}
                <div className="space-y-2">
                    <div className="flex items-center gap-3">
                        <div className="p-3 bg-blue-600/10 rounded-2xl">
                            <Settings className="w-6 h-6 text-blue-500" />
                        </div>
                        <h1 className="text-3xl font-black text-[var(--text-primary)] tracking-tight uppercase">Configuracion</h1>
                    </div>
                    <p className="text-[var(--text-tertiary)] font-medium">Gestiona los detalles de tu cuenta, preferencias de IA y consumo de creditos.</p>
                </div>

                {/* Perfil de Usuario */}
                <section className="bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-3xl p-8 shadow-2xl relative overflow-hidden group">
                    <div className="absolute top-0 right-0 p-8 opacity-5 group-hover:opacity-10 transition-opacity">
                        <User className="w-32 h-32" />
                    </div>
                    
                    <div className="flex items-center gap-6">
                        <img 
                            src={session?.user?.image || ""} 
                            alt="Profile" 
                            className="w-20 h-20 rounded-3xl border-4 border-blue-600/20 shadow-xl"
                        />
                        <div className="space-y-1">
                            <h2 className="text-xl font-black text-[var(--text-primary)]">{session?.user?.name}</h2>
                            <p className="text-sm text-[var(--text-tertiary)] font-medium leading-none">{session?.user?.email}</p>
                            <div className="flex items-center gap-2 mt-4">
                                <span className="bg-emerald-500/10 text-emerald-500 text-[9px] font-black uppercase tracking-widest px-2 py-1 rounded-lg border border-emerald-500/20">Cuenta Pro</span>
                                <span className="bg-blue-600/10 text-blue-400 text-[9px] font-black uppercase tracking-widest px-2 py-1 rounded-lg border border-blue-600/20">Socio Consultor</span>
                            </div>
                        </div>
                    </div>
                </section>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    
                    {/* Preferencias de IA */}
                    <section className="space-y-6">
                        <div className="flex items-center gap-2 px-1">
                            <Zap className="w-4 h-4 text-purple-500" />
                            <h3 className="text-[10px] font-black text-[var(--text-tertiary)] uppercase tracking-[0.2em]">Preferencias de IA</h3>
                        </div>

                        <div className="bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-3xl p-6 space-y-6">
                            
                            {/* Toggle Sugerencias */}
                            <div className="flex items-center justify-between group cursor-pointer" onClick={() => setShowAiSuggestions(!showAiSuggestions)}>
                                <div className="space-y-1">
                                    <p className="text-sm font-bold text-[var(--text-primary)]">Sugerencias Automáticas</p>
                                    <p className="text-[10px] text-[var(--text-tertiary)] leading-relaxed">
                                        Analiza tus datos para sugerir preguntas estratégicas. 
                                        <span className="text-orange-500 block font-bold mt-1">Consumo: ~1 crédito por sugerencia.</span>
                                    </p>
                                </div>
                                <button className="transition-all active:scale-90">
                                    {showAiSuggestions ? (
                                        <ToggleRight className="w-8 h-8 text-blue-500" />
                                    ) : (
                                        <ToggleLeft className="w-8 h-8 text-[var(--text-tertiary)]" />
                                    )}
                                </button>
                            </div>

                            <hr className="border-[var(--border-color)]" />

                            {/* Info de Créditos */}
                            <div className="flex items-start gap-4 bg-purple-600/5 p-4 rounded-2xl border border-purple-500/10 transition-all hover:bg-purple-600/10">
                                <div className="p-2 bg-purple-600/20 rounded-xl">
                                    <Sparkles className="w-4 h-4 text-purple-400" />
                                </div>
                                <div className="space-y-1">
                                    <p className="text-xs font-bold text-purple-300">Tips de Optimización</p>
                                    <p className="text-[10px] text-purple-400/80 leading-relaxed italic">
                                        Desactivar las sugerencias puede ahorrar hasta un 40% de tus créditos mensuales si realizas muchos análisis.
                                    </p>
                                </div>
                            </div>
                        </div>
                    </section>

                    {/* Pasos para Editar Cuenta */}
                    <section className="space-y-6">
                        <div className="flex items-center gap-2 px-1">
                            <Info className="w-4 h-4 text-blue-500" />
                            <h3 className="text-[10px] font-black text-[var(--text-tertiary)] uppercase tracking-[0.2em]">Guía de Cuenta</h3>
                        </div>

                        <div className="bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-3xl p-6 space-y-4">
                            {[
                                { step: 1, text: "Accede a la sección de Perfil para cambiar tu nombre de consultor.", icon: User },
                                { step: 2, text: "Configura tus llaves API (Gemini/Mistral) para usar tus propios créditos externos.", icon: Key },
                                { step: 3, text: "Gestiona tus fuentes de datos guardadas en la pestaña 'Datos'.", icon: Database },
                                { step: 4, text: "Si necesitas más créditos, contacta con soporte técnico.", icon: CreditCard },
                            ].map((item, idx) => (
                                <div key={idx} className="flex items-start gap-4 group">
                                    <div className="w-6 h-6 rounded-lg bg-[var(--bg-tertiary)] border border-[var(--border-color)] flex items-center justify-center shrink-0 group-hover:border-blue-500/50 group-hover:bg-blue-600/10 transition-all">
                                        <span className="text-[9px] font-black text-[var(--text-tertiary)] group-hover:text-blue-400">{item.step}</span>
                                    </div>
                                    <p className="text-[11px] text-[var(--text-secondary)] group-hover:text-[var(--text-primary)] transition-colors leading-relaxed pt-0.5">{item.text}</p>
                                </div>
                            ))}
                        </div>
                    </section>

                </div>

                {/* Footer / Info de Seguridad */}
                <div className="flex items-center justify-center gap-6 py-8 border-t border-[var(--border-color)] opacity-40">
                    <div className="flex items-center gap-2">
                        <ShieldCheck className="w-4 h-4" />
                        <span className="text-[10px] font-bold uppercase tracking-widest">Datos Encriptados</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <CreditCard className="w-4 h-4" />
                        <span className="text-[10px] font-bold uppercase tracking-widest">Facturación Segura</span>
                    </div>
                </div>

            </div>
        </div>
    );
}
