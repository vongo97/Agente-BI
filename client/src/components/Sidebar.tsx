'use client';

import { useSession, signOut } from "next-auth/react";
import {
    Upload, Settings, Database, LogOut, ChevronDown, Activity,
    FileText, X, Brain, Sparkles,
    MessageSquare, History, LayoutDashboard, LogIn
} from "lucide-react";
import { useState, useEffect, useCallback } from "react";
import {
    uploadFile, connectSql, connectGoogleSheets,
    getHistory, getChatDetails, getDataSources,
    removeSessionSource, clearSession
} from "@/lib/api";
import { useDashboard } from "@/context/DashboardContext";
import { ChatSession, DataSource } from "@/types/shared";
import { ThemeToggle } from "./ThemeToggle";

/* ── Navigation items ─────────────────────────────── */
const NAV_ITEMS = [
    { view: 'chat',       label: 'Chat',       icon: MessageSquare },
    { view: 'dashboard',  label: 'Panel',       icon: LayoutDashboard },
    { view: 'simulation', label: 'Simulador',   icon: Brain },
    { view: 'settings',   label: 'Configuración', icon: Settings },
] as const;

type NavView = typeof NAV_ITEMS[number]['view'] | 'visual-summary';
// NavView is the union of navigation views used elsewhere in this module
export type { NavView };

export function Sidebar() {
    const { data: session } = useSession();
    const {
        dataSources, setDataSources, addDataSource, removeDataSource,
        isSidebarOpen, setSidebarOpen,
        setMessages, setActiveChatId, activeChatId,
        view, setView
    } = useDashboard();

    const [uploading, setUploading] = useState(false);
    const [showSqlInput, setShowSqlInput] = useState(false);
    const [showGSheetsInput, setShowGSheetsInput] = useState(false);
    const [sqlUrl, setSqlUrl] = useState("");
    const [gsheetsUrl, setGsheetsUrl] = useState("");
    const [history, setHistory] = useState<ChatSession[]>([]);
    const [savedSources, setSavedSources] = useState<DataSource[]>([]);

    const userId = session?.user?.email || "invitado@agente-bi.local";

    const fetchSources = useCallback(async () => {
        try { const data = await getDataSources(userId); setSavedSources(data); }
        catch (err) { console.error("Error fetching sources:", err); }
    }, [userId]);

    const fetchHistory = useCallback(async () => {
        try { const data = await getHistory(userId); setHistory(data); }
        catch (err) { console.error("Error fetching history:", err); }
    }, [userId]);

    useEffect(() => {
        if (userId) { fetchHistory(); fetchSources(); }
    }, [userId, activeChatId, fetchHistory, fetchSources]);

    const loadChat = async (id: number) => {
        try {
            const res = await getChatDetails(id, userId);
            setMessages(res.messages);
            setActiveChatId(id);
            if (res.data_sources && Array.isArray(res.data_sources)) {
                setDataSources((res.data_sources as DataSource[]).map((s) => ({
                    id: s.id, filename: s.name || s.filename, columns: s.columns || []
                })));
            } else if (res.data_source) {
                const ds = res.data_source as DataSource;
                setDataSources([{ id: ds.id, filename: ds.name || ds.filename, columns: ds.columns || [] }]);
            }
            setView('chat');
            if (window.innerWidth < 1024) setSidebarOpen(false);
        } catch (err) {
            console.error("Error loading chat:", err);
            alert("Error al cargar chat");
        }
    };


    const onFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files || e.target.files.length === 0) return;
        setUploading(true);
        const files = Array.from(e.target.files);
        try {
            for (const file of files) {
                const res = await uploadFile(file, userId) as { id: number; filename: string; columns: string[] };
                addDataSource({ id: res.id, filename: res.filename, columns: res.columns, type: 'file' });
            }
            fetchSources();
            setView('chat');
        } catch (err) {
            const error = err as Error;
            alert("Error al subir archivos: " + (error.message || "Error desconocido"));
        } finally {
            setUploading(false);
            if (e.target) e.target.value = '';
        }
    };

    const handleSqlConnect = async (url?: string) => {
        if (!sqlUrl && !url) return;
        setUploading(true);
        try {
            await connectSql(url || sqlUrl, userId);
            addDataSource({ filename: "Base de Datos SQL", columns: ["SQL Engine Active"], type: 'sql' });
            setShowSqlInput(false); setSqlUrl("");
        } catch (err) {
            const error = err as Error;
            alert("Error SQL: " + (error.message || "Error de conexión"));
        } finally { setUploading(false); }
    };

    const handleGSheetsConnect = async (url?: string) => {
        if (!gsheetsUrl && !url) return;
        setUploading(true);
        try {
            const res = await connectGoogleSheets(url || gsheetsUrl, userId);
            addDataSource({ filename: "Google Sheet", columns: res.columns, type: 'gsheets' });
            setShowGSheetsInput(false); setGsheetsUrl("");
        } catch (err) {
            const error = err as Error;
            alert("Error Google Sheets: " + (error.message || "Verifica que la hoja sea pública"));
        } finally { setUploading(false); }
    };


    const handleRemoveActiveSource = async (source: DataSource) => {
        if (source.id) {
            try { await removeSessionSource(userId, source.id); }
            catch (err) { console.error("Error removing from session:", err); }
        }
        removeDataSource(source.filename);
    };

    return (
        <>
            {/* Mobile overlay */}
            {isSidebarOpen && (
                <div
                    className="fixed inset-0 bg-black/60 backdrop-blur-md z-40 lg:hidden transition-all duration-300"
                    onClick={() => setSidebarOpen(false)}
                />
            )}

            <aside className={`
                fixed lg:relative inset-y-0 left-0 z-50
                w-60 flex flex-col h-screen overflow-hidden
                bg-[var(--bi-surface-0)] border-r border-[var(--bi-border)]
                transition-transform duration-300 ease-in-out
                ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
            `}>

                {/* ── Header ── */}
                <div className="flex items-center justify-between px-4 h-12 border-b border-[var(--bi-border)] flex-shrink-0">
                    <div className="flex items-center gap-2">
                        <div className="w-5 h-5 rounded bg-[var(--bi-teal)] flex items-center justify-center">
                            <Activity className="w-3 h-3 text-black" />
                        </div>
                        <span className="text-sm font-semibold text-[var(--bi-text-1)] tracking-tight">Vektra BI</span>
                        <span className="badge badge-teal">v2.5</span>
                    </div>
                    <button
                        onClick={() => setSidebarOpen(false)}
                        className="lg:hidden p-1 rounded text-[var(--bi-text-3)] hover:text-[var(--bi-text-1)] hover:bg-[var(--bi-surface-2)] transition-colors"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>

                {/* ── Scrollable body ── */}
                <div className="flex-1 overflow-y-auto custom-scrollbar">

                    {/* Navigation */}
                    <div className="p-2 border-b border-[var(--bi-border)]">
                        <nav className="space-y-0.5">
                            {NAV_ITEMS.map(({ view: v, label, icon: Icon }) => (
                                <button
                                    key={v}
                                    onClick={() => { setView(v); if (window.innerWidth < 1024) setSidebarOpen(false); }}
                                    className={`nav-item ${view === v ? 'active' : ''}`}
                                >
                                    <Icon className="w-4 h-4 flex-shrink-0" />
                                    <span>{label}</span>
                                </button>
                            ))}
                            {process.env.NEXT_PUBLIC_ENABLE_VISUAL_SUMMARY === 'true' && (
                                <button
                                    onClick={() => setView('visual-summary')}
                                    className={`nav-item ${view === 'visual-summary' ? 'active' : ''}`}
                                >
                                    <Sparkles className="w-4 h-4 flex-shrink-0" />
                                    <span>Resumen Visual</span>
                                    <span className="ml-auto badge badge-blue">Beta</span>
                                </button>
                            )}
                        </nav>
                    </div>

                    {/* Data sources */}
                    <div className="p-3 border-b border-[var(--bi-border)] space-y-2">
                        <div className="flex items-center justify-between">
                            <span className="section-label">
                                <Database className="w-3 h-3" />
                                Datos ({dataSources.length}/10)
                            </span>
                            {(dataSources.length > 0 || savedSources.length > 0) && (
                                <button
                                    onClick={async () => {
                                        try { await clearSession(userId); setDataSources([]); fetchSources(); }
                                        catch { setDataSources([]); fetchSources(); }
                                    }}
                                    className="text-[10px] font-medium text-[var(--bi-text-3)] hover:text-[var(--bi-red)] transition-colors"
                                >
                                    Limpiar
                                </button>
                            )}
                        </div>

                        {/* Active sources */}
                        <div className="space-y-1">
                            {dataSources.map((source, idx) => (
                                <div key={idx} className="source-chip animate-in slide-in-from-left-2 duration-300">
                                    <div className="w-5 h-5 rounded bg-[var(--bi-teal-dim)] border border-[var(--bi-teal-border)] flex items-center justify-center flex-shrink-0">
                                        {source.type === 'sql'
                                            ? <Database className="w-3 h-3 text-[var(--bi-teal)]" />
                                            : <FileText className="w-3 h-3 text-[var(--bi-teal)]" />
                                        }
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-xs font-medium text-[var(--bi-text-1)] truncate leading-tight">{source.filename}</p>
                                        <p className="text-[10px] text-[var(--bi-text-3)]">{source.columns.length} cols</p>
                                    </div>
                                    <button
                                        onClick={() => handleRemoveActiveSource(source)}
                                        className="p-0.5 rounded text-[var(--bi-text-3)] hover:text-[var(--bi-red)] transition-colors flex-shrink-0"
                                    >
                                        <X className="w-3 h-3" />
                                    </button>
                                </div>
                            ))}

                            {/* Upload drop zone */}
                            {dataSources.length < 10 && (
                                <div className="relative border border-dashed border-[var(--bi-border)] rounded-md p-3 text-center hover:border-[var(--bi-teal-border)] hover:bg-[var(--bi-teal-dim)] transition-all cursor-pointer group">
                                    <input
                                        type="file" multiple accept=".csv,.xlsx,.xls"
                                        className="absolute inset-0 opacity-0 cursor-pointer z-10"
                                        onChange={onFileUpload}
                                    />
                                    {uploading ? (
                                        <div className="flex items-center justify-center gap-2">
                                            <Activity className="w-3.5 h-3.5 text-[var(--bi-teal)] animate-pulse" />
                                            <span className="text-xs text-[var(--bi-teal)]">Cargando…</span>
                                        </div>
                                    ) : (
                                        <div className="flex items-center justify-center gap-2">
                                            <Upload className="w-3.5 h-3.5 text-[var(--bi-text-3)] group-hover:text-[var(--bi-teal)] transition-colors" />
                                            <span className="text-xs text-[var(--bi-text-3)] group-hover:text-[var(--bi-teal)] transition-colors">Subir CSV / Excel</span>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>

                        {/* Connectors */}
                        <div className="space-y-1 pt-1">
                            {/* Google Sheets */}
                            <button
                                onClick={() => setShowGSheetsInput(!showGSheetsInput)}
                                className="w-full flex items-center justify-between px-2.5 py-1.5 rounded-md border border-[var(--bi-border)] text-[var(--bi-text-3)] hover:text-[var(--bi-text-1)] hover:bg-[var(--bi-surface-1)] transition-all text-xs"
                            >
                                <span className="font-medium text-emerald-400/80">Google Sheets</span>
                                <ChevronDown className={`w-3 h-3 transition-transform ${showGSheetsInput ? 'rotate-180' : ''}`} />
                            </button>
                            {showGSheetsInput && (
                                <div className="p-2 bg-[var(--bi-surface-1)] border border-[var(--bi-border)] rounded-md space-y-2 animate-in fade-in duration-300">
                                    <input
                                        type="text" value={gsheetsUrl}
                                        onChange={e => setGsheetsUrl(e.target.value)}
                                        placeholder="URL de la hoja pública…"
                                        className="input-bi"
                                    />
                                    <button onClick={() => handleGSheetsConnect()} className="btn-primary w-full text-xs justify-center">
                                        Conectar
                                    </button>
                                </div>
                            )}

                            {/* SQL */}
                            <button
                                onClick={() => setShowSqlInput(!showSqlInput)}
                                className="w-full flex items-center justify-between px-2.5 py-1.5 rounded-md border border-[var(--bi-border)] text-[var(--bi-text-3)] hover:text-[var(--bi-text-1)] hover:bg-[var(--bi-surface-1)] transition-all text-xs"
                            >
                                <span className="font-medium text-[var(--bi-blue)]/80">Base de Datos SQL</span>
                                <ChevronDown className={`w-3 h-3 transition-transform ${showSqlInput ? 'rotate-180' : ''}`} />
                            </button>
                            {showSqlInput && (
                                <div className="p-2 bg-[var(--bi-surface-1)] border border-[var(--bi-border)] rounded-md space-y-2 animate-in fade-in duration-300">
                                    <input
                                        type="text" value={sqlUrl}
                                        onChange={e => setSqlUrl(e.target.value)}
                                        placeholder="postgresql://…"
                                        className="input-bi font-mono"
                                    />
                                    <button onClick={() => handleSqlConnect()} className="btn-primary w-full text-xs justify-center">
                                        Conectar
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* History */}
                    <div className="p-3 space-y-1">
                        <span className="section-label">
                            <History className="w-3 h-3" />
                            Recientes
                        </span>
                        <div className="space-y-0.5 mt-1">
                            {history.slice(0, 8).map((chat) => (
                                <button
                                    key={chat.id}
                                    onClick={() => loadChat(chat.id)}
                                    className={`nav-item ${activeChatId === chat.id ? 'active' : ''}`}
                                >
                                    <MessageSquare className="w-3.5 h-3.5 flex-shrink-0" />
                                    <span className="truncate text-xs">{chat.title}</span>
                                </button>
                            ))}
                            {history.length === 0 && (
                                <p className="text-[11px] text-[var(--bi-text-3)] px-1 py-2">Sin historial aún</p>
                            )}
                        </div>
                    </div>
                </div>

                {/* ── Footer ── */}
                <div className="flex-shrink-0 border-t border-[var(--bi-border)] p-3 space-y-2">
                    {/* User row */}
                    {session?.user && (
                        <div className="flex items-center gap-2 px-1">
                            {session.user.image
                                // eslint-disable-next-line @next/next/no-img-element
                                ? <img src={session.user.image} className="w-6 h-6 rounded-full border border-[var(--bi-border)]" alt="Avatar" />
                                : <div className="w-6 h-6 rounded-full bg-[var(--bi-surface-2)] flex items-center justify-center"><LogIn className="w-3 h-3 text-[var(--bi-text-3)]" /></div>
                            }
                            <div className="flex-1 min-w-0">
                                <p className="text-xs font-medium text-[var(--bi-text-1)] truncate">{session.user.name}</p>
                                <p className="text-[10px] text-[var(--bi-text-3)] truncate">{session.user.email}</p>
                            </div>
                        </div>
                    )}
                    <div className="flex items-center gap-2">
                        <div className="flex-1">
                            <ThemeToggle />
                        </div>
                        <button
                            onClick={() => signOut()}
                            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium text-[var(--bi-text-3)] hover:text-[var(--bi-red)] hover:bg-[var(--bi-red-dim)] transition-colors"
                            title="Cerrar sesión"
                        >
                            <LogOut className="w-3.5 h-3.5" />
                            <span className="hidden sm:inline">Salir</span>
                        </button>
                    </div>
                </div>
            </aside>
        </>
    );
}
