'use client';

import { useSession, signOut } from "next-auth/react";
import { Upload, Settings, Database, LogOut, ChevronDown, Activity, CheckCircle2, AlertCircle, FileText, X, Menu, Brain, Sparkles, Zap } from "lucide-react";
import { useState, useEffect } from "react";
import { validateApiKey, uploadFile, connectSql, connectGoogleSheets, getHistory, getChatDetails, getDataSources, saveDataSource, deleteDataSource, removeSessionSource, clearSession } from "@/lib/api";
import { useDashboard } from "@/context/DashboardContext";
import { History, MessageSquare, Clock } from "lucide-react";
import { ThemeToggle } from "./ThemeToggle";

export function Sidebar() {
    const { data: session } = useSession();
    const { apiKey, setApiKey, mistralKey, setMistralKey, aiProvider, setAiProvider, dataSources, setDataSources, addDataSource, removeDataSource, isSidebarOpen, setSidebarOpen, setMessages, setActiveChatId, activeChatId, view, setView } = useDashboard();
    const [apiKeyStatus, setApiKeyStatus] = useState<"idle" | "success" | "error">("idle");
    const [errorMsg, setErrorMsg] = useState("");
    const [uploading, setUploading] = useState(false);
    const [showSqlInput, setShowSqlInput] = useState(false);
    const [showGSheetsInput, setShowGSheetsInput] = useState(false);
    const [sqlUrl, setSqlUrl] = useState("");
    const [gsheetsUrl, setGsheetsUrl] = useState("");
    const [history, setHistory] = useState<any[]>([]);
    const [savedSources, setSavedSources] = useState<any[]>([]);
    const [saveConnection, setSaveConnection] = useState(false);
    const [sourceName, setSourceName] = useState("");

    const userId = session?.user?.email || "invitado@agente-bi.local";

    useEffect(() => {
        if (userId) {
            fetchHistory();
            fetchSources();
        }
    }, [userId, activeChatId]);

    const fetchSources = async () => {
        try {
            const data = await getDataSources(userId);
            setSavedSources(data);
        } catch (err) {
            console.error("Error fetching sources:", err);
        }
    };

    const fetchHistory = async () => {
        try {
            const data = await getHistory(userId);
            setHistory(data);
        } catch (err) {
            console.error("Error fetching history:", err);
        }
    };

    const loadChat = async (id: number) => {
        try {
            const res = await getChatDetails(id, userId);
            setMessages(res.messages);
            setActiveChatId(id);
            
            // Restaurar fuentes de datos vinculadas
            if (res.data_sources && Array.isArray(res.data_sources)) {
                setDataSources(res.data_sources.map((s: any) => ({
                    id: s.id,
                    filename: s.name,
                    columns: s.columns || []
                })));
            } else if (res.data_source) {
                // Fallback para chats antiguos
                setDataSources([{
                    id: res.data_source.id,
                    filename: res.data_source.name,
                    columns: res.data_source.columns || []
                }]);
            }

            setView('chat');
            if (window.innerWidth < 1024) setSidebarOpen(false);
        } catch (err) {
            alert("Error al cargar chat");
        }
    };

    const handleApiKeyChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const val = e.target.value;
        setApiKey(val);
        if (val.length > 20) {
            try {
                const res = await validateApiKey(val, "gemini");
                if (res.valid) {
                    setApiKeyStatus("success");
                } else {
                    setApiKeyStatus("error");
                    setErrorMsg(res.error);
                }
            } catch (err) {
                setApiKeyStatus("error");
                setErrorMsg("Error de conexión con el servidor");
            }
        } else {
            setApiKeyStatus("idle");
        }
    };

    const [mistralKeyStatus, setMistralKeyStatus] = useState<"idle" | "success" | "error">("idle");

    const handleMistralKeyChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const val = e.target.value;
        setMistralKey(val);
        if (val.length > 10) {
            try {
                const res = await validateApiKey(val, "mistral");
                if (res.valid) {
                    setMistralKeyStatus("success");
                } else {
                    setMistralKeyStatus("error");
                }
            } catch (err) {
                setMistralKeyStatus("error");
            }
        } else {
            setMistralKeyStatus("idle");
        }
    };

    const onFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files || e.target.files.length === 0) return;
        
        setUploading(true);
        const files = Array.from(e.target.files);
        
        try {
            for (const file of files) {
                const res = await uploadFile(file, userId);
                addDataSource({ 
                    id: (res as any).id, 
                    filename: res.filename, 
                    columns: res.columns,
                    type: 'file'
                });
            }
            fetchSources();
            setView('chat'); 
        } catch (err: any) {
            console.error(err);
            alert("Error al subir archivos: " + (err.message || "Error desconocido"));
        } finally {
            setUploading(false);
            if (e.target) e.target.value = '';
        }
    };

    const handleSqlConnect = async (url?: string) => {
        if (!sqlUrl && !url) return;
        setUploading(true);
        try {
            const res = await connectSql(url || sqlUrl, userId);
            addDataSource({ filename: "Base de Datos SQL", columns: ["SQL Engine Active"], type: 'sql' });
            if (saveConnection && sourceName && !url) {
                await saveDataSource(userId, sourceName, 'sql', sqlUrl);
                fetchSources();
            }
            setShowSqlInput(false);
            setSqlUrl("");
            setSourceName("");
        } catch (err: any) {
            console.error(err);
            alert("Error SQL: " + (err.message || "Error de conexión"));
        } finally {
            setUploading(false);
        }
    };

    const handleGSheetsConnect = async (url?: string) => {
        if (!gsheetsUrl && !url) return;
        setUploading(true);
        try {
            const res = await connectGoogleSheets(url || gsheetsUrl, userId);
            addDataSource({ filename: "Google Sheet", columns: res.columns, type: 'gsheets' });
            if (saveConnection && sourceName && !url) {
                await saveDataSource(userId, sourceName, 'gsheets', gsheetsUrl);
                fetchSources();
            }
            setShowGSheetsInput(false);
            setGsheetsUrl("");
            setSourceName("");
        } catch (err: any) {
            console.error(err);
            alert("Error Google Sheets: " + (err.message || "Verifica que la hoja sea pública"));
        } finally {
            setUploading(false);
        }
    };

    const handleDeleteSource = async (id: number) => {
        if (!confirm("¿Eliminar esta fuente guardada?")) return;
        try {
            await deleteDataSource(id, userId);
            fetchSources();
        } catch (err) {
            alert("Error al eliminar fuente");
        }
    };

    const handleRemoveActiveSource = async (source: any) => {
        if (source.id) {
            try {
                await removeSessionSource(userId, source.id);
            } catch (err) {
                console.error("Error removing from session:", err);
            }
        }
        removeDataSource(source.filename);
    };

    return (
        <>
            {/* Overlay para móvil */}
            {isSidebarOpen && (
                <div
                    className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
                    onClick={() => setSidebarOpen(false)}
                />
            )}

            <aside className={`
                fixed lg:relative inset-y-0 left-0 z-50
                w-80 bg-[var(--bg-secondary)] border-r border-[var(--border-color)] flex flex-col h-screen overflow-hidden
                transition-transform duration-300 ease-in-out
                ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
            `}>
                <div className="p-6 border-b border-[var(--border-color)] bg-[var(--bg-secondary)] relative">
                    {/* Botón cerrar en móvil */}
                    <button
                        onClick={() => setSidebarOpen(false)}
                        className="lg:hidden absolute right-4 top-4 p-2 text-gray-500 hover:text-white"
                    >
                        <X className="w-5 h-5" />
                    </button>

                    <div className="flex items-center gap-3 mb-8 group cursor-default">
                        <div className="p-2.5 bg-blue-600 rounded-xl shadow-lg shadow-blue-600/20 group-hover:scale-110 transition-transform">
                            <Activity className="w-6 h-6 text-white" />
                        </div>
                        <h1 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">Vektra BI <span className="text-[10px] bg-blue-600/20 text-blue-400 py-0.5 px-1.5 rounded ml-1 uppercase">v2.5</span></h1>
                    </div>

                    <div className="grid grid-cols-2 gap-2 mb-6">
                        <button
                            onClick={() => setView('chat')}
                            className={`flex flex-col items-center justify-center p-3 rounded-xl border transition-all ${view === 'chat' ? 'bg-blue-600/10 border-blue-500/30 text-blue-400' : 'bg-[var(--bg-tertiary)] border-[var(--border-color)] text-[var(--text-secondary)] hover:bg-gray-100 dark:hover:bg-white/[0.05]'}`}
                        >
                            <MessageSquare className="w-5 h-5 mb-1" />
                            <span className="text-[9px] font-black uppercase tracking-tighter">Chat</span>
                        </button>
                        <button
                            onClick={() => setView('dashboard')}
                            className={`flex flex-col items-center justify-center p-3 rounded-xl border transition-all ${view === 'dashboard' ? 'bg-blue-600/10 border-blue-500/30 text-blue-400' : 'bg-[var(--bg-tertiary)] border-[var(--border-color)] text-[var(--text-secondary)] hover:bg-gray-100 dark:hover:bg-white/[0.05]'}`}
                        >
                            <Activity className="w-5 h-5 mb-1" />
                            <span className="text-[9px] font-black uppercase tracking-tighter">Panel</span>
                        </button>
                        <button
                            onClick={() => setView('simulation')}
                            className={`flex flex-col items-center justify-center p-3 rounded-xl border transition-all ${view === 'simulation' ? 'bg-blue-600/10 border-blue-500/30 text-blue-400' : 'bg-[var(--bg-tertiary)] border-[var(--border-color)] text-[var(--text-secondary)] hover:bg-gray-100 dark:hover:bg-white/[0.05]'}`}
                        >
                            <Brain className="w-5 h-5 mb-1" />
                            <span className="text-[9px] font-black uppercase tracking-tighter">Simulador</span>
                        </button>
                        <button
                            onClick={() => setView('settings')}
                            className={`flex flex-col items-center justify-center p-3 rounded-xl border transition-all ${view === 'settings' ? 'bg-blue-600/10 border-blue-500/30 text-blue-400' : 'bg-[var(--bg-tertiary)] border-[var(--border-color)] text-[var(--text-secondary)] hover:bg-gray-100 dark:hover:bg-white/[0.05]'}`}
                        >
                            <Settings className="w-5 h-5 mb-1" />
                            <span className="text-[9px] font-black uppercase tracking-tighter">Config</span>
                        </button>
                    </div>

                    {process.env.NEXT_PUBLIC_ENABLE_VISUAL_SUMMARY === 'true' && (
                        <button
                            onClick={() => setView('visual-summary')}
                            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl border mb-6 transition-all ${
                                view === 'visual-summary'
                                    ? 'bg-blue-600/10 border-blue-500/30 text-blue-400 shadow-md shadow-blue-500/5'
                                    : 'bg-gradient-to-r from-blue-600/10 to-indigo-600/5 border-blue-500/10 text-gray-400 hover:text-white hover:border-blue-500/20'
                            }`}
                        >
                            <div className="p-1.5 bg-blue-600/20 rounded-lg text-blue-400">
                                <Sparkles className="w-4 h-4 animate-pulse" />
                            </div>
                            <div className="flex-1 text-left">
                                <span className="text-[10px] font-black uppercase tracking-wider block">Resumen Visual</span>
                                <span className="text-[8px] text-gray-500 font-bold block">EXPERIMENTO NAPKIN AI</span>
                            </div>
                        </button>
                    )}

                    <div className="bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-2xl p-4 flex items-center gap-3 hover:bg-[var(--bg-primary)] transition-colors">
                        <img src={session?.user?.image || ""} className="w-10 h-10 rounded-full border-2 border-blue-600/30" alt="Profile" />
                        <div className="overflow-hidden">
                            <p className="text-sm font-semibold text-[var(--text-primary)] truncate">{session?.user?.name}</p>
                            <p className="text-[10px] text-[var(--text-tertiary)] font-medium truncate italic uppercase tracking-tighter">Socio Consultor • 2026</p>
                        </div>
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto p-4 space-y-8 custom-scrollbar">
                    {/* Fuentes de Datos ACTIVAS */}
                    <div>
                        <div className="flex items-center justify-between mb-4 px-1">
                            <label className="flex items-center gap-2 text-[10px] font-black text-gray-600 uppercase tracking-[0.2em]">
                                <Database className="w-3.5 h-3.5" /> Pool de Datos ({dataSources.length}/10)
                            </label>
                            {dataSources.length > 0 && (
                                <button 
                                    onClick={async () => {
                                        try {
                                            await clearSession(userId);
                                            setDataSources([]);
                                        } catch (err) {
                                            setDataSources([]);
                                        }
                                    }}
                                    className="text-[9px] font-black text-red-500/50 hover:text-red-500 uppercase tracking-tighter transition-colors"
                                >
                                    Limpiar Todo
                                </button>
                            )}
                        </div>

                        <div className="space-y-3">
                            {dataSources.map((source, idx) => (
                                <div key={idx} className="bg-blue-600/5 border border-blue-500/20 rounded-xl p-3 relative overflow-hidden group animate-in slide-in-from-left-2 duration-300">
                                    <div className="flex items-center gap-3">
                                        <div className="p-1.5 bg-blue-500/20 rounded-lg">
                                            {source.type === 'sql' ? <Database className="w-4 h-4 text-blue-400" /> : <FileText className="w-4 h-4 text-blue-400" />}
                                        </div>
                                        <div className="overflow-hidden flex-1">
                                            <p className="text-xs font-bold text-blue-100 truncate">{source.filename}</p>
                                            <p className="text-[9px] text-blue-400/80 font-bold uppercase">{source.columns.length} Cols</p>
                                        </div>
                                        <button 
                                            onClick={() => handleRemoveActiveSource(source)}
                                            className="p-1 text-blue-400/30 hover:text-red-400 transition-colors"
                                        >
                                            <X className="w-3.5 h-3.5" />
                                        </button>
                                    </div>
                                </div>
                            ))}

                            {dataSources.length < 10 && (
                                <div className="group relative border-2 border-dashed border-white/5 rounded-2xl p-6 text-center hover:border-blue-500/30 hover:bg-blue-500/[0.02] transition-all cursor-pointer overflow-hidden">
                                    <input type="file" multiple className="absolute inset-0 opacity-0 cursor-pointer z-10" onChange={onFileUpload} />
                                    {uploading ? (
                                        <div className="flex flex-col items-center gap-2">
                                            <Activity className="w-6 h-6 text-blue-500 animate-pulse" />
                                            <p className="text-[10px] text-blue-400 font-black animate-pulse uppercase tracking-widest">Cargando...</p>
                                        </div>
                                    ) : (
                                        <>
                                            <div className="w-10 h-10 bg-white/[0.02] rounded-full flex items-center justify-center mx-auto mb-3 group-hover:bg-blue-600/10 transition-colors">
                                                <Upload className="w-5 h-5 text-gray-600 group-hover:text-blue-500 transition-colors" />
                                            </div>
                                            <p className="text-xs text-gray-400 font-bold group-hover:text-gray-200 uppercase tracking-tighter">Subir Nuevo Dataset</p>
                                        </>
                                    )}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Conectores Rápidos */}
                    <div className="space-y-2">
                        <button
                            onClick={() => setShowGSheetsInput(!showGSheetsInput)}
                            className="w-full flex items-center justify-between px-5 py-3 bg-white/[0.02] border border-white/5 rounded-xl text-gray-500 hover:text-white hover:bg-white/[0.05] transition-all"
                        >
                            <span className="text-[10px] font-black uppercase tracking-widest text-emerald-500/80">Google Sheets</span>
                            <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showGSheetsInput ? 'rotate-180' : ''}`} />
                        </button>
                        {showGSheetsInput && (
                            <div className="p-3 bg-white/[0.02] border border-white/5 rounded-xl space-y-3 animate-in fade-in slide-in-from-top-2">
                                <input
                                    type="text"
                                    value={gsheetsUrl}
                                    onChange={(e) => setGsheetsUrl(e.target.value)}
                                    placeholder="URL de la hoja pública..."
                                    className="w-full bg-black border border-white/10 rounded-lg px-4 py-2 text-xs text-white focus:outline-none focus:border-blue-500/50"
                                />
                                <button
                                    onClick={() => handleGSheetsConnect()}
                                    className="w-full py-2 bg-blue-600 hover:bg-blue-500 text-white text-[10px] font-black uppercase tracking-widest rounded-lg transition-all"
                                >
                                    Conectar
                                </button>
                            </div>
                        )}
                        
                        <button
                            onClick={() => setShowSqlInput(!showSqlInput)}
                            className="w-full flex items-center justify-between px-5 py-3 bg-white/[0.02] border border-white/5 rounded-xl text-gray-500 hover:text-white hover:bg-white/[0.05] transition-all"
                        >
                            <span className="text-[10px] font-black uppercase tracking-widest text-blue-500/80">Base de Datos SQL</span>
                            <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showSqlInput ? 'rotate-180' : ''}`} />
                        </button>
                        {showSqlInput && (
                            <div className="p-3 bg-white/[0.02] border border-white/5 rounded-xl space-y-3 animate-in fade-in slide-in-from-top-2">
                                <input
                                    type="text"
                                    value={sqlUrl}
                                    onChange={(e) => setSqlUrl(e.target.value)}
                                    placeholder="URL: postgresql://..."
                                    className="w-full bg-black border border-white/10 rounded-lg px-4 py-2 text-xs text-white focus:outline-none focus:border-blue-500/50"
                                />
                                <button
                                    onClick={() => handleSqlConnect()}
                                    className="w-full py-2 bg-blue-600 hover:bg-blue-500 text-white text-[10px] font-black uppercase tracking-widest rounded-lg transition-all"
                                >
                                    Conectar
                                </button>
                            </div>
                        )}
                    </div>

                    {/* Historial */}
                    <div className="pt-4 border-t border-white/5">
                        <label className="flex items-center gap-2 text-[10px] font-black text-gray-600 uppercase tracking-[0.2em] mb-4">
                            <History className="w-3.5 h-3.5" /> Historial Reciente
                        </label>
                        <div className="space-y-2 pb-8">
                            {history.slice(0, 5).map((chat) => (
                                <button
                                    key={chat.id}
                                    onClick={() => loadChat(chat.id)}
                                    className={`w-full flex items-center gap-3 p-3 rounded-xl transition-all border ${activeChatId === chat.id
                                        ? 'bg-blue-600/10 border-blue-500/30 text-blue-400'
                                        : 'bg-white/[0.02] border-white/5 text-gray-500 hover:text-gray-300'
                                        }`}
                                >
                                    <MessageSquare className="w-3.5 h-3.5" />
                                    <p className="text-[10px] font-bold truncate flex-1 text-left tracking-tight">{chat.title}</p>
                                </button>
                            ))}
                        </div>
                    </div>
                </div>

                <div className="p-6 border-t border-[var(--border-color)] bg-[var(--bg-secondary)] space-y-3">
                    <ThemeToggle />
                    <button
                        onClick={() => signOut()}
                        className="w-full flex items-center justify-center gap-2 px-4 py-4 text-gray-500 hover:text-red-400 hover:bg-red-500/10 rounded-2xl transition-all text-xs font-black uppercase tracking-[0.2em]"
                    >
                        <LogOut className="w-4 h-4" /> Salir
                    </button>
                </div>
            </aside>
        </>
    );
}
