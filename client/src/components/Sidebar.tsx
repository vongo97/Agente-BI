'use client';

import { useSession, signOut } from "next-auth/react";
import { Upload, Settings, Database, LogOut, ChevronDown, Activity, CheckCircle2, AlertCircle, FileText, X, Menu } from "lucide-react";
import { useState, useEffect } from "react";
import { validateApiKey, uploadFile, connectSql, connectGoogleSheets, getHistory, getChatDetails, getPdfExportUrl } from "@/lib/api";
import { useDashboard } from "@/context/DashboardContext";
import { History, MessageSquare, Clock } from "lucide-react";
import { ThemeToggle } from "./ThemeToggle";

export function Sidebar() {
    const { data: session } = useSession();
    const { apiKey, setApiKey, mistralKey, setMistralKey, aiProvider, setAiProvider, dataSource, setDataSource, isSidebarOpen, setSidebarOpen, setMessages, setActiveChatId, activeChatId, view, setView } = useDashboard();
    const [apiKeyStatus, setApiKeyStatus] = useState<"idle" | "success" | "error">("idle");
    const [errorMsg, setErrorMsg] = useState("");
    const [uploading, setUploading] = useState(false);
    const [showSqlInput, setShowSqlInput] = useState(false);
    const [showGSheetsInput, setShowGSheetsInput] = useState(false);
    const [sqlUrl, setSqlUrl] = useState("");
    const [gsheetsUrl, setGsheetsUrl] = useState("");
    const [history, setHistory] = useState<any[]>([]);

    const userId = session?.user?.email || "default_user";

    useEffect(() => {
        if (userId) {
            fetchHistory();
        }
    }, [userId, activeChatId]);

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
                const res = await validateApiKey(val);
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

    const onFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files?.[0]) return;
        setUploading(true);
        try {
            const res = await uploadFile(e.target.files[0], userId);
            setMessages([]); // Limpiar chat anterior para nueva fuente
            setActiveChatId(null);
            setDataSource({ filename: res.filename, columns: res.columns });
        } catch (err: any) {
            console.error(err);
            alert("Error al subir archivo: " + (err.message || "Error desconocido"));
        } finally {
            setUploading(false);
        }
    };

    const handleSqlConnect = async () => {
        if (!sqlUrl) return;
        setUploading(true);
        try {
            const res = await connectSql(sqlUrl, userId);
            setMessages([]); // Limpiar chat anterior
            setActiveChatId(null);
            setDataSource({ filename: "Base de Datos SQL", columns: ["SQL Engine Active"] });
            setShowSqlInput(false);
        } catch (err: any) {
            console.error(err);
            alert("Error SQL: " + (err.message || "Error de conexión"));
        } finally {
            setUploading(false);
        }
    };

    const handleGSheetsConnect = async () => {
        if (!gsheetsUrl) return;
        setUploading(true);
        try {
            const res = await connectGoogleSheets(gsheetsUrl, userId);
            setMessages([]); // Limpiar chat anterior
            setActiveChatId(null);
            setDataSource({ filename: "Google Sheet", columns: res.columns });
            setShowGSheetsInput(false);
        } catch (err: any) {
            console.error(err);
            alert("Error Google Sheets: " + (err.message || "Verifica que la hoja sea pública"));
        } finally {
            setUploading(false);
        }
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
                        <h1 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">Agente BI <span className="text-[10px] bg-blue-600/20 text-blue-400 py-0.5 px-1.5 rounded ml-1 uppercase">v2.5</span></h1>
                    </div>

                    <div className="grid grid-cols-2 gap-2 mb-6">
                        <button
                            onClick={() => setView('chat')}
                            className={`flex flex-col items-center justify-center p-3 rounded-xl border transition-all ${view === 'chat' ? 'bg-blue-600/10 border-blue-500/30 text-blue-400' : 'bg-[var(--bg-tertiary)] border-[var(--border-color)] text-[var(--text-secondary)] hover:bg-gray-100 dark:hover:bg-white/[0.05]'}`}
                        >
                            <MessageSquare className="w-5 h-5 mb-1" />
                            <span className="text-[10px] font-black uppercase tracking-tighter">Chat</span>
                        </button>
                        <button
                            onClick={() => setView('dashboard')}
                            className={`flex flex-col items-center justify-center p-3 rounded-xl border transition-all ${view === 'dashboard' ? 'bg-blue-600/10 border-blue-500/30 text-blue-400' : 'bg-[var(--bg-tertiary)] border-[var(--border-color)] text-[var(--text-secondary)] hover:bg-gray-100 dark:hover:bg-white/[0.05]'}`}
                        >
                            <Activity className="w-5 h-5 mb-1" />
                            <span className="text-[10px] font-black uppercase tracking-tighter">Panel</span>
                        </button>
                    </div>

                    <div className="bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-2xl p-4 flex items-center gap-3 hover:bg-[var(--bg-primary)] transition-colors">
                        <img src={session?.user?.image || ""} className="w-10 h-10 rounded-full border-2 border-blue-600/30" alt="Profile" />
                        <div className="overflow-hidden">
                            <p className="text-sm font-semibold text-[var(--text-primary)] truncate">{session?.user?.name}</p>
                            <p className="text-[10px] text-[var(--text-tertiary)] font-medium truncate italic uppercase tracking-tighter">Sesión de Análisis Activa</p>
                        </div>
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto p-4 space-y-8 custom-scrollbar">
                    {/* Configuración */}
                    <div>
                        <label className="flex items-center gap-2 text-[10px] font-black text-[var(--text-tertiary)] uppercase tracking-[0.2em] mb-4">
                            <Settings className="w-3.5 h-3.5" /> Configuración IA
                        </label>
                        <div className="space-y-4">
                            {/* Selector de Proveedor */}
                            <div className="bg-[var(--bg-tertiary)] p-1 rounded-xl flex gap-1">
                                <button
                                    onClick={() => setAiProvider("gemini")}
                                    className={`flex-1 py-1.5 text-[9px] lg:text-[10px] font-bold uppercase tracking-wider rounded-lg transition-all ${aiProvider === 'gemini' ? 'bg-blue-600 text-white shadow-md' : 'text-[var(--text-secondary)] hover:bg-black/5 dark:hover:bg-white/5'}`}
                                >
                                    Gemini
                                </button>
                                <button
                                    onClick={() => setAiProvider("mistral")}
                                    className={`flex-1 py-1.5 text-[9px] lg:text-[10px] font-bold uppercase tracking-wider rounded-lg transition-all ${aiProvider === 'mistral' ? 'bg-purple-600 text-white shadow-md' : 'text-[var(--text-secondary)] hover:bg-black/5 dark:hover:bg-white/5'}`}
                                >
                                    Mistral
                                </button>
                                <button
                                    onClick={() => setAiProvider("hybrid")}
                                    className={`flex-1 py-1.5 text-[9px] lg:text-[10px] font-bold uppercase tracking-wider rounded-lg transition-all ${aiProvider === 'hybrid' ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-md' : 'text-[var(--text-secondary)] hover:bg-black/5 dark:hover:bg-white/5'}`}
                                    title="Modo Colaborativo: Gemini (Ingeniero) + Mistral (Estratega)"
                                >
                                    Dual
                                </button>
                            </div>

                            {/* Google API Key - Solo en Gemini o Dual */}
                            {(aiProvider === 'gemini' || aiProvider === 'hybrid') && (
                                <div className="relative">
                                    <input
                                        type="password"
                                        value={apiKey}
                                        onChange={handleApiKeyChange}
                                        placeholder="Google API Key (Gemini)..."
                                        className="w-full bg-[var(--bg-tertiary)] border border-blue-500/50 focus:border-blue-500 focus:ring-4 focus:ring-blue-500/5 rounded-xl px-4 py-3 text-sm text-[var(--text-primary)] placeholder-[var(--text-tertiary)] focus:outline-none transition-all"
                                    />
                                    <div className="absolute right-3 top-1/2 -translate-y-1/2">
                                        {apiKeyStatus === "success" && <CheckCircle2 className="w-4 h-4 text-green-500" />}
                                        {apiKeyStatus === "error" && <AlertCircle className="w-4 h-4 text-red-500" />}
                                    </div>
                                </div>
                            )}

                            {/* Mistral API Key - Solo en Mistral o Dual */}
                            {(aiProvider === 'mistral' || aiProvider === 'hybrid') && (
                                <div className="relative">
                                    <input
                                        type="password"
                                        value={mistralKey}
                                        onChange={(e) => setMistralKey(e.target.value)}
                                        placeholder="Mistral API Key (Mistral)..."
                                        className="w-full bg-[var(--bg-tertiary)] border border-purple-500/50 focus:border-purple-500 focus:ring-4 focus:ring-purple-500/5 rounded-xl px-4 py-3 text-sm text-[var(--text-primary)] placeholder-[var(--text-tertiary)] focus:outline-none transition-all"
                                    />
                                </div>
                            )}
                        </div>
                    </div>


                    {/* Fuentes de Datos */}
                    <div>
                        <label className="flex items-center gap-2 text-[10px] font-black text-gray-600 uppercase tracking-[0.2em] mb-4">
                            <Database className="w-3.5 h-3.5" /> Fuentes de Datos
                        </label>
                        <div className="space-y-4">
                            {dataSource ? (
                                <div className="bg-blue-600/5 border border-blue-500/20 rounded-xl p-4 relative overflow-hidden group">
                                    <div className="flex items-center gap-3">
                                        <div className="p-2 bg-blue-500/20 rounded-lg">
                                            <FileText className="w-5 h-5 text-blue-400" />
                                        </div>
                                        <div className="overflow-hidden">
                                            <p className="text-sm font-semibold text-blue-100 truncate">{dataSource.filename}</p>
                                            <p className="text-[10px] text-blue-400 font-bold uppercase">{dataSource.columns.length} Columnas Detectadas</p>
                                        </div>
                                    </div>
                                    <button
                                        onClick={() => setDataSource(null)}
                                        className="mt-3 w-full py-2 text-[10px] font-bold text-blue-400/50 hover:text-blue-400 uppercase tracking-widest transition-colors"
                                    >
                                        Eliminar Fuente
                                    </button>
                                </div>
                            ) : (
                                <>
                                    <div className="group relative border-2 border-dashed border-white/5 rounded-2xl p-8 text-center hover:border-blue-500/30 hover:bg-blue-500/[0.02] transition-all cursor-pointer overflow-hidden">
                                        <input type="file" className="absolute inset-0 opacity-0 cursor-pointer z-10" onChange={onFileUpload} />
                                        {uploading ? (
                                            <div className="flex flex-col items-center gap-2">
                                                <Activity className="w-8 h-8 text-blue-500 animate-pulse" />
                                                <p className="text-sm text-blue-400 font-bold animate-pulse">Procesando...</p>
                                            </div>
                                        ) : (
                                            <>
                                                <div className="w-12 h-12 bg-white/[0.02] rounded-full flex items-center justify-center mx-auto mb-4 group-hover:bg-blue-600/10 transition-colors">
                                                    <Upload className="w-6 h-6 text-gray-600 group-hover:text-blue-500 transition-colors" />
                                                </div>
                                                <p className="text-sm text-gray-400 font-medium group-hover:text-gray-200">Subir CSV o Excel</p>
                                                <p className="text-[10px] text-gray-600 mt-1 uppercase tracking-tighter">Arrastra tus datos aquí</p>
                                            </>
                                        )}
                                    </div>

                                    {/* Conector Google Sheets */}
                                    <div className="space-y-2">
                                        <button
                                            onClick={() => setShowGSheetsInput(!showGSheetsInput)}
                                            className="w-full flex items-center justify-between px-5 py-4 bg-white/[0.02] border border-white/5 rounded-2xl text-gray-500 hover:text-white hover:bg-white/[0.05] hover:border-white/10 transition-all group"
                                        >
                                            <span className="text-xs font-bold uppercase tracking-widest">Google Sheets</span>
                                            <ChevronDown className={`w-4 h-4 transition-transform ${showGSheetsInput ? 'rotate-180' : ''}`} />
                                        </button>
                                        {showGSheetsInput && (
                                            <div className="p-4 bg-white/[0.02] border border-white/5 rounded-2xl space-y-3 animate-in fade-in slide-in-from-top-2">
                                                <input
                                                    type="text"
                                                    value={gsheetsUrl}
                                                    onChange={(e) => setGsheetsUrl(e.target.value)}
                                                    placeholder="Pegar URL de la hoja..."
                                                    className="w-full bg-black border border-white/10 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-blue-500/50"
                                                />
                                                <button
                                                    onClick={handleGSheetsConnect}
                                                    className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-[10px] font-black uppercase tracking-widest rounded-xl transition-all"
                                                >
                                                    Conectar Hoja
                                                </button>
                                            </div>
                                        )}
                                    </div>

                                    {/* Conector SQL */}
                                    <div className="space-y-2">
                                        <button
                                            onClick={() => setShowSqlInput(!showSqlInput)}
                                            className="w-full flex items-center justify-between px-5 py-4 bg-white/[0.02] border border-white/5 rounded-2xl text-gray-500 hover:text-white hover:bg-white/[0.05] hover:border-white/10 transition-all group"
                                        >
                                            <span className="text-xs font-bold uppercase tracking-widest">Base de Datos SQL</span>
                                            <ChevronDown className={`w-4 h-4 transition-transform ${showSqlInput ? 'rotate-180' : ''}`} />
                                        </button>
                                        {showSqlInput && (
                                            <div className="p-4 bg-white/[0.02] border border-white/5 rounded-2xl space-y-3 animate-in fade-in slide-in-from-top-2">
                                                <input
                                                    type="text"
                                                    value={sqlUrl}
                                                    onChange={(e) => setSqlUrl(e.target.value)}
                                                    placeholder="postgresql://user:pass@host/db"
                                                    className="w-full bg-black border border-white/10 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-blue-500/50"
                                                />
                                                <button
                                                    onClick={handleSqlConnect}
                                                    className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-[10px] font-black uppercase tracking-widest rounded-xl transition-all"
                                                >
                                                    Conectar SQL
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                </>
                            )}
                        </div>
                    </div>

                    {/* Historial de Análisis */}
                    <div className="pt-4 border-t border-white/5">
                        <label className="flex items-center gap-2 text-[10px] font-black text-gray-600 uppercase tracking-[0.2em] mb-4">
                            <History className="w-3.5 h-3.5" /> Historial Reciente
                        </label>
                        <div className="space-y-2 pb-8">
                            {history.length === 0 ? (
                                <div className="p-4 border border-dashed border-white/5 rounded-xl text-center">
                                    <p className="text-[10px] text-gray-600 font-bold uppercase tracking-tight">Sin historial previo</p>
                                </div>
                            ) : (
                                history.map((chat) => (
                                    <button
                                        key={chat.id}
                                        onClick={() => loadChat(chat.id)}
                                        className={`w-full flex items-center gap-3 p-3 rounded-xl transition-all border ${activeChatId === chat.id
                                            ? 'bg-blue-600/10 border-blue-500/30 text-blue-400'
                                            : 'bg-white/[0.02] border-white/5 text-gray-500 hover:bg-white/[0.05] hover:border-white/10 hover:text-gray-300'
                                            }`}
                                    >
                                        <div className={`p-1.5 rounded-lg flex-shrink-0 ${activeChatId === chat.id ? 'bg-blue-500/20' : 'bg-white/5'}`}>
                                            <MessageSquare className="w-3.5 h-3.5" />
                                        </div>
                                        <div className="flex-1 text-left overflow-hidden">
                                            <p className="text-[11px] font-bold truncate tracking-tight">{chat.title}</p>
                                            <div className="flex items-center gap-1 mt-0.5 opacity-50">
                                                <Clock className="w-2.5 h-2.5" />
                                                <p className="text-[8px] font-black uppercase">{new Date(chat.created_at).toLocaleDateString()}</p>
                                            </div>
                                        </div>
                                    </button>
                                ))
                            )}
                        </div>
                    </div>
                </div>


                <div className="p-6 border-t border-[var(--border-color)] bg-[var(--bg-secondary)] space-y-3">
                    <ThemeToggle />
                    <button
                        onClick={() => signOut()}
                        className="w-full flex items-center justify-center gap-2 px-4 py-4 text-gray-500 hover:text-red-400 hover:bg-red-500/10 rounded-2xl transition-all text-xs font-black uppercase tracking-[0.2em]"
                    >
                        <LogOut className="w-4 h-4" /> Salir del Sistema
                    </button>
                </div>
            </aside>
        </>
    );
}
