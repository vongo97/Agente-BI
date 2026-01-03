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
}

const DashboardContext = createContext<DashboardContextType | undefined>(undefined);

export function DashboardProvider({ children }: { children: React.ReactNode }) {
    const [apiKey, setApiKey] = useState("");
    const [dataSource, setDataSource] = useState<{ filename: string; columns: string[] } | null>(null);
    const [isSidebarOpen, setSidebarOpen] = useState(false);
    const [messages, setMessages] = useState<Message[]>([]);
    const [activeChatId, setActiveChatId] = useState<number | null>(null);
    const [view, setView] = useState<'chat' | 'dashboard'>('chat');

    // Cargar API Key de localStorage si existe
    useEffect(() => {
        const saved = localStorage.getItem("gemini_api_key");
        if (saved) setApiKey(saved);
    }, []);

    useEffect(() => {
        if (apiKey) localStorage.setItem("gemini_api_key", apiKey);
    }, [apiKey]);

    return (
        <DashboardContext.Provider value={{
            apiKey, setApiKey,
            dataSource, setDataSource,
            isSidebarOpen, setSidebarOpen,
            messages, setMessages,
            activeChatId, setActiveChatId,
            view, setView
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
