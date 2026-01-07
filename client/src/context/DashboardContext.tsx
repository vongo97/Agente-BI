'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';

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
    dataSource: { filename: string; columns: string[] } | null;
    setDataSource: (source: { filename: string; columns: string[] } | null) => void;
    isSidebarOpen: boolean;
    setSidebarOpen: (open: boolean) => void;
    messages: Message[];
    setMessages: (messages: Message[] | ((prev: Message[]) => Message[])) => void;
    activeChatId: number | null;
    setActiveChatId: (id: number | null) => void;
    view: 'chat' | 'dashboard';
    setView: (view: 'chat' | 'dashboard') => void;
    isServerHealthy: boolean | null;
    isWakingUp: boolean;
    suggestions: string[];
    setSuggestions: (suggestions: string[]) => void;
    loadingSuggestions: boolean;
    setLoadingSuggestions: (loading: boolean) => void;
}

const DashboardContext = createContext<DashboardContextType | undefined>(undefined);

export function DashboardProvider({ children }: { children: React.ReactNode }) {
    const [apiKey, setApiKey] = useState("");
    const [mistralKey, setMistralKey] = useState("");
    const [aiProvider, setAiProvider] = useState<"gemini" | "mistral" | "hybrid">("gemini");
    const [dataSource, setDataSource] = useState<{ filename: string; columns: string[] } | null>(null);
    const [isSidebarOpen, setSidebarOpen] = useState(false);
    const [messages, setMessages] = useState<Message[]>([]);
    const [activeChatId, setActiveChatId] = useState<number | null>(null);
    const [view, setView] = useState<'chat' | 'dashboard'>('chat');
    const [isServerHealthy, setIsServerHealthy] = useState<boolean | null>(null);
    const [isWakingUp, setIsWakingUp] = useState(false);
    const [suggestions, setSuggestions] = useState<string[]>([]);
    const [loadingSuggestions, setLoadingSuggestions] = useState(false);

    // Cargar API Keys y preferencias
    useEffect(() => {
        const savedGemini = localStorage.getItem("gemini_api_key");
        if (savedGemini) setApiKey(savedGemini);

        const savedMistral = localStorage.getItem("mistral_api_key");
        if (savedMistral) setMistralKey(savedMistral);

        const savedProvider = localStorage.getItem("ai_provider") as "gemini" | "mistral" | "hybrid";
        if (savedProvider) setAiProvider(savedProvider);
    }, []);

    useEffect(() => {
        if (apiKey) localStorage.setItem("gemini_api_key", apiKey);
    }, [apiKey]);

    useEffect(() => {
        if (mistralKey) localStorage.setItem("mistral_api_key", mistralKey);
    }, [mistralKey]);

    useEffect(() => {
        localStorage.setItem("ai_provider", aiProvider);
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
            loadingSuggestions, setLoadingSuggestions
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
