'use client';

import { useState, useEffect } from "react";
import { Brain, Download, PlusCircle } from "lucide-react";
import { useDashboard } from "@/context/DashboardContext";
import { createSimulation, getSimulations, getSimulationDetails, getSimulationMessages, exportSimulationPdf, getDataSources, getSimulationSuggestions } from "@/lib/api";

// Sub-componentes refactorizados
import { SimHistory } from "./simulation/SimHistory";
import { SimForm } from "./simulation/SimForm";
import { SimDebate } from "./simulation/SimDebate";
import { SimReport } from "./simulation/SimReport";

export function SimulationSandbox() {
    const { apiKey, mistralKey, aiProvider, setAiProvider, userId, dataSources } = useDashboard();
    const [title, setTitle] = useState("");
    const [hypothesis, setHypothesis] = useState("");
    const [loading, setLoading] = useState(false);
    const [simulations, setSimulations] = useState<any[]>([]);
    const [activeSim, setActiveSim] = useState<any>(null);
    const [messages, setMessages] = useState<any[]>([]);
    const [polling, setPolling] = useState(false);
    const [selectedSources, setSelectedSources] = useState<Set<number>>(new Set());
    const [allHistoricalSources, setAllHistoricalSources] = useState<any[]>([]);
    const [suggestions, setSuggestions] = useState<any[]>([]);
    const [loadingSuggestions, setLoadingSuggestions] = useState(false);
    const [downloadingPdf, setDownloadingPdf] = useState(false);

    const handleDownloadPdf = async () => {
        if (!activeSim?.id) return;
        setDownloadingPdf(true);
        try {
            const blob = await exportSimulationPdf(activeSim.id, userId);
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `veredicto_sim_${activeSim.id}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();
        } catch (err) {
            console.error("Error al descargar PDF de simulación:", err);
            alert("Error al descargar el veredicto en PDF de forma segura.");
        } finally {
            setDownloadingPdf(false);
        }
    };

    useEffect(() => {
        fetchSimulations();
        fetchHistoricalSources();
    }, [userId]);

    const fetchHistoricalSources = async () => {
        try {
            const data = await getDataSources(userId);
            setAllHistoricalSources(data);
        } catch (e) {
            console.error("Error fetching historical sources", e);
        }
    };

    useEffect(() => {
        if (dataSources.length > 0) {
            setSelectedSources(new Set(dataSources.map(ds => ds.id).filter((id): id is number => id !== undefined)));
        }
    }, [dataSources]);

    const toggleSource = (id: number) => {
        const next = new Set(selectedSources);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        setSelectedSources(next);
        setSuggestions([]);
    };

    const fetchSuggestions = async () => {
        const currentUserId = userId || localStorage.getItem("userId") || "invitado@agente-bi.local";
        if (selectedSources.size === 0 || (!apiKey && !mistralKey)) return;
        setLoadingSuggestions(true);
        try {
            const ids = Array.from(selectedSources);
            const data = await getSimulationSuggestions(currentUserId, ids, apiKey, aiProvider, mistralKey);
            setSuggestions(data);
        } catch (err) {
            console.error("Error fetching suggestions", err);
        } finally {
            setLoadingSuggestions(false);
        }
    };

    const applySuggestion = (sug: any) => {
        setTitle(sug.title);
        setHypothesis(sug.hypothesis);
    };

    useEffect(() => {
        let interval: any;
        if (polling && activeSim?.id) {
            interval = setInterval(async () => {
                const details = await getSimulationDetails(activeSim.id);
                const msgs = await getSimulationMessages(activeSim.id);
                setMessages(msgs);
                setActiveSim(details);
                if (details.status === 'completed' || details.status === 'error') {
                    setPolling(false);
                    fetchSimulations();
                }
            }, 2000);
        }
        return () => clearInterval(interval);
    }, [polling, activeSim]);

    const fetchSimulations = async () => {
        try {
            const data = await getSimulations(userId);
            setSimulations(data);
        } catch (err) {
            console.error("Error fetching simulations", err);
        }
    };

    const handleStart = async () => {
        const currentUserId = userId || localStorage.getItem("userId") || "invitado@agente-bi.local";
        const currentApiKey = aiProvider === 'mistral' ? mistralKey : apiKey;
        
        if (!currentApiKey && aiProvider !== 'hybrid') {
            alert("Asegúrate de tener una API Key para el motor seleccionado.");
            return;
        }
        if (!title || !hypothesis) {
            alert("Completa el título y la hipótesis.");
            return;
        }
        if (selectedSources.size === 0) {
            alert("Selecciona al menos un archivo.");
            return;
        }
        setLoading(true);
        try {
            const ids = Array.from(selectedSources);
            const res = await createSimulation(
                currentUserId, title, hypothesis, undefined, apiKey, ids as any, aiProvider, mistralKey
            );
            const initialDetails = await getSimulationDetails(res.simulation_id);
            setActiveSim(initialDetails);
            setMessages([]);
            setPolling(true);
            setTitle("");
            setHypothesis("");
        } catch (err) {
            alert("Error al iniciar simulación");
        } finally {
            setLoading(false);
        }
    };

    const loadSim = async (sim: any) => {
        setActiveSim(sim);
        const msgs = await getSimulationMessages(sim.id);
        setMessages(msgs);
        setPolling(sim.status === 'running');
    };

    return (
        <div className="flex h-full bg-[var(--bg-primary)] overflow-hidden">
            <SimHistory 
                simulations={simulations} 
                activeSim={activeSim} 
                loadSim={loadSim} 
            />

            <div className="flex-1 flex flex-col overflow-hidden">
                <header className="p-8 border-b border-[var(--border-color)] bg-gradient-to-r from-purple-900/10 to-transparent">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <div className="p-3 bg-purple-600 rounded-2xl shadow-xl shadow-purple-600/20">
                                <Brain className="w-6 h-6 text-white" />
                            </div>
                            <div>
                                <h1 className="text-2xl font-black text-white tracking-tight italic">Ensayos del Futuro</h1>
                                <p className="text-[10px] text-purple-400 font-black uppercase tracking-widest">Inteligencia de Enjambre • Mirofish Lite</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-3">
                            <button
                                onClick={() => { setActiveSim(null); setTitle(""); setHypothesis(""); }}
                                className="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 text-gray-300 rounded-xl text-[10px] font-black uppercase tracking-widest border border-white/5 transition-all"
                            >
                                <PlusCircle className="w-3.5 h-3.5" /> Nuevo Ensayo
                            </button>

                            {activeSim?.status === 'completed' && (
                                <button 
                                    onClick={handleDownloadPdf}
                                    disabled={downloadingPdf}
                                    className="flex items-center gap-2 px-6 py-2.5 bg-purple-600 hover:bg-purple-500 text-white rounded-xl text-[10px] font-black uppercase tracking-widest shadow-xl shadow-purple-600/20 transition-all disabled:opacity-50 cursor-pointer"
                                >
                                    <Download className="w-3.5 h-3.5" /> 
                                    <span>{downloadingPdf ? "Exportando..." : "Exportar Veredicto"}</span>
                                </button>
                            )}
                        </div>
                    </div>
                </header>

                <div className="flex-1 overflow-y-auto p-8 space-y-12 custom-scrollbar">
                    {!activeSim ? (
                        <SimForm 
                            aiProvider={aiProvider} setAiProvider={setAiProvider}
                            title={title} setTitle={setTitle}
                            hypothesis={hypothesis} setHypothesis={setHypothesis}
                            suggestions={suggestions} fetchSuggestions={fetchSuggestions}
                            loadingSuggestions={loadingSuggestions} applySuggestion={applySuggestion}
                            allHistoricalSources={allHistoricalSources} selectedSources={selectedSources}
                            toggleSource={toggleSource} dataSources={dataSources}
                            handleStart={handleStart} loading={loading}
                        />
                    ) : (
                        <div className="flex flex-col h-full">
                            <div className="grid grid-cols-12 gap-8 h-full">
                                <SimDebate 
                                    messages={messages} 
                                    polling={polling} 
                                    activeSim={activeSim} 
                                />
                                <SimReport 
                                    activeSim={activeSim} 
                                    userId={userId} 
                                    polling={polling} 
                                />
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
