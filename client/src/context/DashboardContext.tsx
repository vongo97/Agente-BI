import React, { createContext, useContext, useState, useEffect } from 'react';
import { useSession } from "next-auth/react";
import { setApiAuthToken, getUserConfig, setUserConfig } from "@/lib/api";
import { ChatMessage, DataSource } from '@/types/shared';

export type Message = ChatMessage;
export type { DataSource };

interface ExtendedSession {
    user?: {
        name?: string | null;
        email?: string | null;
        image?: string | null;
    };
    accessToken?: string;
}

interface DashboardContextType {
    apiKey: string;
    setApiKey: (key: string) => void;
    mistralKey: string;
    setMistralKey: (key: string) => void;
    aiProvider: "gemini" | "mistral" | "hybrid";
    setAiProvider: (provider: "gemini" | "mistral" | "hybrid") => void;
    dataSources: DataSource[];
    setDataSources: (sources: DataSource[]) => void;
    addDataSource: (source: DataSource) => void;
    removeDataSource: (filename: string) => void;
    isSidebarOpen: boolean;
    setSidebarOpen: (open: boolean) => void;
    messages: Message[];
    setMessages: (messages: Message[] | ((prev: Message[]) => Message[])) => void;
    activeChatId: number | null;
    setActiveChatId: (id: number | null) => void;
    view: 'chat' | 'dashboard' | 'settings' | 'simulation' | 'visual-summary';
    setView: (view: 'chat' | 'dashboard' | 'settings' | 'simulation' | 'visual-summary') => void;
    showAiSuggestions: boolean;
    setShowAiSuggestions: (show: boolean) => void;
    autoSuggestionsEnabled: boolean;
    setAutoSuggestionsEnabled: (enabled: boolean) => void;
    isServerHealthy: boolean | null;
    isWakingUp: boolean;
    suggestions: string[];
    setSuggestions: (suggestions: string[]) => void;
    loadingSuggestions: boolean;
    setLoadingSuggestions: (loading: boolean) => void;
    filters: Record<string, string | number | null>;
    setFilters: React.Dispatch<React.SetStateAction<Record<string, string | number | null>>>;
    userId: string;
    userName: string;
}

const DashboardContext = createContext<DashboardContextType | undefined>(undefined);

export function DashboardProvider({ children }: { children: React.ReactNode }) {
    const { data: sessionData } = useSession();
    const session = sessionData as ExtendedSession | null;
    const userId = session?.user?.email || "invitado@agente-bi.local";
    const userName = session?.user?.name || userId;
    const [apiKey, setApiKey] = useState("");
    const [mistralKey, setMistralKey] = useState("");
    const [aiProvider, setAiProvider] = useState<"gemini" | "mistral" | "hybrid">("gemini");
    const [dataSources, setDataSources] = useState<DataSource[]>([]);
    const [isSidebarOpen, setSidebarOpen] = useState(false);
    const [messages, setMessages] = useState<Message[]>([]);
    const [activeChatId, setActiveChatId] = useState<number | null>(null);
    const [view, setView] = useState<'chat' | 'dashboard' | 'settings' | 'simulation' | 'visual-summary'>('chat');
    const [showAiSuggestions, setShowAiSuggestions] = useState(true);
    const [autoSuggestionsEnabled, setAutoSuggestionsEnabled] = useState(false);
    const [isServerHealthy, setIsServerHealthy] = useState<boolean | null>(null);
    const [isWakingUp, setIsWakingUp] = useState(false);
    const [suggestions, setSuggestions] = useState<string[]>([]);
    const [loadingSuggestions, setLoadingSuggestions] = useState(false);
    const [filters, setFilters] = useState<Record<string, string | number | null>>({});

    const addDataSource = (source: DataSource) => {
        setDataSources(prev => {
            // Evitar duplicados por nombre de archivo
            if (prev.find(s => s.filename === source.filename)) return prev;
            if (prev.length >= 10) {
                alert("Límite de 10 archivos alcanzado.");
                return prev;
            }
            return [...prev, source];
        });
    };

    const removeDataSource = (filename: string) => {
        setDataSources(prev => prev.filter(s => s.filename !== filename));
    };

    // Cargar API Keys y preferencias desde el Backend
    useEffect(() => {
        // Configurar token de autorización en el API wrapper
        if (session && session.accessToken) {
            setApiAuthToken(session.accessToken);
        } else {
            setApiAuthToken(null);
        }

        const fetchConfig = async () => {
            const userEmail = session?.user?.email || "invitado@agente-bi.local";
            try {
                const data = await getUserConfig(userEmail);
                if (data.gemini_key) setApiKey(data.gemini_key);
                if (data.mistral_key) setMistralKey(data.mistral_key);
                if (data.preferred_provider) setAiProvider(data.preferred_provider as "gemini" | "mistral" | "hybrid");

                // Hardening de LocalStorage (Migración única a DB segura)
                const localGemini = localStorage.getItem("gemini_api_key");
                const localMistral = localStorage.getItem("mistral_api_key");
                const localProvider = localStorage.getItem("ai_provider");

                let needsSync = false;
                let syncGemini = undefined;
                let syncMistral = undefined;
                let syncProvider = undefined;

                if (localGemini && !data.gemini_key) {
                    syncGemini = localGemini;
                    needsSync = true;
                }
                if (localMistral && !data.mistral_key) {
                    syncMistral = localMistral;
                    needsSync = true;
                }
                if (localProvider && !data.preferred_provider) {
                    syncProvider = localProvider;
                    needsSync = true;
                }

                if (needsSync) {
                    await setUserConfig(userEmail, syncGemini, syncMistral, undefined, syncProvider);
                    if (syncGemini) setApiKey(syncGemini);
                    if (syncMistral) setMistralKey(syncMistral);
                    if (syncProvider) setAiProvider(syncProvider as "gemini" | "mistral" | "hybrid");
                }

                // Eliminar claves sensibles de LocalStorage
                localStorage.removeItem("gemini_api_key");
                localStorage.removeItem("mistral_api_key");
                localStorage.removeItem("ai_provider");
            } catch (err) {
                console.error("Error cargando config del server:", err);
            }
        };

        if (session) {
            fetchConfig();
        }
    }, [session]);

    // Guardar en Backend automáticamente (Hardening: No guardar en LocalStorage)
    const syncConfig = async (value: string, field: string) => {
        const userEmail = session?.user?.email || "invitado@agente-bi.local";
        // Si el valor es una máscara o está vacío, no lo sincronizamos
        if (!value || value.startsWith("xxxx") || value.includes("...")) return;
        
        try {
            if (field === "gemini_key") {
                await setUserConfig(userEmail, value, undefined, undefined, undefined);
            } else if (field === "mistral_key") {
                await setUserConfig(userEmail, undefined, value, undefined, undefined);
            } else if (field === "preferred_provider") {
                await setUserConfig(userEmail, undefined, undefined, undefined, value);
            }
        } catch (err) {
            console.error(`Error sincronizando ${field}:`, err);
        }
    };

    useEffect(() => {
        if (apiKey) syncConfig(apiKey, "gemini_key");
    }, [apiKey]);

    useEffect(() => {
        if (mistralKey) syncConfig(mistralKey, "mistral_key");
    }, [mistralKey]);

    useEffect(() => {
        if (aiProvider) syncConfig(aiProvider, "preferred_provider");
    }, [aiProvider]);

    // Verificar salud del servidor (Render Wake-up)
    useEffect(() => {
        const checkHealth = async () => {
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            try {
                setIsWakingUp(true);
                const res = await fetch(`${API_URL}/`, { method: "GET" });
                if (res.ok) {
                    setIsServerHealthy(true);
                } else {
                    setIsServerHealthy(false);
                }
            } catch (err) {
                console.warn("Backend is waking up or unreachable:", err);
                setIsServerHealthy(false);
            } finally {
                setIsWakingUp(false);
            }
        };

        checkHealth();
        // Re-verificar cada 30 segundos si falló
        const interval = setInterval(() => {
            if (isServerHealthy !== true) checkHealth();
        }, 30000);

        return () => clearInterval(interval);
    }, [isServerHealthy]);

    return (
        <DashboardContext.Provider value={{
            apiKey, setApiKey,
            mistralKey, setMistralKey,
            aiProvider, setAiProvider,
            dataSources, setDataSources,
            addDataSource, removeDataSource,
            isSidebarOpen, setSidebarOpen,
            messages, setMessages,
            activeChatId, setActiveChatId,
            view, setView,
            isServerHealthy, isWakingUp,
            suggestions, setSuggestions,
            loadingSuggestions, setLoadingSuggestions,
            filters, setFilters,
            showAiSuggestions, setShowAiSuggestions,
            autoSuggestionsEnabled, setAutoSuggestionsEnabled,
            userId, userName
        }}>
            {children}
        </DashboardContext.Provider>
    );
}

export function useDashboard() {
    const context = useContext(DashboardContext);
    if (context === undefined) {
        throw new Error('useDashboard must be used within a DashboardProvider');
    }
    return context;
}
