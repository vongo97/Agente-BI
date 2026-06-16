'use client';

import { useState, useEffect, useCallback } from "react";
import { Brain, Download, PlusCircle, Menu } from "lucide-react";
import { useDashboard } from "@/context/DashboardContext";
import { useToast } from "@/context/ToastContext";
import { 
  createSimulation, 
  getSimulations, 
  getSimulationDetails, 
  getSimulationMessages, 
  exportSimulationPdf, 
  getDataSources, 
  getSimulationSuggestions,
  getSimulationOntology,
  generateSimulationAgents
} from "@/lib/api";
import { Simulation, SimulationMessage, DataSource } from "@/types/shared";

// Sub-componentes refactorizados
import { SimHistory } from "./simulation/SimHistory";
import { SimForm } from "./simulation/SimForm";
import { SimDebate } from "./simulation/SimDebate";
import { SimReport } from "./simulation/SimReport";
import { SimOntologyGraph } from "./simulation/SimOntologyGraph";
import { SimAgentConfig } from "./simulation/SimAgentConfig";


export function SimulationSandbox() {
    const { apiKey, mistralKey, groqKey, aiProvider, setAiProvider, userId, dataSources, setSidebarOpen } = useDashboard();
    const { addToast } = useToast();
    const [title, setTitle] = useState("");
    const [hypothesis, setHypothesis] = useState("");
    const [numRounds, setNumRounds] = useState(3);
    const [loading, setLoading] = useState(false);
    const [simulations, setSimulations] = useState<Simulation[]>([]);
    const [activeSim, setActiveSim] = useState<Simulation | null>(null);
    const [messages, setMessages] = useState<SimulationMessage[]>([]);
    const [polling, setPolling] = useState(false);
    const [selectedSources, setSelectedSources] = useState<Set<number>>(new Set());
    const [allHistoricalSources, setAllHistoricalSources] = useState<DataSource[]>([]);
    const [suggestions, setSuggestions] = useState<{ title: string; hypothesis: string }[]>([]);
    const [loadingSuggestions, setLoadingSuggestions] = useState(false);
    const [downloadingPdf, setDownloadingPdf] = useState(false);

    // Flujo MiroFish: form -> ontology -> agents
    const [sandboxStep, setSandboxStep] = useState<'form' | 'ontology' | 'agents'>('form');
    const [ontologyData, setOntologyData] = useState<{ nodes: any[]; edges: any[] }>({ nodes: [], edges: [] });
    const [loadingOntology, setLoadingOntology] = useState(false);
    const [agentsData, setAgentsData] = useState<any[]>([]);
    const [generatingAgents, setGeneratingAgents] = useState(false);

    const handleDownloadPdf = async () => {
        if (!activeSim?.id) return;
        setDownloadingPdf(true);
        addToast("Iniciando la exportación del veredicto...", "info", 1500);
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
            addToast("Veredicto exportado en PDF con éxito.", "success");
        } catch (err) {
            console.error("Error al descargar PDF de simulación:", err);
            addToast("Error al exportar el veredicto en PDF.", "error");
        } finally {
            setDownloadingPdf(false);
        }
    };

    const fetchSimulations = useCallback(async () => {
        try {
            const data = await getSimulations() as Simulation[];
            setSimulations(data);
        } catch (err) {
            console.error("Error fetching simulations", err);
        }
    }, []);

    const fetchHistoricalSources = useCallback(async () => {
        try {
            const data = await getDataSources(userId);
            setAllHistoricalSources(data);
        } catch (e) {
            console.error("Error fetching historical sources", e);
        }
    }, [userId]);

    useEffect(() => {
        fetchSimulations();
        fetchHistoricalSources();
    }, [userId, fetchSimulations, fetchHistoricalSources]);

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
        if (selectedSources.size === 0 || (!apiKey && !mistralKey && !groqKey)) return;
        setLoadingSuggestions(true);
        try {
            const ids = Array.from(selectedSources);
            let currentApiKey = apiKey;
            if (aiProvider === 'mistral') {
                currentApiKey = mistralKey;
            } else if (aiProvider === 'groq') {
                currentApiKey = groqKey;
            }
            const data = await getSimulationSuggestions(currentUserId, ids, currentApiKey, aiProvider, mistralKey);
            setSuggestions(data);
        } catch (err) {
            console.error("Error fetching suggestions", err);
        } finally {
            setLoadingSuggestions(false);
        }
    };

    const applySuggestion = (sug: { title: string; hypothesis: string }) => {
        setTitle(sug.title);
        setHypothesis(sug.hypothesis);
    };

    useEffect(() => {
        let interval: NodeJS.Timeout;
        if (polling && activeSim?.id) {
            interval = setInterval(async () => {
                const details = await getSimulationDetails(activeSim.id) as Simulation;
                const msgs = await getSimulationMessages(activeSim.id) as SimulationMessage[];
                setMessages(msgs);
                setActiveSim(details);
                if (details.status === 'completed' || details.status === 'error') {
                    setPolling(false);
                    fetchSimulations();
                }
            }, 2000);
        }
        return () => clearInterval(interval);
    }, [polling, activeSim, fetchSimulations]);



    const handleExtractOntology = async () => {
        if (!title || !hypothesis) {
            addToast("Completa el título y la hipótesis de debate.", "warning");
            return;
        }
        if (selectedSources.size === 0) {
            addToast("Selecciona al menos un archivo para fundamentar el debate.", "warning");
            return;
        }

        setSandboxStep('ontology');
        setLoadingOntology(true);
        setOntologyData({ nodes: [], edges: [] });
        try {
            const ids = Array.from(selectedSources);
            const data = await getSimulationOntology(ids, aiProvider === 'groq' ? 'groq' : 'gemini');
            setOntologyData(data);
        } catch (err) {
            console.error("Error al extraer ontología:", err);
            addToast("Error al modelar el Reality Graph de los datos.", "error");
            setSandboxStep('form');
        } finally {
            setLoadingOntology(false);
        }
    };

    const handleGenerateAgents = async () => {
        setGeneratingAgents(true);
        try {
            const ids = Array.from(selectedSources);
            let currentApiKey = apiKey;
            if (aiProvider === 'mistral') {
                currentApiKey = mistralKey;
            } else if (aiProvider === 'groq') {
                currentApiKey = groqKey;
            }
            const data = await generateSimulationAgents(ids, hypothesis, aiProvider, currentApiKey, mistralKey);
            setAgentsData(data);
            setSandboxStep('agents');
        } catch (err) {
            console.error("Error al generar agentes:", err);
            addToast("Error al estructurar el enjambre de agentes consultores.", "error");
        } finally {
            setGeneratingAgents(false);
        }
    };

    const handleStartDebate = async () => {
        const currentUserId = userId || localStorage.getItem("userId") || "invitado@agente-bi.local";
        let currentApiKey = apiKey;
        if (aiProvider === 'mistral') {
            currentApiKey = mistralKey;
        } else if (aiProvider === 'groq') {
            currentApiKey = groqKey;
        }
        
        if (!currentApiKey) {
            addToast("Asegúrate de tener una API Key para el motor seleccionado en Configuración.", "warning");
            return;
        }
        
        setLoading(true);
        addToast("Iniciando debate con enjambre personalizado...", "info", 2000);
        try {
            const ids = Array.from(selectedSources);
            const res = await createSimulation(
                currentUserId, 
                title, 
                hypothesis, 
                undefined, 
                currentApiKey, 
                ids, 
                aiProvider, 
                mistralKey, 
                numRounds,
                agentsData
            );
            const initialDetails = await getSimulationDetails(res.simulation_id) as Simulation;
            setActiveSim(initialDetails);
            setMessages([]);
            setPolling(true);
            
            // Limpiar formulario y resetear paso
            setTitle("");
            setHypothesis("");
            setSandboxStep('form');
            setAgentsData([]);
            setOntologyData({ nodes: [], edges: [] });
            addToast("Debate iniciado con éxito.", "success");
        } catch (err) {
            console.error("Error starting simulation:", err);
            addToast("Error al iniciar el debate de agentes.", "error");
        } finally {
            setLoading(false);
        }
    };


    const loadSim = async (sim: Simulation) => {
        setActiveSim(sim);
        const msgs = await getSimulationMessages(sim.id) as SimulationMessage[];
        setMessages(msgs);
        setPolling(sim.status === 'running');
    };    return (
        <div className="flex h-full bg-[var(--bi-canvas)] overflow-hidden">
            <SimHistory 
                simulations={simulations} 
                activeSim={activeSim} 
                loadSim={loadSim} 
            />

            <div className="flex-1 flex flex-col overflow-hidden">
                <header className="p-4 lg:p-6 border-b border-[var(--bi-border)] bg-[var(--bi-surface-0)]">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3 lg:gap-4">
                            <button
                                onClick={() => setSidebarOpen(true)}
                                className="lg:hidden p-2 rounded-md text-[var(--bi-text-3)] hover:text-[var(--bi-text-1)] hover:bg-[var(--bi-surface-1)] active:bg-[var(--bi-surface-2)] transition-all duration-200 cursor-pointer"
                                aria-label="Abrir menú"
                            >
                                <Menu className="w-5 h-5" />
                            </button>
                            <div className="p-2 bg-[var(--sim-accent-soft)] border border-[var(--sim-border)] rounded-lg hidden sm:block">
                                <Brain className="w-5 h-5 text-[var(--sim-accent)]" />
                            </div>
                            <div>
                                <h1 className="text-sm font-semibold text-[var(--bi-text-1)] uppercase">Ensayos del Futuro</h1>
                                <p className="text-[10px] text-[var(--sim-accent)] font-semibold uppercase tracking-widest">Inteligencia de Enjambre • Mirofish Lite</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-3">
                            <button
                                onClick={() => { setActiveSim(null); setTitle(""); setHypothesis(""); }}
                                className="flex items-center gap-1.5 px-3 py-1.5 bg-[var(--bi-surface-1)] hover:bg-[var(--bi-surface-2)] text-[var(--bi-text-2)] hover:text-[var(--bi-text-1)] rounded-lg text-[10px] font-semibold uppercase tracking-wider border border-[var(--bi-border)] transition-colors cursor-pointer"
                            >
                                <PlusCircle className="w-3.5 h-3.5" /> Nuevo Ensayo
                            </button>

                            {activeSim?.status === 'completed' && (
                                <button 
                                    onClick={handleDownloadPdf}
                                    disabled={downloadingPdf}
                                    className="flex items-center gap-1.5 px-4 py-2 bg-[var(--sim-accent)] hover:bg-[var(--sim-accent-hover)] text-white rounded-lg text-[10px] font-semibold uppercase tracking-wider transition-all disabled:opacity-50 cursor-pointer shadow-lg shadow-[var(--sim-accent-soft)]"
                                >
                                    <Download className="w-3.5 h-3.5" /> 
                                    <span>{downloadingPdf ? "Exportando..." : "Exportar Veredicto"}</span>
                                </button>
                            )}
                        </div>
                    </div>
                </header>

                <div className="flex-1 overflow-y-auto p-6 lg:p-8 space-y-12 custom-scrollbar bg-[var(--bi-canvas)]">
                    {!activeSim ? (
                        sandboxStep === 'form' ? (
                            <SimForm 
                                aiProvider={aiProvider} setAiProvider={setAiProvider}
                                title={title} setTitle={setTitle}
                                hypothesis={hypothesis} setHypothesis={setHypothesis}
                                suggestions={suggestions} fetchSuggestions={fetchSuggestions}
                                loadingSuggestions={loadingSuggestions} applySuggestion={applySuggestion}
                                allHistoricalSources={allHistoricalSources} selectedSources={selectedSources}
                                toggleSource={toggleSource} dataSources={dataSources}
                                handleStart={handleExtractOntology} loading={loading}
                                numRounds={numRounds} setNumRounds={setNumRounds}
                            />
                        ) : sandboxStep === 'ontology' ? (
                            <SimOntologyGraph
                                nodes={ontologyData.nodes}
                                edges={ontologyData.edges}
                                loading={loadingOntology}
                                onNext={() => setSandboxStep('agents')}
                                onGenerateAgents={handleGenerateAgents}
                                generatingAgents={generatingAgents}
                                hasGeneratedAgents={agentsData.length > 0}
                            />
                        ) : (
                            <SimAgentConfig
                                agents={agentsData}
                                onChange={setAgentsData}
                                onBack={() => setSandboxStep('ontology')}
                                onStart={handleStartDebate}
                                loading={loading}
                            />
                        )
                    ) : (
                        <div className="flex flex-col h-full animate-in fade-in duration-500">
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
