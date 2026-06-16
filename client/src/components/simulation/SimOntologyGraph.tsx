'use client';

import React, { useRef, useState, useEffect } from "react";
import { useForceLayout, ForceNode, ForceLink } from "@/hooks/useForceLayout";
import { Network, HelpCircle, ArrowRight, Zap, RefreshCw, ZoomIn, ZoomOut } from "lucide-react";

interface SimOntologyGraphProps {
  nodes: { id: string; label?: string; type?: string }[];
  edges: { source: string; target: string; relationship?: string }[];
  loading?: boolean;
  onNext?: () => void;
  onGenerateAgents?: () => void;
  generatingAgents?: boolean;
  hasGeneratedAgents?: boolean;
}

export function SimOntologyGraph({
  nodes: rawNodes,
  edges: rawEdges,
  loading = false,
  onNext,
  onGenerateAgents,
  generatingAgents = false,
  hasGeneratedAgents = false,
}: SimOntologyGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [dimensions, setDimensions] = useState({ width: 700, height: 480 });
  const [selectedNode, setSelectedNode] = useState<ForceNode | null>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const panStartRef = useRef({ x: 0, y: 0 });

  // Ajustar tamaño del canvas dinámicamente
  useEffect(() => {
    if (containerRef.current) {
      const resizeObserver = new ResizeObserver((entries) => {
        for (let entry of entries) {
          const { width, height } = entry.contentRect;
          setDimensions({
            width: Math.max(width, 400),
            height: Math.max(height || 480, 350)
          });
        }
      });
      resizeObserver.observe(containerRef.current);
      return () => resizeObserver.disconnect();
    }
  }, []);

  // Hook de físicas dirigido por fuerzas
  const {
    nodes,
    links,
    dragStart,
    dragUpdate,
    dragEnd
  } = useForceLayout(rawNodes, rawEdges, {
    width: dimensions.width,
    height: dimensions.height,
    repulsion: 3200,      // Mayor repulsión para dar más espacio
    attraction: 0.04,     // Atracción más suave
    gravity: 0.01,        // Gravedad muy baja para expandir
    restLength: 135       // Distancia de enlaces alargada
  });

  const cx = dimensions.width / 2;
  const cy = dimensions.height / 2;

  // Cálculo dinámico para posicionar etiquetas radialmente hacia afuera y evitar colisiones
  const getLabelCoords = (x: number, y: number) => {
    const dx = x - cx;
    const dy = y - cy;
    const dist = Math.sqrt(dx * dx + dy * dy);
    if (dist === 0) return { x, y: y + 26, vx: 0, vy: 1 };
    const vx = dx / dist;
    const vy = dy / dist;
    const offsetDist = 26; // Radio del nodo (15px) + margen cómodo (11px) = 26px
    return {
      x: x + vx * offsetDist,
      y: y + vy * offsetDist,
      vx,
      vy
    };
  };

  const getGradientId = (type?: string) => {
    const t = (type || "").toLowerCase();
    if (t.includes("métrica") || t.includes("metric") || t.includes("valor")) {
      return "teal-node-grad";
    }
    if (t.includes("fecha") || t.includes("periodo") || t.includes("date") || t.includes("tiempo")) {
      return "blue-node-grad";
    }
    if (t.includes("categoría") || t.includes("dimensión") || t.includes("dimension") || t.includes("entidad")) {
      return "purple-node-grad";
    }
    return "gray-node-grad";
  };

  // Manejadores de arrastre de nodo y paneo de fondo
  const handleMouseDown = (e: React.MouseEvent<SVGElement>, targetId: string | 'bg') => {
    e.stopPropagation();
    if (targetId === 'bg') {
      // Iniciar paneo del fondo
      setIsPanning(true);
      panStartRef.current = { x: e.clientX - pan.x, y: e.clientY - pan.y };
    } else {
      // Iniciar arrastre de nodo
      setSelectedNode(nodes.find(n => n.id === targetId) || null);
      dragStart(targetId);
    }
  };

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (isPanning) {
      setPan({
        x: e.clientX - panStartRef.current.x,
        y: e.clientY - panStartRef.current.y
      });
    } else {
      // Coordenadas locales del SVG con zoom/pan
      if (svgRef.current) {
        const rect = svgRef.current.getBoundingClientRect();
        // Convertir coordenada de pantalla a local del SVG teniendo en cuenta zoom y pan
        const localX = (e.clientX - rect.left - pan.x) / zoom;
        const localY = (e.clientY - rect.top - pan.y) / zoom;
        dragUpdate(localX, localY);
      }
    }
  };

  const handleMouseUpOrLeave = () => {
    if (isPanning) {
      setIsPanning(false);
    } else {
      dragEnd();
    }
  };

  // Color adaptativo según el tipo de nodo (púrpura de simulación, azul acento, teal primario, etc.)
  const getNodeColorClass = (type?: string) => {
    const t = (type || "").toLowerCase();
    if (t.includes("métrica") || t.includes("metric") || t.includes("valor")) {
      return {
        fill: "bg-teal-500/10 dark:bg-teal-400/20",
        border: "border-teal-500 dark:border-teal-400",
        text: "text-teal-600 dark:text-teal-400",
        svgFill: "var(--bi-teal, #2dd4bf)",
        glow: "rgba(45, 212, 191, 0.4)"
      };
    }
    if (t.includes("fecha") || t.includes("periodo") || t.includes("date") || t.includes("tiempo")) {
      return {
        fill: "bg-blue-500/10 dark:bg-blue-400/20",
        border: "border-blue-500 dark:border-blue-400",
        text: "text-blue-600 dark:text-blue-400",
        svgFill: "var(--bi-blue, #60a5fa)",
        glow: "rgba(96, 165, 250, 0.4)"
      };
    }
    if (t.includes("categoría") || t.includes("dimensión") || t.includes("dimension") || t.includes("entidad")) {
      return {
        fill: "bg-purple-500/10 dark:bg-purple-400/20",
        border: "border-purple-500 dark:border-purple-400",
        text: "text-purple-600 dark:text-purple-400",
        svgFill: "var(--bi-purple, #a855f7)",
        glow: "rgba(168, 85, 247, 0.4)"
      };
    }
    return {
      fill: "bg-gray-500/10 dark:bg-gray-400/20",
      border: "border-gray-400 dark:border-gray-500",
      text: "text-gray-600 dark:text-gray-400",
      svgFill: "#94a3b8",
      glow: "rgba(148, 163, 184, 0.3)"
    };
  };

  const handleZoom = (factor: number) => {
    setZoom(prev => Math.max(0.5, Math.min(2.5, prev * factor)));
  };

  const handleResetZoom = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setSelectedNode(null);
  };

  // Renderizar Loader
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] bg-bi-s0 border border-bi-border rounded-lg p-8 space-y-4">
        <div className="relative flex items-center justify-center w-16 h-16">
          <div className="absolute w-full h-full border-4 border-purple-500/20 border-t-purple-500 rounded-full animate-spin"></div>
          <Network className="w-6 h-6 text-purple-400 animate-pulse" />
        </div>
        <div className="text-center space-y-2">
          <h3 className="text-lg font-medium text-bi-text-1">Analizando Estructura de Datos (Reality Graph)</h3>
          <p className="text-sm text-bi-text-2 max-w-md">
            Extrayendo entidades clave, variables y relaciones de causa-efecto utilizando el motor GraphRAG de MiroFish...
          </p>
        </div>
      </div>
    );
  }

  // Renderizar Empty State
  if (nodes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] bg-bi-s0 border border-bi-border rounded-lg p-8 text-center space-y-4">
        <Network className="w-12 h-12 text-bi-text-2/40" />
        <div className="space-y-1">
          <h3 className="text-lg font-medium text-bi-text-1">Reality Graph Vacío</h3>
          <p className="text-sm text-bi-text-2 max-w-sm">
            Selecciona tus fuentes de datos y escribe una hipótesis analítica para modelar el escenario de debate.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
      {/* Columna Izquierda: Grafo Interactivo (SVG) */}
      <div className="lg:col-span-3 flex flex-col bg-bi-s0 border border-bi-border rounded-lg overflow-hidden">
        {/* Barra de herramientas superior */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-bi-border bg-bi-s0/50 backdrop-blur-sm">
          <div className="flex items-center space-x-2">
            <span className="flex h-2 w-2 rounded-full bg-purple-500 animate-pulse" />
            <h3 className="text-xs font-semibold tracking-wider text-bi-text-2 uppercase">Reality Graph (Físicas Activas)</h3>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => handleZoom(1.2)}
              className="p-1.5 bg-bi-s1 border border-bi-border hover:bg-bi-s2 text-bi-text-1 rounded-md transition-colors"
              title="Aumentar Zoom"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => handleZoom(0.8)}
              className="p-1.5 bg-bi-s1 border border-bi-border hover:bg-bi-s2 text-bi-text-1 rounded-md transition-colors"
              title="Disminuir Zoom"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={handleResetZoom}
              className="p-1.5 bg-bi-s1 border border-bi-border hover:bg-bi-s2 text-bi-text-1 rounded-md transition-colors text-xs font-medium flex items-center space-x-1"
            >
              <RefreshCw className="w-3 h-3" />
              <span>Centrar</span>
            </button>
          </div>
        </div>

        {/* Contenedor del lienzo interactivo */}
        <div 
          ref={containerRef}
          className="relative flex-1 min-h-[480px] bg-bi-canvas select-none cursor-grab active:cursor-grabbing overflow-hidden"
        >
          <svg
            ref={svgRef}
            width={dimensions.width}
            height={dimensions.height}
            className="w-full h-full select-none bg-[radial-gradient(circle_at_center,rgba(20,15,30,0.6)_0%,rgba(10,10,12,0.95)_100%)]"
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUpOrLeave}
            onMouseLeave={handleMouseUpOrLeave}
            onMouseDown={(e) => handleMouseDown(e, 'bg')}
          >
            {/* Inyección de Animaciones CSS inline */}
            <style>{`
              @keyframes radar-rotate {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
              }
              .radar-line-ont {
                animation: radar-rotate 22s linear infinite;
              }
            `}</style>

            {/* Definiciones para marcadores de flechas y filtros de brillo */}
            <defs>
              {/* Patrón de Rejilla Cyberpunk */}
              <pattern id="tactical-grid" width="30" height="30" patternUnits="userSpaceOnUse">
                <path d="M 30 0 L 0 0 0 30" fill="none" stroke="rgba(147, 51, 234, 0.07)" strokeWidth="0.8" />
                <circle cx="0" cy="0" r="1.2" fill="rgba(168, 85, 247, 0.18)" />
              </pattern>

              <marker
                id="arrow"
                viewBox="0 0 10 10"
                refX="25"
                refY="5"
                markerWidth="6"
                markerHeight="6"
                orient="auto-start-reverse"
              >
                <path d="M 0 1 L 10 5 L 0 9 z" fill="rgba(168, 85, 247, 0.4)" />
              </marker>

              <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="6" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
              
              {/* Filtro de Brillo Neón */}
              <filter id="neon-glow" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="4.5" result="blur" />
                  <feMerge>
                      <feMergeNode in="blur" />
                      <feMergeNode in="SourceGraphic" />
                  </feMerge>
              </filter>

              {/* Gradientes radiales 3D para nodos de la ontología */}
              <radialGradient id="teal-node-grad" cx="35%" cy="35%" r="65%">
                  <stop offset="0%" stopColor="#2dd4bf" stopOpacity="0.9" />
                  <stop offset="30%" stopColor="#0f766e" stopOpacity="0.95" />
                  <stop offset="70%" stopColor="#115e59" />
                  <stop offset="100%" stopColor="#042f2e" />
              </radialGradient>

              <radialGradient id="blue-node-grad" cx="35%" cy="35%" r="65%">
                  <stop offset="0%" stopColor="#60a5fa" stopOpacity="0.9" />
                  <stop offset="30%" stopColor="#1d4ed8" stopOpacity="0.95" />
                  <stop offset="70%" stopColor="#1e3a8a" />
                  <stop offset="100%" stopColor="#172554" />
              </radialGradient>

              <radialGradient id="purple-node-grad" cx="35%" cy="35%" r="65%">
                  <stop offset="0%" stopColor="#c084fc" stopOpacity="0.9" />
                  <stop offset="30%" stopColor="#6b21a8" stopOpacity="0.95" />
                  <stop offset="70%" stopColor="#4a044e" />
                  <stop offset="100%" stopColor="#2a002a" />
              </radialGradient>

              <radialGradient id="gray-node-grad" cx="35%" cy="35%" r="65%">
                  <stop offset="0%" stopColor="#cbd5e1" stopOpacity="0.9" />
                  <stop offset="30%" stopColor="#475569" stopOpacity="0.95" />
                  <stop offset="70%" stopColor="#1e293b" />
                  <stop offset="100%" stopColor="#0f172a" />
              </radialGradient>

              {/* Gradiente de Brillo Especular para efecto de Cristal 3D */}
              <radialGradient id="glass-specular" cx="30%" cy="30%" r="40%">
                  <stop offset="0%" stopColor="rgba(255, 255, 255, 0.4)" />
                  <stop offset="50%" stopColor="rgba(255, 255, 255, 0.05)" />
                  <stop offset="100%" stopColor="rgba(255, 255, 255, 0)" stopOpacity="0" />
              </radialGradient>
            </defs>

            {/* 1. Fondo de Rejilla Táctica */}
            <rect width={dimensions.width} height={dimensions.height} fill="url(#tactical-grid)" />

            {/* 2. Escáner de Radar Giratorio Concéntrico */}
            <circle cx={cx} cy={cy} r={240} fill="none" stroke="rgba(147, 51, 234, 0.04)" strokeWidth="1" />
            <circle cx={cx} cy={cy} r={140} fill="none" stroke="rgba(147, 51, 234, 0.03)" strokeWidth="1" strokeDasharray="5 15" />
            <line 
                x1={cx} 
                y1={cy} 
                x2={cx + 240} 
                y2={cy} 
                stroke="rgba(168, 85, 247, 0.1)" 
                strokeWidth="2" 
                strokeLinecap="round"
                className="radar-line-ont"
                style={{ transformOrigin: `${cx}px ${cy}px` }}
            />

            {/* Grupo principal con zoom y paneo */}
            <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
              
              {/* Renderizar Aristas (Enlaces) */}
              {links.map((link, idx) => {
                const sourceNode = nodes.find(n => n.id === link.source);
                const targetNode = nodes.find(n => n.id === link.target);
                if (!sourceNode || !targetNode) return null;
                
                const midX = (sourceNode.x + targetNode.x) / 2;
                const midY = (sourceNode.y + targetNode.y) / 2;

                return (
                  <g key={`link-${idx}`} className="group/link">
                    {/* Línea del enlace */}
                    <line
                      x1={sourceNode.x}
                      y1={sourceNode.y}
                      x2={targetNode.x}
                      y2={targetNode.y}
                      stroke="rgba(168, 85, 247, 0.22)"
                      strokeWidth="1.5"
                      strokeOpacity="0.5"
                      className="group-hover/link:stroke-blue-400 group-hover/link:stroke-[2px] transition-all"
                      markerEnd="url(#arrow)"
                    />
                    
                    {/* Etiqueta de la relación (al pasar el mouse) */}
                    {link.relationship && (
                      <g transform={`translate(${midX}, ${midY})`}>
                        <rect
                          x={-45}
                          y={-8}
                          width={90}
                          height={16}
                          rx={3}
                          fill="rgba(10, 8, 16, 0.88)"
                          stroke="rgba(168, 85, 247, 0.25)"
                          strokeWidth="0.5"
                          className="opacity-0 group-hover/link:opacity-100 transition-opacity"
                          style={{ backdropFilter: 'blur(2px)' }}
                        />
                        <text
                          textAnchor="middle"
                          y={3}
                          fontSize="9"
                          fill="var(--bi-text-2)"
                          className="opacity-0 group-hover/link:opacity-100 transition-opacity font-semibold pointer-events-none"
                        >
                          {link.relationship}
                        </text>
                      </g>
                    )}
                  </g>
                );
              })}

              {/* Renderizar Nodos (Entidades en Cristal 3D) */}
              {nodes.map((node) => {
                const colorTheme = getNodeColorClass(node.type);
                const isSelected = selectedNode?.id === node.id;
                const nodeR = isSelected ? 18 : 14;

                return (
                  <g
                    key={node.id}
                    transform={`translate(${node.x}, ${node.y})`}
                    onMouseDown={(e) => handleMouseDown(e, node.id)}
                    className="cursor-pointer group"
                  >
                    {/* Brillo perimetral al seleccionar o en hover */}
                    <circle
                      r={nodeR + 6}
                      fill={colorTheme.svgFill}
                      opacity={isSelected ? 0.35 : 0.06}
                      className="group-hover:opacity-20 transition-all"
                      style={{ filter: isSelected ? 'url(#glow)' : 'none' }}
                    />
                    
                    {/* Círculo base del nodo */}
                    <circle
                      r={nodeR}
                      fill={`url(#${getGradientId(node.type)})`}
                      stroke={isSelected ? "rgba(255, 255, 255, 0.75)" : "rgba(255, 255, 255, 0.2)"}
                      strokeWidth={isSelected ? 1.5 : 0.8}
                    />

                    {/* Specular de Cristal */}
                    <circle
                      r={nodeR}
                      fill="url(#glass-specular)"
                      pointerEvents="none"
                    />

                    {/* Micro-indicador de categoría */}
                    <circle
                      r={3.2}
                      fill="rgba(255, 255, 255, 0.85)"
                      style={{ filter: 'drop-shadow(0 0 1px rgba(255,255,255,0.8))' }}
                    />
                  </g>
                );
              })}

              {/* Renderizar Etiquetas flotantes (Capa superior anticolisión) */}
              {nodes.map((node) => {
                const isSelected = selectedNode?.id === node.id;
                const labelCoord = getLabelCoords(node.x, node.y);
                
                const badgeW = 100;
                const badgeH = 17;
                const rx = -badgeW / 2 + (labelCoord.vx * badgeW / 2);
                const ry = -badgeH / 2 + (labelCoord.vy * badgeH / 2);
                const textX = labelCoord.vx * badgeW / 2;
                const textY = labelCoord.vy * badgeH / 2 + 3.0;

                return (
                  <g
                    key={`label-${node.id}`}
                    transform={`translate(${labelCoord.x}, ${labelCoord.y})`}
                    className="pointer-events-none"
                  >
                    <rect
                      x={rx}
                      y={ry}
                      width={badgeW}
                      height={badgeH}
                      rx="8.5"
                      fill="rgba(10, 8, 16, 0.82)"
                      stroke={isSelected ? "var(--bi-purple)" : "rgba(168, 85, 247, 0.25)"}
                      strokeWidth="0.8"
                      style={{ backdropFilter: 'blur(3px)' }}
                    />
                    <text
                      x={textX}
                      y={textY}
                      textAnchor="middle"
                      className={`text-[8.5px] font-bold select-none ${
                        isSelected ? "fill-[var(--bi-purple)]" : "fill-[var(--bi-text-1)]"
                      }`}
                    >
                      {node.label && node.label.length > 17
                        ? `${node.label.substring(0, 14)}...`
                        : node.label || node.id}
                    </text>
                  </g>
                );
              })}
            </g>
          </svg>
          
          {/* Leyenda en esquina inferior izquierda */}
          <div className="absolute bottom-3 left-3 bg-bi-s0/90 border border-bi-border rounded-md p-2.5 text-[10px] space-y-1.5 backdrop-blur-sm pointer-events-none">
            <div className="font-semibold text-bi-text-2 uppercase tracking-wider pb-0.5 border-b border-bi-border">Nodos</div>
            <div className="flex items-center space-x-1.5">
              <span className="h-2 w-2 rounded-full bg-teal-400" />
              <span className="text-bi-text-1 font-medium">Métricas & Cifras</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <span className="h-2 w-2 rounded-full bg-blue-400" />
              <span className="text-bi-text-1 font-medium">Fechas & Tiempos</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <span className="h-2 w-2 rounded-full bg-purple-400" />
              <span className="text-bi-text-1 font-medium">Dimensiones & Categorías</span>
            </div>
          </div>
        </div>
      </div>

      {/* Columna Derecha: Panel Detalle / Control */}
      <div className="flex flex-col space-y-4">
        {/* Tarjeta del Nodo Seleccionado */}
        <div className="bg-bi-s0 border border-bi-border rounded-lg p-4 flex flex-col justify-between min-h-[160px]">
          <div>
            <h4 className="text-xs font-semibold text-bi-text-2 tracking-wider uppercase mb-2">Entidad Inspeccionada</h4>
            {selectedNode ? (
              <div className="space-y-2.5">
                <div>
                  <div className="text-sm font-bold text-bi-text-1 leading-tight">{selectedNode.label}</div>
                  <div className="text-[10px] text-bi-text-2 mt-0.5 font-mono">{selectedNode.id}</div>
                </div>
                <div>
                  <span className={`inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full ${getNodeColorClass(selectedNode.type).fill} ${getNodeColorClass(selectedNode.type).text} border border-current/25`}>
                    {selectedNode.type || "Entidad"}
                  </span>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center text-center h-[90px] border border-dashed border-bi-border rounded-md p-3">
                <HelpCircle className="w-5 h-5 text-bi-text-2/40 mb-1" />
                <p className="text-[11px] text-bi-text-2">Haz click en cualquier nodo para ver sus metadatos.</p>
              </div>
            )}
          </div>
        </div>

        {/* Acciones principales y Stepper de MiroFish */}
        <div className="bg-bi-s0 border border-bi-border rounded-lg p-4 flex-1 flex flex-col justify-between">
          <div className="space-y-3.5">
            <h4 className="text-xs font-semibold text-bi-text-2 tracking-wider uppercase">Enjambre MiroFish</h4>
            <p className="text-xs text-bi-text-2 leading-relaxed">
              El Reality Graph ha mapeado las relaciones en tus datos. Ahora el sistema generará un enjambre de agentes consultores expertos (Swarm Config) alineados con estas temáticas detectadas.
            </p>
            
            <div className="pt-2 border-t border-bi-border space-y-2">
              <div className="flex items-center space-x-2 text-[11px]">
                <div className="flex h-5 w-5 items-center justify-center rounded-full bg-purple-500/20 text-purple-400 font-mono font-bold">1</div>
                <span className="text-bi-text-1 font-semibold">Ontología extraída</span>
              </div>
              <div className="flex items-center space-x-2 text-[11px]">
                <div className={`flex h-5 w-5 items-center justify-center rounded-full ${hasGeneratedAgents ? 'bg-purple-500/20 text-purple-400' : 'bg-bi-s1 text-bi-text-2'} font-mono font-bold`}>2</div>
                <span className={hasGeneratedAgents ? 'text-bi-text-1 font-semibold' : 'text-bi-text-2'}>Personalización de Agentes</span>
              </div>
            </div>
          </div>

          <div className="space-y-2 mt-4">
            {onGenerateAgents && !hasGeneratedAgents && (
              <button
                onClick={onGenerateAgents}
                disabled={generatingAgents}
                className="w-full flex items-center justify-center space-x-2 py-2 px-3 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-md text-xs font-semibold shadow-sm transition-all active:scale-[0.98]"
              >
                {generatingAgents ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Diseñando Enjambre...</span>
                  </>
                ) : (
                  <>
                    <Zap className="w-3.5 h-3.5" />
                    <span>Autogenerar Enjambre</span>
                  </>
                )}
              </button>
            )}

            {hasGeneratedAgents && onNext && (
              <button
                onClick={onNext}
                className="w-full flex items-center justify-center space-x-2 py-2 px-3 bg-teal-600 hover:bg-teal-700 text-white rounded-md text-xs font-semibold shadow-sm transition-all active:scale-[0.98]"
              >
                <span>Configurar Agentes</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
