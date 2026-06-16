import React, { useState } from "react";
import { useForceLayout } from "@/hooks/useForceLayout";
import { Loader2, User, Layers, Brain, CheckCircle, Clock, ChevronRight, Activity, MessageSquare } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { Simulation, SimulationMessage } from "@/types/shared";

interface SimDebateProps {
    messages: SimulationMessage[];
    polling: boolean;
    activeSim: Simulation | null;
}

export function SimDebate({ messages, polling, activeSim }: SimDebateProps) {
    const [viewMode, setViewMode] = useState<'brain' | 'feed'>('brain');
    const [selectedAgentName, setSelectedAgentName] = useState<string | null>(null);

    // Obtener iniciales del nombre de agente
    const getInitials = (name?: string) => {
        if (!name || name === "Sistema") return "SY";
        if (name === "Asistente") return "AS";
        const parts = name.split(" ");
        if (parts.length >= 2) {
            return (parts[0][0] + parts[1][0]).toUpperCase();
        }
        return name.slice(0, 2).toUpperCase();
    };

    // Color determinista para el avatar del agente
    const getAvatarColor = (name?: string) => {
        if (!name || name === "Sistema" || name === "Asistente") {
            return "bg-[var(--bi-surface-2)] text-[var(--bi-text-2)] border-[var(--bi-border)]";
        }
        const colors = [
            "bg-blue-500/10 text-blue-400 border-blue-500/20",
            "bg-teal-500/10 text-teal-400 border-teal-500/20",
            "bg-purple-500/10 text-purple-400 border-purple-500/20",
            "bg-pink-500/10 text-pink-400 border-pink-500/20",
            "bg-indigo-500/10 text-indigo-400 border-indigo-500/20",
            "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
            "bg-amber-500/10 text-amber-400 border-amber-500/20"
        ];
        let hash = 0;
        for (let i = 0; i < name.length; i++) {
            hash = name.charCodeAt(i) + ((hash << 5) - hash);
        }
        const index = Math.abs(hash) % colors.length;
        return colors[index];
    };

    // Extraer la lista de agentes únicos que participan en este debate
    const agentsList = React.useMemo(() => {
        return messages.reduce((acc, m) => {
            if (m.agent_name && m.agent_name !== "Sistema" && m.agent_name !== "Asistente" && !acc.some(a => a.name === m.agent_name)) {
                acc.push({
                    name: m.agent_name,
                    role: m.agent_role || "Analista",
                    description: m.agent_description || "Analista de Negocios",
                    personality: m.agent_personality || "Profesional"
                });
            }
            return acc;
        }, [] as { name: string; role: string; description: string; personality: string }[]);
    }, [messages]);

    // Filtrar los mensajes reales del debate
    const filteredMessages = React.useMemo(() => {
        return messages.filter(
            m => m.content && !m.content.includes("Límite de cuota") && !m.content.includes("Error Gemini")
        );
    }, [messages]);

    // Calcular el agente que hablará en el turno actual
    const currentSpeaker = React.useMemo(() => {
        const debateMessagesCount = filteredMessages.filter(m => m.agent_name !== "Sistema" && m.agent_name !== "Asistente").length;
        return agentsList.length > 0
            ? agentsList[debateMessagesCount % agentsList.length]
            : null;
    }, [agentsList, filteredMessages]);

    // --- CÁLCULO DE COORDENADAS CON FÍSICAS DE FUERZAS EN TIEMPO REAL ---
    const width = 800;
    const height = 450;
    const cx = width / 2;
    const cy = height / 2;
    const r = 150;

    // Detectar interacciones y réplicas entre analistas
    const semanticConnections = React.useMemo(() => {
        const list: { source: string; target: string; isFlowing: boolean }[] = [];
        
        filteredMessages.forEach((m, msgIdx) => {
            const sender = m.agent_name;
            const content = (m.content || "").toLowerCase();
            if (!sender) return;
            
            agentsList.forEach(other => {
                if (other.name !== sender) {
                    const nameParts = other.name.split(" ").filter(p => p.length > 2);
                    let mentioned = false;
                    for (const part of nameParts) {
                        if (content.includes(part.toLowerCase())) {
                            mentioned = true;
                            break;
                        }
                    }
                    if (mentioned) {
                        const isFlowing = polling && msgIdx === filteredMessages.length - 1;
                        list.push({
                            source: sender,
                            target: other.name,
                            isFlowing
                        });
                    }
                }
            });
        });

        // Conexiones en anillo por defecto para que no queden desconectados en la visualización
        if (list.length === 0 && agentsList.length > 1) {
            for (let i = 0; i < agentsList.length; i++) {
                list.push({
                    source: agentsList[i].name,
                    target: agentsList[(i + 1) % agentsList.length].name,
                    isFlowing: polling
                });
            }
        }

        // Eliminar duplicados
        return list.filter((v, i, self) => 
            self.findIndex(t => t.source === v.source && t.target === v.target) === i
        );
    }, [filteredMessages, agentsList, polling]);

    const initialForceNodes = React.useMemo(() => {
        return agentsList.map(a => ({ id: a.name, label: a.name, type: 'agent' }));
    }, [agentsList]);

    const initialForceLinks = React.useMemo(() => {
        return semanticConnections.map(c => ({ source: c.source, target: c.target }));
    }, [semanticConnections]);

    const {
        nodes: forceNodes,
        dragStart,
        dragUpdate,
        dragEnd
    } = useForceLayout(initialForceNodes, initialForceLinks, {
        width,
        height,
        repulsion: 4500, // Incrementado proporcionalmente para separar más a los agentes en el lienzo más grande
        attraction: 0.045,
        gravity: 0.012, // Suave atracción al centro
        restLength: 170 // Mayor distancia de reposo
    });

    const handleNodeMouseDown = (e: React.MouseEvent<SVGElement>, nodeId: string) => {
        e.stopPropagation();
        setSelectedAgentName(nodeId);
        dragStart(nodeId);
    };

    const handleSvgMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
        const rect = e.currentTarget.getBoundingClientRect();
        // Convertir posición local del ratón con escala a la caja de coordenadas SVG (800x450)
        const localX = ((e.clientX - rect.left) / rect.width) * width;
        const localY = ((e.clientY - rect.top) / rect.height) * height;
        dragUpdate(localX, localY);
    };

    // Dibujar curva Bézier cuadrática
    const drawCurve = (x1: number, y1: number, x2: number, y2: number) => {
        const dx = x2 - x1;
        const dy = y2 - y1;
        const mx = (x1 + x2) / 2;
        const my = (y1 + y2) / 2;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist === 0) return "";
        const offset = 22; // Mayor curvatura para un flujo más elegante
        const px = mx - (dy / dist) * offset;
        const py = my + (dx / dist) * offset;
        return `M ${x1} ${y1} Q ${px} ${py} ${x2} ${y2}`;
    };

    // Cálculo dinámico para posicionar etiquetas radialmente hacia afuera y evitar colisiones
    const getLabelCoords = (x: number, y: number) => {
        const dx = x - cx;
        const dy = y - cy;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist === 0) return { x, y: y + 36, vx: 0, vy: 1 };
        const vx = dx / dist;
        const vy = dy / dist;
        const offsetDist = 38; // Distancia radial de separación del círculo del nodo
        return {
            x: x + vx * offsetDist,
            y: y + vy * offsetDist,
            vx,
            vy
        };
    };

    // Selección de analista activo para el panel inferior
    const activeAgentForDisplay = React.useMemo(() => {
        if (selectedAgentName) {
            return agentsList.find(a => a.name === selectedAgentName) || null;
        }
        return currentSpeaker || (agentsList.length > 0 ? agentsList[0] : null);
    }, [selectedAgentName, currentSpeaker, agentsList]);

    const lastMessageForActiveAgent = React.useMemo(() => {
        if (!activeAgentForDisplay) return null;
        const agentMsgs = filteredMessages.filter(m => m.agent_name === activeAgentForDisplay.name);
        return agentMsgs.length > 0 ? agentMsgs[agentMsgs.length - 1] : null;
    }, [activeAgentForDisplay, filteredMessages]);

    return (
        <div className="col-span-12 lg:col-span-7 space-y-6 pb-20">
            {/* Cabecera con Selector de Modo de Vista */}
            <div className="flex items-center justify-between px-2">
                <div className="flex items-center gap-4">
                    <h3 className="text-[10px] font-bold text-[var(--bi-text-3)] uppercase tracking-widest flex-shrink-0">Interacción del Enjambre</h3>
                    {agentsList.length > 0 && (
                        <div className="flex bg-[var(--bi-surface-1)] border border-[var(--bi-border)] rounded-lg p-0.5 text-[8px] font-bold uppercase tracking-wider">
                            <button
                                type="button"
                                onClick={() => setViewMode('brain')}
                                className={`flex items-center gap-1 px-2.5 py-1 rounded-md transition-all duration-200 cursor-pointer ${
                                    viewMode === 'brain' 
                                    ? 'bg-[var(--module-simulation-accent)] text-white shadow-md shadow-[rgba(168,85,247,0.15)]' 
                                    : 'text-[var(--bi-text-3)] hover:text-[var(--bi-text-1)]'
                                }`}
                            >
                                <Activity className="w-3 h-3" />
                                <span>Cerebro Enjambre</span>
                            </button>
                            <button
                                type="button"
                                onClick={() => setViewMode('feed')}
                                className={`flex items-center gap-1 px-2.5 py-1 rounded-md transition-all duration-200 cursor-pointer ${
                                    viewMode === 'feed' 
                                    ? 'bg-[var(--module-simulation-accent)] text-white shadow-md shadow-[rgba(168,85,247,0.15)]' 
                                    : 'text-[var(--bi-text-3)] hover:text-[var(--bi-text-1)]'
                                }`}
                            >
                                <MessageSquare className="w-3 h-3" />
                                <span>Feed de Chat</span>
                            </button>
                        </div>
                    )}
                </div>
                <div className="flex items-center gap-2">
                    <span className={`w-2.5 h-2.5 rounded-full ${polling ? 'bg-[var(--module-simulation-accent)] animate-pulse' : 'bg-[var(--bi-green)]'}`}></span>
                    <span className={`text-[9px] font-bold uppercase tracking-widest ${polling ? 'text-[var(--module-simulation-accent)]' : 'text-[var(--bi-green)]'}`}>
                        {polling ? 'Debate en Curso' : 'Simulación Completada'}
                    </span>
                </div>
            </div>

            {/* Stepper Refinado */}
            {activeSim && (
                <div className="bg-[var(--bi-surface-0)] border border-[var(--bi-border)] rounded-xl p-5 shadow-lg">
                    <div className="grid grid-cols-4 gap-2">
                        {[
                            { title: "Preparación", desc: "Datos & Contexto", stepNum: 1 },
                            { title: "Debate Swarm", desc: `Ronda ${activeSim.current_round}`, stepNum: 2 },
                            { title: "Síntesis", desc: "Generando veredicto", stepNum: 3 },
                            { title: "Consolidado", desc: "Reporte listo", stepNum: 4 }
                        ].map((step, sIdx) => {
                            const status = activeSim.status;
                            let isCompleted = false;
                            let isActive = false;
 
                            if (sIdx === 0) {
                                isCompleted = status !== 'pending';
                                isActive = status === 'pending';
                            } else if (sIdx === 1) {
                                isCompleted = status === 'completed' || (status === 'running' && activeSim.result_report !== null);
                                isActive = status === 'running' && activeSim.result_report === null;
                            } else if (sIdx === 2) {
                                isCompleted = status === 'completed';
                                isActive = status === 'running' && activeSim.result_report !== null;
                            } else if (sIdx === 3) {
                                isCompleted = status === 'completed';
                                isActive = false;
                            }

                            return (
                                <div key={sIdx} className="flex flex-col items-center text-center relative group">
                                    <div className={`w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold border transition-all duration-300 z-10 ${
                                        isCompleted
                                            ? "bg-[var(--bi-green-dim)] border-[var(--bi-green)] text-[var(--bi-green)]"
                                            : isActive
                                                ? "bg-[var(--module-simulation-accent-soft)] border-[var(--module-simulation-accent)] text-[var(--module-simulation-accent)] animate-pulse shadow-[0_0_12px_rgba(168,85,247,0.25)]"
                                                : "bg-[var(--bi-surface-1)] border-[var(--bi-border)] text-[var(--bi-text-3)]"
                                    }`}>
                                        {isCompleted ? "✓" : step.stepNum}
                                    </div>

                                    <span className={`text-[9px] font-bold mt-2.5 uppercase tracking-wider transition-colors duration-200 ${
                                        isActive ? "text-[var(--module-simulation-accent)]" : isCompleted ? "text-[var(--bi-text-2)]" : "text-[var(--bi-text-3)]"
                                    }`}>
                                        {step.title}
                                    </span>
                                    <span className="text-[8px] text-[var(--bi-text-3)] font-semibold mt-0.5 max-w-[90px] truncate leading-tight uppercase tracking-tight">
                                        {step.desc}
                                    </span>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* CONTENIDO INTERACTIVO SEGÚN MODO DE VISTA */}
            {viewMode === 'brain' && agentsList.length > 0 ? (
                <div className="space-y-6">
                    {/* LIENZO DE CEREBRO NEURONAL (GRAFO INTERACTIVO) */}
                    <div className="bg-[var(--bi-canvas)] border border-[var(--bi-border)] rounded-xl p-4 shadow-xl overflow-hidden relative group">
                        <svg 
                            viewBox={`0 0 ${width} ${height}`} 
                            className="w-full h-auto select-none bg-[radial-gradient(circle_at_center,rgba(20,15,30,0.6)_0%,rgba(10,10,12,0.95)_100%)]"
                            onMouseMove={handleSvgMouseMove}
                            onMouseLeave={dragEnd}
                            onMouseUp={dragEnd}
                        >
                             <style>{`
                                 @keyframes dash-flow {
                                     to {
                                         stroke-dashoffset: -30;
                                     }
                                 }
                                 .flowing-edge {
                                     animation: dash-flow 1s linear infinite;
                                 }
                                 @keyframes pulse-ring {
                                     0% {
                                         transform: scale(0.65);
                                         opacity: 0;
                                     }
                                     50% {
                                         opacity: 0.45;
                                     }
                                     100% {
                                         transform: scale(1.45);
                                         opacity: 0;
                                     }
                                 }
                                 .active-ring {
                                     animation: pulse-ring 2.5s cubic-bezier(0.25, 0.46, 0.45, 0.94) infinite;
                                 }
                                 @keyframes radar-rotate {
                                     from { transform: rotate(0deg); }
                                     to { transform: rotate(360deg); }
                                 }
                                 .radar-line {
                                     animation: radar-rotate 14s linear infinite;
                                     transform-origin: 400px 225px;
                                 }
                                 @keyframes rotate-slow {
                                     from { transform: rotate(0deg); }
                                     to { transform: rotate(360deg); }
                                 }
                                 .rotating-core {
                                     animation: rotate-slow 35s linear infinite;
                                     transform-origin: 0px 0px;
                                 }
                                 @keyframes rotate-reverse {
                                     from { transform: rotate(360deg); }
                                     to { transform: rotate(0deg); }
                                 }
                                 .rotating-orbit {
                                     animation: rotate-reverse 45s linear infinite;
                                     transform-origin: 0px 0px;
                                 }
                                 @keyframes bubble-float {
                                     0%, 100% { transform: translateY(0px) scale(1); }
                                     50% { transform: translateY(-4px) scale(1.02); }
                                 }
                                 .floating-core {
                                     animation: bubble-float 6s ease-in-out infinite;
                                 }
                             `}</style>

                             <defs>
                                 <pattern id="tactical-grid" width="30" height="30" patternUnits="userSpaceOnUse">
                                     <path d="M 30 0 L 0 0 0 30" fill="none" stroke="rgba(147, 51, 234, 0.07)" strokeWidth="0.8" />
                                     <circle cx="0" cy="0" r="1.2" fill="rgba(168, 85, 247, 0.18)" />
                                 </pattern>
                                 
                                 <filter id="neon-glow" x="-20%" y="-20%" width="140%" height="140%">
                                     <feGaussianBlur stdDeviation="4.5" result="blur" />
                                     <feMerge>
                                         <feMergeNode in="blur" />
                                         <feMergeNode in="SourceGraphic" />
                                     </feMerge>
                                 </filter>

                                 <filter id="liquid-plasma" x="-20%" y="-20%" width="140%" height="140%">
                                     <feTurbulence type="fractalNoise" baseFrequency="0.045 0.045" numOctaves="2" result="noise">
                                         <animate attributeName="baseFrequency" values="0.04 0.04;0.055 0.065;0.04 0.04" dur="12s" repeatCount="indefinite" />
                                     </feTurbulence>
                                     <feDisplacementMap in="SourceGraphic" in2="noise" scale="6" xChannelSelector="R" yChannelSelector="G" />
                                 </filter>

                                 <radialGradient id="plasma-core" cx="35%" cy="35%" r="65%">
                                     <stop offset="0%" stopColor="#d8b4fe" />
                                     <stop offset="40%" stopColor="#a855f7" />
                                     <stop offset="85%" stopColor="#6b21a8" />
                                     <stop offset="100%" stopColor="#250244" />
                                 </radialGradient>

                                 <radialGradient id="cyber-node-grad" cx="35%" cy="35%" r="65%">
                                     <stop offset="0%" stopColor="#d8b4fe" stopOpacity="0.9" />
                                     <stop offset="25%" stopColor="#8b5cf6" stopOpacity="0.95" />
                                     <stop offset="65%" stopColor="#4c1d95" />
                                     <stop offset="100%" stopColor="#0f051d" />
                                 </radialGradient>

                                 <radialGradient id="glass-specular" cx="30%" cy="30%" r="40%">
                                     <stop offset="0%" stopColor="rgba(255, 255, 255, 0.4)" />
                                     <stop offset="50%" stopColor="rgba(255, 255, 255, 0.05)" />
                                     <stop offset="100%" stopColor="rgba(255, 255, 255, 0)" stopOpacity="0" />
                                 </radialGradient>

                                 <marker id="arrow-static" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
                                     <path d="M 0 1 L 9 5 L 0 9 z" fill="rgba(168, 85, 247, 0.3)" />
                                 </marker>
                                 <marker id="arrow-active" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="5.5" markerHeight="5.5" orient="auto-start-reverse">
                                     <path d="M 0 1 L 9 5 L 0 9 z" fill="var(--module-simulation-accent)" />
                                 </marker>
                             </defs>

                             <rect width={width} height={height} fill="url(#tactical-grid)" />

                             <circle cx={cx} cy={cy} r={r * 1.25} fill="none" stroke="rgba(147, 51, 234, 0.06)" strokeWidth="1" />
                             <line 
                                 x1={cx} 
                                 y1={cy} 
                                 x2={cx + r * 1.25} 
                                 y2={cy} 
                                 stroke="rgba(168, 85, 247, 0.12)" 
                                 strokeWidth="2.5" 
                                 strokeLinecap="round"
                                 className="radar-line" 
                             />
                             
                             <circle cx={cx} cy={cy} r={r} fill="none" stroke="rgba(168, 85, 247, 0.07)" strokeWidth="1.2" strokeDasharray="6 15" className="rotating-orbit" />

                             {forceNodes.map((agent, i) => (
                                 <line
                                     key={`center-line-${i}`}
                                     x1={agent.x}
                                     y1={agent.y}
                                     x2={cx}
                                     y2={cy}
                                     stroke="rgba(168, 85, 247, 0.12)"
                                     strokeWidth="1.2"
                                     strokeDasharray="3 5"
                                 />
                             ))}

                             {semanticConnections.map((conn, i) => {
                                 const sourceNode = forceNodes.find(n => n.id === conn.source);
                                 const targetNode = forceNodes.find(n => n.id === conn.target);
                                 if (!sourceNode || !targetNode) return null;

                                 return (
                                     <g key={`edge-${i}`}>
                                         <path
                                             d={drawCurve(sourceNode.x, sourceNode.y, targetNode.x, targetNode.y)}
                                             fill="none"
                                             stroke={conn.isFlowing ? "var(--module-simulation-accent)" : "rgba(147, 51, 234, 0.18)"}
                                             strokeWidth={conn.isFlowing ? "1.8" : "1.0"}
                                             markerEnd={conn.isFlowing ? "url(#arrow-active)" : "url(#arrow-static)"}
                                             opacity={conn.isFlowing ? "0.95" : "0.6"}
                                         />
                                         {conn.isFlowing && (
                                             <path
                                                 d={drawCurve(sourceNode.x, sourceNode.y, targetNode.x, targetNode.y)}
                                                 fill="none"
                                                 stroke="var(--module-simulation-accent)"
                                                 strokeWidth="2.5"
                                                 strokeDasharray="6 24"
                                                 className="flowing-edge"
                                                 filter="url(#neon-glow)"
                                             />
                                         )}
                                     </g>
                                 );
                             })}

                             <g transform={`translate(${cx}, ${cy})`}>
                                 <g className="floating-core" style={{ transformOrigin: '0px 0px' }}>
                                     {polling && (
                                         <>
                                             <circle cx="0" cy="0" r="46" fill="none" stroke="rgba(168, 85, 247, 0.22)" strokeWidth="1" className="active-ring" style={{ animationDelay: '0s', transformOrigin: '0px 0px' }} />
                                             <circle cx="0" cy="0" r="46" fill="none" stroke="rgba(168, 85, 247, 0.12)" strokeWidth="1.2" className="active-ring" style={{ animationDelay: '1.2s', transformOrigin: '0px 0px' }} />
                                         </>
                                     )}
                                     
                                     <circle 
                                         cx="0" 
                                         cy="0" 
                                         r="32" 
                                         fill="url(#plasma-core)" 
                                         filter="url(#liquid-plasma)"
                                         className="rotating-core" 
                                         style={{ transformOrigin: '0px 0px' }}
                                     />
                                     
                                     <circle cx="0" cy="0" r="34" fill="none" stroke="rgba(216, 180, 254, 0.3)" strokeWidth="0.8" strokeDasharray="4 2" />
                                     
                                     <g transform="translate(-14, -14)">
                                         <Brain width={28} height={28} className="text-purple-100" style={{ filter: 'drop-shadow(0 0 4px rgba(255,255,255,0.7))' }} />
                                     </g>
                                 </g>
                             </g>

                             {forceNodes.map((node, i) => {
                                 const agent = agentsList.find(a => a.name === node.id);
                                 if (!agent) return null;
                                 const isSelected = activeAgentForDisplay?.name === node.id;
                                 const isSpeaking = currentSpeaker?.name === node.id && polling;
                                 const nodeR = isSelected ? 26 : 22;

                                 return (
                                     <g 
                                         key={`node-${i}`} 
                                         onMouseDown={(e) => handleNodeMouseDown(e, node.id)}
                                         className="cursor-pointer"
                                     >
                                         {isSpeaking && (
                                             <>
                                                 <circle cx={node.x} cy={node.y} r={nodeR + 10} fill="none" stroke="rgba(168, 85, 247, 0.25)" strokeWidth="1.2" className="active-ring" style={{ animationDelay: '0s', transformOrigin: `${node.x}px ${node.y}px` }} />
                                                 <circle cx={node.x} cy={node.y} r={nodeR + 10} fill="none" stroke="rgba(168, 85, 247, 0.12)" strokeWidth="1.0" className="active-ring" style={{ animationDelay: '1.0s', transformOrigin: `${node.x}px ${node.y}px` }} />
                                             </>
                                         )}

                                         <circle
                                             cx={node.x}
                                             cy={node.y}
                                             r={nodeR}
                                             fill="none"
                                             stroke={isSelected || isSpeaking ? "var(--module-simulation-accent)" : "transparent"}
                                             strokeWidth="3.5"
                                             opacity="0.25"
                                             filter="url(#neon-glow)"
                                         />

                                         <circle
                                             cx={node.x}
                                             cy={node.y}
                                             r={nodeR}
                                             fill="url(#cyber-node-grad)"
                                             stroke={isSelected ? "var(--module-simulation-accent)" : isSpeaking ? "var(--module-simulation-accent)" : "rgba(168,85,247,0.35)"}
                                             strokeWidth={isSelected ? "2.0" : isSpeaking ? "1.8" : "1.0"}
                                             className="transition-all duration-300 hover:scale-105"
                                         />

                                         <circle
                                             cx={node.x}
                                             cy={node.y}
                                             r={nodeR}
                                             fill="url(#glass-specular)"
                                             pointerEvents="none"
                                         />

                                         <text
                                             x={node.x}
                                             y={node.y + 4.0}
                                             textAnchor="middle"
                                             className="text-[11px] font-bold select-none tracking-tighter fill-white"
                                             style={{ filter: 'drop-shadow(0 0 2px rgba(0,0,0,0.85))' }}
                                         >
                                             {getInitials(node.id)}
                                         </text>
                                     </g>
                                 );
                             })}

                             {forceNodes.map((node, i) => {
                                 const isSelected = activeAgentForDisplay?.name === node.id;
                                 const labelCoord = getLabelCoords(node.x, node.y);
                                 
                                 const badgeW = 105;
                                 const badgeH = 19;
                                 const rx = -badgeW / 2 + (labelCoord.vx * badgeW / 2);
                                 const ry = -badgeH / 2 + (labelCoord.vy * badgeH / 2);
                                 const textX = labelCoord.vx * badgeW / 2;
                                 const textY = labelCoord.vy * badgeH / 2 + 3.5;

                                 return (
                                     <g 
                                         key={`label-${i}`} 
                                         transform={`translate(${labelCoord.x}, ${labelCoord.y})`}
                                         className="pointer-events-none"
                                     >
                                         <rect
                                             x={rx}
                                             y={ry}
                                             width={badgeW}
                                             height={badgeH}
                                             rx="9.5"
                                             fill="rgba(10, 8, 16, 0.82)"
                                             stroke={isSelected ? "var(--module-simulation-accent)" : "rgba(168, 85, 247, 0.25)"}
                                             strokeWidth="1.0"
                                             style={{ backdropFilter: 'blur(3px)' }}
                                         />
                                         <text
                                             x={textX}
                                             y={textY}
                                             textAnchor="middle"
                                             className={`text-[8.5px] font-bold select-none ${
                                                 isSelected ? "fill-[var(--module-simulation-accent)]" : "fill-[var(--bi-text-1)]"
                                             }`}
                                         >
                                             {node.id.length > 18 ? `${node.id.substring(0, 15)}...` : node.id}
                                         </text>
                                     </g>
                                 );
                             })}
                        </svg>

                        <div className="absolute bottom-2.5 left-2.5 right-2.5 flex items-center justify-between">
                            <span className="text-[7px] font-bold text-[var(--bi-text-3)] uppercase tracking-wider">Haz clic en los nodos para inspeccionar analistas</span>
                            {polling && currentSpeaker && (
                                <span className="text-[7.5px] font-bold text-[var(--module-simulation-accent)] uppercase tracking-wider animate-pulse flex items-center gap-1">
                                    <Activity className="w-2.5 h-2.5" /> Turno: {currentSpeaker.name}
                                </span>
                            )}
                        </div>
                    </div>

                    {/* PANEL DE LECTURA INTERACTIVO INFERIOR */}
                    {activeAgentForDisplay && (
                        <div className="animate-in fade-in duration-300 relative">
                            {/* Efecto 3D Drop Shadow */}
                            <div className="absolute inset-0 bg-[rgba(20,15,30,0.4)] rounded-xl translate-x-[2px] translate-y-[2px] -z-10 border border-transparent"></div>
                            
                            <div className="bg-[var(--bi-surface-0)] border border-[var(--module-simulation-border)]/40 rounded-xl p-5 lg:p-6 space-y-4">
                                <div className="flex items-start justify-between gap-3">
                                    <div className="flex items-center gap-3">
                                        <div className={`w-9 h-9 rounded-full flex items-center justify-center font-bold text-xs uppercase border flex-shrink-0 ${getAvatarColor(activeAgentForDisplay.name)}`}>
                                            {getInitials(activeAgentForDisplay.name)}
                                        </div>
                                        <div>
                                            <div className="flex items-center gap-2">
                                                <h4 className="text-xs font-bold text-[var(--bi-text-1)]">{activeAgentForDisplay.name}</h4>
                                                <span className="text-[7.5px] font-bold bg-[var(--bi-surface-1)] border border-[var(--bi-border)] px-1.5 py-0.2 rounded text-[var(--bi-text-2)] uppercase">{activeAgentForDisplay.role}</span>
                                            </div>
                                            <div className="text-[7.5px] font-bold text-[var(--module-simulation-accent)] uppercase tracking-wider mt-0.5">Enfoque: {activeAgentForDisplay.personality}</div>
                                        </div>
                                    </div>
                                    <span className="text-[7.5px] font-bold text-[var(--bi-text-3)] uppercase tracking-widest bg-[var(--bi-surface-1)] px-2 py-0.5 rounded border border-[var(--bi-border)] flex-shrink-0">
                                        {lastMessageForActiveAgent?.round_number ? `Ronda ${lastMessageForActiveAgent.round_number}` : 'Espera de Turno'}
                                    </span>
                                </div>

                                <div className="text-xs lg:text-sm text-[var(--bi-text-2)] leading-relaxed font-medium pt-3 border-t border-[var(--bi-border)]/30 min-h-24">
                                    {lastMessageForActiveAgent ? (
                                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                            {lastMessageForActiveAgent.content}
                                        </ReactMarkdown>
                                    ) : (
                                        <div className="py-6 text-center text-[10px] text-[var(--bi-text-3)] italic">
                                            {polling 
                                                ? `${activeAgentForDisplay.name} se encuentra estructurando su argumentación y analizando los datos. Su intervención se desplegará en su siguiente turno en vivo.`
                                                : `${activeAgentForDisplay.name} no ha intervenido directamente en las rondas de este escenario.`
                                            }
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            ) : (
                /* FEED CLÁSICO VERTICAL (VISTA CHAT) */
                <div className="space-y-6">
                    {filteredMessages.map((m, idx) => {
                        const isLatestAndPolling = polling && idx === filteredMessages.length - 1;
                        const avatarStyle = getAvatarColor(m.agent_name);

                        return (
                            <div
                                key={idx}
                                className={`bg-[var(--bi-surface-0)] border rounded-xl p-5 lg:p-6 space-y-4 animate-in slide-in-from-bottom-4 duration-500 relative overflow-hidden transition-all duration-300 shadow-md ${
                                    isLatestAndPolling 
                                    ? 'border-[var(--module-simulation-accent)] bg-[var(--module-simulation-accent-soft)]/20 shadow-[0_0_12px_rgba(168,85,247,0.06)] scale-[1.01]' 
                                    : 'border-[var(--bi-border)] hover:border-[var(--bi-border-strong)]'
                                }`}
                            >
                                {/* Badge de Ronda */}
                                {m.round_number && (
                                    <div className="absolute top-0 right-0 px-3 py-1 bg-[var(--bi-surface-1)] text-[8px] font-bold uppercase tracking-wider rounded-bl-lg border-l border-b border-[var(--bi-border)] text-[var(--bi-text-2)]">
                                        Ronda {m.round_number}
                                    </div>
                                )}

                                {/* Cabecera del Mensaje */}
                                <div className="flex items-start gap-3.5">
                                    <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-xs uppercase border flex-shrink-0 ${avatarStyle}`}>
                                        {getInitials(m.agent_name)}
                                    </div>
                                    <div className="flex flex-col min-w-0">
                                        <div className="flex items-center flex-wrap gap-2">
                                            <span className="text-xs font-bold text-[var(--bi-text-1)] tracking-tight">
                                                {m.agent_name || "Agente"}
                                            </span>
                                            <span className="text-[8px] font-bold uppercase tracking-wider bg-[var(--bi-surface-1)] px-2 py-0.5 rounded border border-[var(--bi-border)] text-[var(--bi-text-2)]">
                                                {m.agent_role || "Analista"}
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-2 mt-1">
                                            {m.agent_personality && (
                                                <span className="text-[8px] font-bold text-[var(--module-simulation-accent)] uppercase tracking-widest">
                                                    Enfoque: {m.agent_personality}
                                                </span>
                                            )}
                                            {m.agent_description && (
                                                <span className="text-[8px] text-[var(--bi-text-3)] font-semibold uppercase tracking-tight truncate max-w-[200px]">
                                                    • {m.agent_description}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>

                                {/* Contenido Markdown */}
                                <div className="text-xs lg:text-sm text-[var(--bi-text-2)] leading-relaxed font-medium markdown-content pl-13 pt-1 border-t border-[var(--bi-border)]/30">
                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                        {m.content}
                                    </ReactMarkdown>
                                </div>
                            </div>
                        );
                    })}

                    {/* Shimmer de escritura premium activo */}
                    {polling && (
                        <div className="bg-[var(--bi-surface-0)] border border-dashed border-[var(--module-simulation-border)] rounded-xl p-5 shadow-lg animate-pulse space-y-4">
                            <div className="flex items-center gap-3.5">
                                <div className="w-10 h-10 rounded-full bg-[var(--bi-surface-1)] flex items-center justify-center border border-[var(--bi-border)] flex-shrink-0">
                                    <Loader2 className="w-5 h-5 text-[var(--module-simulation-accent)] animate-spin" />
                                </div>
                                <div className="flex flex-col space-y-1">
                                    <span className="text-[10px] font-bold text-[var(--module-simulation-accent)] uppercase tracking-wider">
                                        {currentSpeaker ? `${currentSpeaker.name} está redactando...` : "El Enjambre está analizando..."}
                                    </span>
                                    <span className="text-[8px] text-[var(--bi-text-3)] font-bold uppercase tracking-widest">
                                        {currentSpeaker ? currentSpeaker.role : "Sincronizando modelos"}
                                    </span>
                                </div>
                            </div>
                            
                            <p className="text-[11px] text-[var(--bi-text-2)] italic font-semibold leading-relaxed pl-13">
                                {currentSpeaker 
                                    ? `"${currentSpeaker.name} está procesando las réplicas del debate y formulando su postura (${currentSpeaker.personality.toLowerCase()})..."`
                                    : '"Consolidando la hipótesis del escenario en múltiples dimensiones analíticas..."'}
                            </p>
                            
                            <div className="pl-13 space-y-2 pt-2">
                                <div className="h-2 bg-[var(--bi-surface-1)] rounded w-5/6"></div>
                                <div className="h-2 bg-[var(--bi-surface-1)] rounded w-4/6"></div>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

