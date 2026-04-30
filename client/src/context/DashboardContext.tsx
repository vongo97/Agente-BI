'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { useSession } from "next-auth/react";

export type Message = {
    id?: number;
    role: 'user' | 'assistant';
    content: string;
    fig?: any;
};

interface DashboardContextType {
    apiKey: string;
    setApiKey: (key: string) => void;
    mistralKey: string;
    setMistralKey: (key: string) => void;
    aiProvider: "gemini" | "mistral" | "hybrid";
    setAiProvider: (provider: "gemini" | "mistral" | "hybrid") => void;
    dataSource: { id?: number; filename: string; columns: string[] } | null;
    setDataSource: (source: { id?: number; filename: string; columns: string[] } | null) => void;
    isSidebarOpen: boolean;
    setSidebarOpen: (open: boolean) => void;
    messages: Message[];
    setMessages: (messages: Message[] | ((prev: Message[]) => Message[])) => void;
    activeChatId: number | null;
    setActiveChatId: (id: number | null) => void;
    view: 'chat' | 'dashboard' | 'settings' | 'simulation';
    setView: (view: 'chat' | 'dashboard' | 'settings' | 'simulation') => void;
    showAiSuggestions: boolean;
    setShowAiSuggestions: (show: boolean) => void;
    isServerHealthy: boolean | null;
    isWakingUp: boolean;
    suggestions: string[];
    setSuggestions: (suggestions: string[]) => void;
    loadingSuggestions: boolean;
    setLoadingSuggestions: (loading: boolean) => void;
    filters: Record<string, string | number | null>;
    setFilters: (filters: Record<string, string | number | null> | ((prev: any) => any)) => void;
}

const DashboardContext = createContext<DashboardContextType | undefined>(undefined);

export function DashboardProvider({ children }: { children: React.ReactNode }) {
    const { data: session } = useSession();
    const [apiKey, setApiKey] = useState("");
    const [mistralKey, setMistralKey] = useState("");
    const [aiProvider, setAiProvider] = useState<"gemini" | "mistral" | "hybrid">("gemini");
    const [dataSource, setDataSource] = useState<{ id?: number; filename: string; columns: string[] } | null>(null);
    const [isSidebarOpen, setSidebarOpen] = useState(false);
    const [messages, setMessages] = useState<Message[]>([]);
    const [activeChatId, setActiveChatId] = useState<number | null>(null);
    const [view, setView] = useState<'chat' | 'dashboard' | 'settings' | 'simulation'>('chat');
    const [showAiSuggestions, setShowAiSuggestions] = useState(true);
    const [isServerHealthy, setIsServerHealthy] = useState<boolean | null>(null);
    const [isWakingUp, setIsWakingUp] = useState(false);
    const [suggestions, setSuggestions] = useState<string[]>([]);
    const [loadingSuggestions, setLoadingSuggestions] = useState(false);
    const [filters, setFilters] = useState<Record<string, string | number | null>>({});

    // Cargar API Keys y preferencias desde el Backend y LocalStorage
    useEffect(() => {
        const fetchConfig = async () => {
            const userEmail = session?.user?.email || "invitado@agente-bi.local";
            try {
                const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
                const res = await fetch(`${API_URL}/user-config?user_id=${userEmail}`);
                if (res.ok) {
                    const data = await res.json();
                    if (data.gemini_key) setApiKey(data.gemini_key);
                    if (data.mistral_key) setMistralKey(data.mistral_key);
                    if (data.preferred_provider) setAiProvider(data.preferred_provider as any);
                }
            } catch (err) {
                console.error("Error cargando config del server:", err);
            }
        };

        fetchConfig();

        // Fallback local
        const savedGemini = localStorage.getItem("gemini_api_key");
        if (savedGemini) setApiKey(savedGemini);
        const savedMistral = localStorage.getItem("mistral_api_key");
        if (savedMistral) setMistralKey(savedMistral);
        const savedProvider = localStorage.getItem("ai_provider") as any;
        if (savedProvider) setAiProvider(savedProvider);
    }, [session]);

    // Guardar en Backend y LocalStorage automáticamente
    const syncConfig = async (key: string, value: string, field: string) => {
        const userEmail = session?.user?.email || "invitado@agente-bi.local";
        localStorage.setItem(key, value);
        
        try {
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const formData = new FormData();
            formData.append("user_id", userEmail);
            formData.append(field, value);
            
            await fetch(`${API_URL}/user-config`, {
                method: "POST",
                body: formData
            });
        } catch (err) {
            console.error(`Error sincronizando ${field}:`, err);
        }
    };

    useEffect(() => {
        if (apiKey) syncConfig("gemini_api_key", apiKey, "gemini_key");
    }, [apiKey]);

    useEffect(() => {
        if (mistralKey) syncConfig("mistral_api_key", mistralKey, "mistral_key");
    }, [mistralKey]);

    useEffect(() => {
        syncConfig("ai_provider", aiProvider, "preferred_provider");
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
            dataSource, setDataSource,
            isSidebarOpen, setSidebarOpen,
            messages, setMessages,
            activeChatId, setActiveChatId,
            view, setView,
            isServerHealthy, isWakingUp,
            suggestions, setSuggestions,
            loadingSuggestions, setLoadingSuggestions,
            filters, setFilters,
            showAiSuggestions, setShowAiSuggestions
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
