import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useSession } from "next-auth/react";
import { setApiAuthToken, getUserConfig, setUserConfig } from "@/lib/api";
import { ChatMessage, DataSource } from '@/types/shared';
import { useToast } from '@/context/ToastContext';

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
    groqKey: string;
    setGroqKey: (key: string) => void;
    aiProvider: "gemini" | "mistral" | "groq";
    setAiProvider: (provider: "gemini" | "mistral" | "groq") => void;
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
    temperature: number;
    setTemperature: (t: number) => void;
    anomalySensitivity: number;
    setAnomalySensitivity: (s: number) => void;
    magicCleanStrategy: string;
    setMagicCleanStrategy: (s: string) => void;
    currencyFormat: string;
    setCurrencyFormat: (s: string) => void;
    dateFormat: string;
    setDateFormat: (s: string) => void;
    brandColor: string;
    setBrandColor: (s: string) => void;
    brandLogoUrl: string;
    setBrandLogoUrl: (s: string) => void;
    reportOrgName: string;
    setReportOrgName: (s: string) => void;
    reportFooterText: string;
    setReportFooterText: (s: string) => void;
    pdfOrientation: string;
    setPdfOrientation: (s: string) => void;
    pdfIncludeDataTable: boolean;
    setPdfIncludeDataTable: (b: boolean) => void;
    chartTheme: string;
    setChartTheme: (s: string) => void;
}

const DashboardContext = createContext<DashboardContextType | undefined>(undefined);

export function DashboardProvider({ children }: { children: React.ReactNode }) {
    const { data: sessionData } = useSession();
    const session = sessionData as ExtendedSession | null;
    const { addToast } = useToast();
    const userId = session?.user?.email || "invitado@agente-bi.local";
    const userName = session?.user?.name || userId;
    const [apiKey, setApiKey] = useState("");
    const [mistralKey, setMistralKey] = useState("");
    const [groqKey, setGroqKey] = useState("");
    const [aiProvider, setAiProvider] = useState<"gemini" | "mistral" | "groq">("gemini");
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

    // Configuraciones Avanzadas
    const [temperature, setTemperature] = useState(0.2);
    const [anomalySensitivity, setAnomalySensitivity] = useState(2.5);
    const [magicCleanStrategy, setMagicCleanStrategy] = useState("remove");
    const [currencyFormat, setCurrencyFormat] = useState("USD");
    const [dateFormat, setDateFormat] = useState("DD/MM/YYYY");
    const [brandColor, setBrandColor] = useState("#2dd4bf");
    const [brandLogoUrl, setBrandLogoUrl] = useState("");
    const [reportOrgName, setReportOrgName] = useState("VEKTRA BI");
    const [reportFooterText, setReportFooterText] = useState("Confidencial - Solo uso interno");
    const [pdfOrientation, setPdfOrientation] = useState("portrait");
    const [pdfIncludeDataTable, setPdfIncludeDataTable] = useState(true);
    const [chartTheme, setChartTheme] = useState("neon");

    const addDataSource = (source: DataSource) => {
        setDataSources(prev => {
            // Evitar duplicados por nombre de archivo
            if (prev.find(s => s.filename === source.filename)) return prev;
            if (prev.length >= 10) {
                addToast("Límite de 10 archivos alcanzado.", "warning");
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
                if (data.groq_key) setGroqKey(data.groq_key);
                if (data.preferred_provider) setAiProvider(data.preferred_provider as "gemini" | "mistral" | "groq");

                // Nuevas configuraciones
                if (data.temperature !== undefined) setTemperature(data.temperature);
                if (data.anomaly_sensitivity !== undefined) setAnomalySensitivity(data.anomaly_sensitivity);
                if (data.magic_clean_strategy) setMagicCleanStrategy(data.magic_clean_strategy);
                if (data.currency_format) setCurrencyFormat(data.currency_format);
                if (data.date_format) setDateFormat(data.date_format);
                if (data.brand_color) setBrandColor(data.brand_color);
                if (data.brand_logo_url) setBrandLogoUrl(data.brand_logo_url);
                if (data.report_org_name) setReportOrgName(data.report_org_name);
                if (data.report_footer_text) setReportFooterText(data.report_footer_text);
                if (data.pdf_orientation) setPdfOrientation(data.pdf_orientation);
                if (data.pdf_include_data_table !== undefined) setPdfIncludeDataTable(data.pdf_include_data_table);
                if (data.chart_theme) setChartTheme(data.chart_theme);

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
                    await setUserConfig(userEmail, syncGemini, syncMistral, undefined, syncProvider, undefined);
                    if (syncGemini) setApiKey(syncGemini);
                    if (syncMistral) setMistralKey(syncMistral);
                    if (syncProvider) setAiProvider(syncProvider as "gemini" | "mistral" | "groq");
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
    const syncConfig = useCallback(async (value: string | number | boolean, field: string) => {
        const userEmail = session?.user?.email || "invitado@agente-bi.local";
        // Si el valor es una máscara o está vacío, no lo sincronizamos
        if (typeof value === 'string' && (!value || value.startsWith("xxxx") || value.includes("..."))) return;
        
        try {
            if (field === "gemini_key") {
                await setUserConfig(userEmail, value as string, undefined, undefined, undefined, undefined);
            } else if (field === "mistral_key") {
                await setUserConfig(userEmail, undefined, value as string, undefined, undefined, undefined);
            } else if (field === "groq_key") {
                await setUserConfig(userEmail, undefined, undefined, undefined, undefined, value as string);
            } else if (field === "preferred_provider") {
                await setUserConfig(userEmail, undefined, undefined, undefined, value as string, undefined);
            } else if (field === "temperature") {
                await setUserConfig(userEmail, undefined, undefined, undefined, undefined, undefined, value as number);
            } else if (field === "anomaly_sensitivity") {
                await setUserConfig(userEmail, undefined, undefined, undefined, undefined, undefined, undefined, value as number);
            } else if (field === "magic_clean_strategy") {
                await setUserConfig(userEmail, undefined, undefined, undefined, undefined, undefined, undefined, undefined, value as string);
            } else if (field === "currency_format") {
                await setUserConfig(userEmail, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, value as string);
            } else if (field === "date_format") {
                await setUserConfig(userEmail, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, value as string);
            } else if (field === "brand_color") {
                await setUserConfig(userEmail, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, value as string);
            } else if (field === "brand_logo_url") {
                await setUserConfig(userEmail, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, value as string);
            } else if (field === "report_org_name") {
                await setUserConfig(userEmail, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, value as string);
            } else if (field === "report_footer_text") {
                await setUserConfig(userEmail, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, value as string);
            } else if (field === "pdf_orientation") {
                await setUserConfig(userEmail, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, value as string);
            } else if (field === "pdf_include_data_table") {
                await setUserConfig(userEmail, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, value as boolean);
            } else if (field === "chart_theme") {
                await setUserConfig(userEmail, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, undefined, value as string);
            }
        } catch (err) {
            console.error(`Error sincronizando ${field}:`, err);
        }
    }, [session]);

    useEffect(() => {
        if (apiKey) syncConfig(apiKey, "gemini_key");
    }, [apiKey, syncConfig]);

    useEffect(() => {
        if (mistralKey) syncConfig(mistralKey, "mistral_key");
    }, [mistralKey, syncConfig]);

    useEffect(() => {
        if (groqKey) syncConfig(groqKey, "groq_key");
    }, [groqKey, syncConfig]);

    useEffect(() => {
        if (aiProvider) syncConfig(aiProvider, "preferred_provider");
    }, [aiProvider, syncConfig]);

    useEffect(() => { syncConfig(temperature, "temperature"); }, [temperature, syncConfig]);
    useEffect(() => { syncConfig(anomalySensitivity, "anomaly_sensitivity"); }, [anomalySensitivity, syncConfig]);
    useEffect(() => { syncConfig(magicCleanStrategy, "magic_clean_strategy"); }, [magicCleanStrategy, syncConfig]);
    useEffect(() => { syncConfig(currencyFormat, "currency_format"); }, [currencyFormat, syncConfig]);
    useEffect(() => { syncConfig(dateFormat, "date_format"); }, [dateFormat, syncConfig]);
    useEffect(() => { syncConfig(brandColor, "brand_color"); }, [brandColor, syncConfig]);
    useEffect(() => { syncConfig(brandLogoUrl, "brand_logo_url"); }, [brandLogoUrl, syncConfig]);
    useEffect(() => { syncConfig(reportOrgName, "report_org_name"); }, [reportOrgName, syncConfig]);
    useEffect(() => { syncConfig(reportFooterText, "report_footer_text"); }, [reportFooterText, syncConfig]);
    useEffect(() => { syncConfig(pdfOrientation, "pdf_orientation"); }, [pdfOrientation, syncConfig]);
    useEffect(() => { syncConfig(pdfIncludeDataTable, "pdf_include_data_table"); }, [pdfIncludeDataTable, syncConfig]);
    useEffect(() => { syncConfig(chartTheme, "chart_theme"); }, [chartTheme, syncConfig]);

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
            groqKey, setGroqKey,
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
            userId, userName,
            temperature, setTemperature,
            anomalySensitivity, setAnomalySensitivity,
            magicCleanStrategy, setMagicCleanStrategy,
            currencyFormat, setCurrencyFormat,
            dateFormat, setDateFormat,
            brandColor, setBrandColor,
            brandLogoUrl, setBrandLogoUrl,
            reportOrgName, setReportOrgName,
            reportFooterText, setReportFooterText,
            pdfOrientation, setPdfOrientation,
            pdfIncludeDataTable, setPdfIncludeDataTable,
            chartTheme, setChartTheme
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
