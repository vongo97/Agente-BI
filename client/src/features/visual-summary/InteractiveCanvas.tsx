'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useTheme } from '@/context/ThemeContext';
import * as Icons from 'lucide-react';
import { 
    ZoomIn, 
    ZoomOut, 
    RefreshCw, 
    Download, 
    Plus, 
    Trash2, 
    Maximize2, 
    Edit3,
    Eye,
    HelpCircle
} from 'lucide-react';

interface GraphNode {
    id: string;
    label: string;
    type?: 'root' | 'child' | 'leaf';
    icon?: string;
}

interface GraphEdge {
    source: string;
    target: string;
    label?: string;
}

interface InteractiveCanvasProps {
    nodes: GraphNode[];
    edges: GraphEdge[];
    visualType: 'flowchart' | 'mindmap' | 'timeline' | 'comparison' | 'architecture' | 'auto';
    onGraphChange?: (nodes: GraphNode[], edges: GraphEdge[]) => void;
}

interface NodePosition {
    id: string;
    label: string;
    type: 'root' | 'child' | 'leaf';
    icon: string;
    x: number;
    y: number;
}

// Mapeador de iconos de Lucide dinámico
function DynamicIcon({ name, className }: { name: string; className?: string }) {
    const pascalName = name
        .split('-')
        .map(part => part.charAt(0).toUpperCase() + part.slice(1))
        .join('');
    
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const IconComponent = (Icons as any)[pascalName] || HelpCircle;
    return <IconComponent className={className} />;
}

export function InteractiveCanvas({ nodes: initialNodes, edges: initialEdges, visualType, onGraphChange }: InteractiveCanvasProps) {
    const canvasRef = useRef<HTMLDivElement>(null);
    const { theme } = useTheme();
    const isDark = theme === 'dark';

    // Estados del grafo y posiciones
    const [nodes, setNodes] = useState<NodePosition[]>([]);
    const [edges, setEdges] = useState<GraphEdge[]>([]);
    
    // Estados para Zoom y Pan (Lienzo)
    const [scale, setScale] = useState<number>(1);
    const [panOffset, setPanOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
    const [isCanvasDragging, setIsCanvasDragging] = useState<boolean>(false);
    const [canvasDragStart, setCanvasDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

    // Estados para Arrastre de Nodos Individuales
    const [draggingNodeId, setDraggingNodeId] = useState<string | null>(null);
    const [nodeDragStart, setNodeDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

    // Estado para Edición Inline de Nodo (Doble clic)
    const [editingNodeId, setEditingNodeId] = useState<string | null>(null);
    const [editingText, setEditingText] = useState<string>('');

    // --- 1. Inicialización y Layout Automático ---
    useEffect(() => {
        if (!initialNodes || initialNodes.length === 0) {
            setNodes([]);
            setEdges([]);
            return;
        }

        // Evitar bucles infinitos si la referencia es igual
        setEdges(initialEdges || []);

        const width = 850;
        const height = 480;
        const centerX = width / 2;
        const centerY = height / 2;

        const calculatedPositions: NodePosition[] = [];

        if (visualType === 'mindmap' || visualType === 'auto') {
            // --- Layout Radial ---
            const rootNode = initialNodes.find(n => n.type === 'root') || initialNodes[0];
            const otherNodes = initialNodes.filter(n => n.id !== rootNode.id);
            
            // Posición raíz en el centro
            calculatedPositions.push({
                id: rootNode.id,
                label: rootNode.label,
                type: 'root',
                icon: rootNode.icon || 'brain',
                x: centerX,
                y: centerY
            });

            // Agrupar hijos directos de la raíz
            const rootChildren = otherNodes.filter(n => 
                initialEdges.some(e => e.source === rootNode.id && e.target === n.id)
            );
            const remainingNodes = otherNodes.filter(n => !rootChildren.some(rc => rc.id === n.id));

            // Distribuir hijos en órbita 1 (R = 160)
            const numChildren = rootChildren.length;
            rootChildren.forEach((child, i) => {
                const angle = (2 * Math.PI * i) / (numChildren || 1);
                const r1 = 170;
                const childX = centerX + r1 * Math.cos(angle);
                const childY = centerY + r1 * Math.sin(angle);

                calculatedPositions.push({
                    id: child.id,
                    label: child.label,
                    type: child.type || 'child',
                    icon: child.icon || 'circle',
                    x: childX,
                    y: childY
                });

                // Hojas conectadas a este hijo
                const leaves = remainingNodes.filter(n =>
                    initialEdges.some(e => e.source === child.id && e.target === n.id)
                );
                const numLeaves = leaves.length;

                leaves.forEach((leaf, j) => {
                    // Distribuir las hojas en abanico desde la posición del padre
                    const leafAngleOffset = numLeaves > 1 ? (0.6 * (j - (numLeaves - 1) / 2)) : 0;
                    const leafAngle = angle + leafAngleOffset;
                    const r2 = 120; // Distancia adicional desde el padre
                    const leafX = childX + r2 * Math.cos(leafAngle);
                    const leafY = childY + r2 * Math.sin(leafAngle);

                    calculatedPositions.push({
                        id: leaf.id,
                        label: leaf.label,
                        type: 'leaf',
                        icon: leaf.icon || 'square',
                        x: leafX,
                        y: leafY
                    });
                });
            });

            // Añadir nodos sueltos si queda alguno
            otherNodes.forEach(node => {
                if (!calculatedPositions.some(p => p.id === node.id)) {
                    calculatedPositions.push({
                        id: node.id,
                        label: node.label,
                        type: node.type || 'leaf',
                        icon: node.icon || 'help-circle',
                        x: centerX + (Math.random() - 0.5) * 300,
                        y: centerY + (Math.random() - 0.5) * 200
                    });
                }
            });

        } else if (visualType === 'timeline') {
            // --- Layout Lineal Horizontal ---
            const step = 220;
            const startX = Math.max(100, centerX - (initialNodes.length - 1) * step / 2);
            
            initialNodes.forEach((node, i) => {
                calculatedPositions.push({
                    id: node.id,
                    label: node.label,
                    type: node.type || (i === 0 ? 'root' : i === initialNodes.length - 1 ? 'leaf' : 'child'),
                    icon: node.icon || 'clock',
                    x: startX + i * step,
                    y: centerY
                });
            });

        } else if (visualType === 'comparison') {
            // --- Layout en Dos Columnas ---
            const rootNode = initialNodes.find(n => n.type === 'root') || initialNodes[0];
            const otherNodes = initialNodes.filter(n => n.id !== rootNode.id);
            
            calculatedPositions.push({
                id: rootNode.id,
                label: rootNode.label,
                type: 'root',
                icon: rootNode.icon || 'scale',
                x: centerX,
                y: centerY - 100
            });

            // Dividir por la mitad para columna izquierda y derecha
            const half = Math.ceil(otherNodes.length / 2);
            const leftNodes = otherNodes.slice(0, half);
            const rightNodes = otherNodes.slice(half);

            const vStep = 80;
            const startY = centerY - ((Math.max(leftNodes.length, rightNodes.length) - 1) * vStep) / 2;

            leftNodes.forEach((node, i) => {
                calculatedPositions.push({
                    id: node.id,
                    label: node.label,
                    type: 'child',
                    icon: node.icon || 'minus-circle',
                    x: centerX - 180,
                    y: startY + i * vStep
                });
            });

            rightNodes.forEach((node, i) => {
                calculatedPositions.push({
                    id: node.id,
                    label: node.label,
                    type: 'leaf',
                    icon: node.icon || 'plus-circle',
                    x: centerX + 180,
                    y: startY + i * vStep
                });
            });

        } else {
            // --- Layout Jerárquico por Capas / Columnas ---
            // Calcular in-degree de cada nodo para saber dependencias
            const inDegrees: Record<string, number> = {};
            initialNodes.forEach(n => { inDegrees[n.id] = 0; });
            initialEdges.forEach(e => {
                if (inDegrees[e.target] !== undefined) {
                    inDegrees[e.target]++;
                }
            });

            // Asignar niveles
            const levels: Record<string, number> = {};
            const queue: string[] = [];
            
            initialNodes.forEach(n => {
                if (inDegrees[n.id] === 0) {
                    levels[n.id] = 0;
                    queue.push(n.id);
                }
            });

            while (queue.length > 0) {
                const currId = queue.shift()!;
                const currLevel = levels[currId];
                
                const targets = initialEdges.filter(e => e.source === currId).map(e => e.target);
                targets.forEach(targetId => {
                    if (levels[targetId] === undefined || levels[targetId] < currLevel + 1) {
                        levels[targetId] = currLevel + 1;
                        queue.push(targetId);
                    }
                });
            }

            // Agrupar nodos por nivel asignado
            const nodesByLevel: Record<number, string[]> = {};
            initialNodes.forEach(n => {
                const lvl = levels[n.id] || 0;
                if (!nodesByLevel[lvl]) nodesByLevel[lvl] = [];
                nodesByLevel[lvl].push(n.id);
            });

            const maxLevel = Math.max(...Object.keys(nodesByLevel).map(Number), 0);
            const hStep = 240;
            const startX = centerX - (maxLevel * hStep) / 2;

            Object.entries(nodesByLevel).forEach(([lvlStr, ids]) => {
                const lvl = Number(lvlStr);
                const numIds = ids.length;
                const vStep = 90;
                const startY = centerY - ((numIds - 1) * vStep) / 2;

                ids.forEach((id, i) => {
                    const node = initialNodes.find(n => n.id === id)!;
                    calculatedPositions.push({
                        id: node.id,
                        label: node.label,
                        type: node.type || (lvl === 0 ? 'root' : lvl === maxLevel ? 'leaf' : 'child'),
                        icon: node.icon || 'network',
                        x: startX + lvl * hStep,
                        y: startY + i * vStep
                    });
                });
            });
        }

        setNodes(calculatedPositions);
    }, [initialNodes, initialEdges, visualType]);

    // Notificar cambios al padre cuando mutan las propiedades de los nodos o aristas
    const triggerGraphChange = (newNodes: NodePosition[], newEdges: GraphEdge[]) => {
        if (onGraphChange) {
            const rawNodes = newNodes.map(n => ({
                id: n.id,
                label: n.label,
                type: n.type,
                icon: n.icon
            }));
            onGraphChange(rawNodes, newEdges);
        }
    };

    // --- 2. Lógica de Arrastre de Nodos (Drag) ---
    const handleNodeMouseDown = (nodeId: string, e: React.MouseEvent) => {
        e.stopPropagation();
        if (editingNodeId) return; // Bloquear arrastre durante edición de texto
        if (e.button !== 0) return; // Solo clic izquierdo

        setDraggingNodeId(nodeId);
        const node = nodes.find(n => n.id === nodeId);
        if (node) {
            // Guardar posición inicial del mouse escalado
            setNodeDragStart({
                x: e.clientX / scale - node.x,
                y: e.clientY / scale - node.y
            });
        }
    };

    // --- 3. Lógica de Arrastre del Lienzo (Pan) ---
    const handleCanvasMouseDown = (e: React.MouseEvent) => {
        if (e.button !== 0) return; // Solo clic izquierdo
        setIsCanvasDragging(true);
        setCanvasDragStart({
            x: e.clientX - panOffset.x,
            y: e.clientY - panOffset.y
        });
    };

    const handleMouseMove = (e: React.MouseEvent) => {
        if (draggingNodeId) {
            // Mover Nodo
            setNodes(prev => prev.map(n => {
                if (n.id === draggingNodeId) {
                    return {
                        ...n,
                        x: e.clientX / scale - nodeDragStart.x,
                        y: e.clientY / scale - nodeDragStart.y
                    };
                }
                return n;
            }));
        } else if (isCanvasDragging) {
            // Mover Lienzo (Pan)
            setPanOffset({
                x: e.clientX - canvasDragStart.x,
                y: e.clientY - canvasDragStart.y
            });
        }
    };

    const handleMouseUp = () => {
        if (draggingNodeId) {
            triggerGraphChange(nodes, edges);
            setDraggingNodeId(null);
        }
        setIsCanvasDragging(false);
    };

    const handleWheel = (e: React.WheelEvent) => {
        e.preventDefault();
        const zoomFactor = 1.08;
        const newScale = e.deltaY < 0 ? scale * zoomFactor : scale / zoomFactor;
        setScale(Math.min(Math.max(newScale, 0.2), 3));
    };

    // --- 4. Controles Flotantes ---
    const handleZoomIn = () => setScale(s => Math.min(s * 1.15, 3));
    const handleZoomOut = () => setScale(s => Math.max(s / 1.15, 0.2));
    const handleReset = () => {
        setScale(1);
        setPanOffset({ x: 0, y: 0 });
    };

    // --- 5. Edición Inline WYSIWYG ---
    const handleNodeDoubleClick = (nodeId: string, label: string) => {
        setEditingNodeId(nodeId);
        setEditingText(label);
    };

    const handleSaveNodeLabel = (nodeId: string) => {
        if (editingText.trim()) {
            const updatedNodes = nodes.map(n => n.id === nodeId ? { ...n, label: editingText } : n);
            setNodes(updatedNodes);
            triggerGraphChange(updatedNodes, edges);
        }
        setEditingNodeId(null);
    };

    // --- 6. Creación y Eliminación Interactiva ---
    const handleAddChildNode = (parentId: string) => {
        const parent = nodes.find(n => n.id === parentId);
        if (!parent) return;

        const newId = `node-${Math.floor(Math.random() * 100000)}`;
        const newNode: NodePosition = {
            id: newId,
            label: 'Nuevo Concepto',
            type: 'leaf',
            icon: 'circle',
            x: parent.x + 150 + (Math.random() - 0.5) * 40,
            y: parent.y + (Math.random() - 0.5) * 60
        };

        const newEdge: GraphEdge = {
            source: parentId,
            target: newId,
            label: 'conecta'
        };

        const updatedNodes = [...nodes, newNode];
        const updatedEdges = [...edges, newEdge];

        setNodes(updatedNodes);
        setEdges(updatedEdges);
        triggerGraphChange(updatedNodes, updatedEdges);
    };

    const handleDeleteNode = (nodeId: string, e: React.MouseEvent) => {
        e.stopPropagation();
        // Evitar dejar el grafo huérfano si borramos el raíz único
        const node = nodes.find(n => n.id === nodeId);
        if (node?.type === 'root' && nodes.filter(n => n.type === 'root').length === 1 && nodes.length > 1) {
            alert("No puedes borrar el nodo central raíz del diagrama.");
            return;
        }

        const updatedNodes = nodes.filter(n => n.id !== nodeId);
        const updatedEdges = edges.filter(e => e.source !== nodeId && e.target !== nodeId);

        setNodes(updatedNodes);
        setEdges(updatedEdges);
        triggerGraphChange(updatedNodes, updatedEdges);
    };

    // --- 7. Exportación Dinámica ---
    const handleDownloadSVG = () => {
        // Encontrar o fabricar un SVG que junte los elementos actuales
        if (!canvasRef.current) return;
        const svgElement = canvasRef.current.querySelector('svg');
        if (!svgElement) return;

        const clonedSvg = svgElement.cloneNode(true) as SVGElement;
        
        // Incrustar los nodos HTML dentro del SVG en un contenedor <foreignObject>
        // para descargarlo todo en un solo bloque vectorial estándar
        const svgNS = "http://www.w3.org/2000/svg";
        const foreignObject = document.createElementNS(svgNS, "foreignObject");
        
        // Obtener la caja contenedora de los nodos
        const minX = Math.min(...nodes.map(n => n.x)) - 100;
        const minY = Math.min(...nodes.map(n => n.y)) - 100;
        const maxX = Math.max(...nodes.map(n => n.x)) + 300;
        const maxY = Math.max(...nodes.map(n => n.y)) + 150;
        const width = maxX - minX;
        const height = maxY - minY;

        foreignObject.setAttribute("x", `${minX}`);
        foreignObject.setAttribute("y", `${minY}`);
        foreignObject.setAttribute("width", `${width}`);
        foreignObject.setAttribute("height", `${height}`);

        // Crear contenedor HTML para colocar los nodos en la misma posición relativa
        const htmlWrapper = document.createElement("div");
        htmlWrapper.setAttribute("xmlns", "http://www.w3.org/1999/xhtml");
        htmlWrapper.style.position = "relative";
        htmlWrapper.style.width = "100%";
        htmlWrapper.style.height = "100%";
        
        nodes.forEach(node => {
            const el = document.createElement("div");
            el.style.position = "absolute";
            el.style.left = `${node.x - minX}px`;
            el.style.top = `${node.y - minY}px`;
            el.style.padding = "10px 14px";
            el.style.background = isDark ? "#1e293b" : "#ffffff";
            el.style.border = `1.5px solid ${isDark ? "#334155" : "#cbd5e1"}`;
            el.style.borderRadius = "8px";
            el.style.color = isDark ? "#ffffff" : "#0f172a";
            el.style.fontSize = "11px";
            el.style.fontFamily = "sans-serif";
            el.innerText = node.label;
            htmlWrapper.appendChild(el);
        });

        foreignObject.appendChild(htmlWrapper);
        clonedSvg.appendChild(foreignObject);
        clonedSvg.setAttribute("viewBox", `${minX} ${minY} ${width} ${height}`);
        clonedSvg.setAttribute("width", "100%");
        clonedSvg.setAttribute("height", "100%");

        const svgString = new XMLSerializer().serializeToString(clonedSvg);
        const blob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `vektra-canvas-${Date.now()}.svg`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    };

    return (
        <div className="flex flex-col h-full bg-[var(--bi-surface-0)] border border-[var(--bi-border)] rounded-lg overflow-hidden shadow-sm relative group/canvas">
            {/* Cabecera del Canvas */}
            <div className="flex justify-between items-center px-5 py-3 border-b border-[var(--bi-border)] bg-[var(--bi-surface-0)] z-20 shrink-0 select-none">
                <span className="text-[10px] font-bold text-[var(--bi-text-3)] uppercase tracking-wider flex items-center gap-1.5">
                    <Eye className="w-3.5 h-3.5 text-[var(--bi-blue)]" /> Vektra Canvas Interactivo
                </span>
                
                <div className="flex items-center gap-2">
                    <span className="text-[8px] bg-[var(--bi-blue-dim)] text-[var(--bi-blue)] border border-[var(--bi-blue-border)] py-0.5 px-2 rounded text-[8px] font-bold uppercase tracking-wider">
                        {visualType}
                    </span>
                    <button
                        onClick={handleDownloadSVG}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-[var(--bi-blue)] hover:bg-[var(--bi-blue-hover)] text-[var(--bi-canvas)] rounded-md text-[10px] font-semibold uppercase tracking-wider transition-all cursor-pointer shadow-sm"
                        title="Exportar canvas vectorial"
                    >
                        <Download className="w-3.5 h-3.5" />
                        <span>Exportar</span>
                    </button>
                </div>
            </div>

            {/* Lienzo del Canvas */}
            <div 
                ref={canvasRef}
                className="flex-1 min-h-[400px] bg-[var(--bi-canvas)] overflow-hidden relative cursor-grab select-none active:cursor-grabbing"
                onMouseDown={handleCanvasMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
                onWheel={handleWheel}
            >
                {/* Rejilla de Fondo sutil */}
                <div 
                    className="absolute inset-0 pointer-events-none opacity-[0.03] dark:opacity-[0.04]"
                    style={{
                        backgroundImage: `radial-gradient(var(--bi-text-1) 1.5px, transparent 1.5px)`,
                        backgroundSize: '24px 24px',
                        transform: `translate(${panOffset.x}px, ${panOffset.y}px) scale(${scale})`,
                        transformOrigin: '0 0'
                    }}
                />

                {/* Contenedor del Grafo Transformado (Zoom & Pan) */}
                <div
                    style={{
                        transform: `translate(${panOffset.x}px, ${panOffset.y}px) scale(${scale})`,
                        transformOrigin: '0 0',
                        width: '100%',
                        height: '100%',
                        position: 'absolute',
                        left: 0,
                        top: 0
                    }}
                >
                    {/* Aristas (Conexiones SVG) en el fondo */}
                    <svg className="absolute inset-0 w-full h-full pointer-events-none z-0 overflow-visible">
                        <defs>
                            <marker
                                id="arrowhead"
                                markerWidth="10"
                                markerHeight="7"
                                refX="15"
                                refY="3.5"
                                orient="auto"
                            >
                                <polygon
                                    points="0 0, 10 3.5, 0 7"
                                    fill={isDark ? '#475569' : '#94a3b8'}
                                />
                            </marker>
                        </defs>
                        {edges.map((edge, i) => {
                            const sourceNode = nodes.find(n => n.id === edge.source);
                            const targetNode = nodes.find(n => n.id === edge.target);
                            if (!sourceNode || !targetNode) return null;

                            // Calcular centros
                            const x1 = sourceNode.x;
                            const y1 = sourceNode.y;
                            const x2 = targetNode.x;
                            const y2 = targetNode.y;

                            // Dibujar una curva Bezier cúbica suave
                            const dx = Math.abs(x2 - x1) * 0.5;
                            const pathData = `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;

                            return (
                                <g key={i}>
                                    <path
                                        d={pathData}
                                        fill="none"
                                        stroke={isDark ? '#334155' : '#cbd5e1'}
                                        strokeWidth="2"
                                        markerEnd="url(#arrowhead)"
                                        className="transition-all"
                                    />
                                    {edge.label && edge.label !== 'conecta' && (
                                        <g transform={`translate(${(x1 + x2) / 2}, ${(y1 + y2) / 2})`}>
                                            <rect
                                                x={-30}
                                                y={-8}
                                                width={60}
                                                height={16}
                                                rx={4}
                                                fill={isDark ? '#0d1117' : '#ffffff'}
                                                stroke={isDark ? '#334155' : '#e2e8f0'}
                                                strokeWidth="1"
                                            />
                                            <text
                                                textAnchor="middle"
                                                y={3}
                                                fontSize="8px"
                                                fontWeight="bold"
                                                fill={isDark ? '#94a3b8' : '#64748b'}
                                                className="uppercase tracking-wider"
                                            >
                                                {edge.label}
                                            </text>
                                        </g>
                                    )}
                                </g>
                            );
                        })}
                    </svg>

                    {/* Nodos (Tarjetas React) en el primer plano */}
                    {nodes.map(node => {
                        const isEditing = editingNodeId === node.id;
                        
                        // Clases según la jerarquía del nodo
                        const isRoot = node.type === 'root';
                        const typeClasses = isRoot 
                            ? 'bg-[var(--bi-blue-dim)] border-[var(--bi-blue-border)] text-[var(--bi-text-1)] min-w-[150px] shadow-md z-30'
                            : 'bg-[var(--bi-surface-1)] border-[var(--bi-border)] text-[var(--bi-text-2)] hover:text-[var(--bi-text-1)] hover:border-[var(--bi-blue-border)] z-20 min-w-[130px]';

                        return (
                            <div
                                key={node.id}
                                onMouseDown={(e) => handleNodeMouseDown(node.id, e)}
                                onDoubleClick={() => handleNodeDoubleClick(node.id, node.label)}
                                className={`absolute rounded-lg border p-3 flex flex-col items-center gap-1.5 transition-shadow cursor-pointer select-none group/node -translate-x-1/2 -translate-y-1/2 ${typeClasses}`}
                                style={{
                                    left: `${node.x}px`,
                                    top: `${node.y}px`,
                                }}
                            >
                                {/* Barra superior de herramientas del nodo (Aparece en hover) */}
                                <div className="absolute -top-3.5 right-1 bg-[var(--bi-surface-0)] border border-[var(--bi-border)] rounded-md py-0.5 px-1 flex gap-1 items-center opacity-0 group-hover/node:opacity-100 transition-opacity shadow-sm z-50">
                                    <button
                                        onClick={() => handleAddChildNode(node.id)}
                                        className="p-0.5 hover:bg-[var(--bi-surface-2)] text-[var(--bi-blue)] rounded transition-colors"
                                        title="Agregar nodo conectado"
                                    >
                                        <Plus className="w-3 h-3" />
                                    </button>
                                    <button
                                        onClick={(e) => handleDeleteNode(node.id, e)}
                                        className="p-0.5 hover:bg-[var(--bi-surface-2)] text-[var(--bi-red)] rounded transition-colors"
                                        title="Eliminar nodo"
                                    >
                                        <Trash2 className="w-3 h-3" />
                                    </button>
                                </div>

                                {/* Icono del Nodo */}
                                <div className={`w-7 h-7 rounded-md flex items-center justify-center ${isRoot ? 'bg-[var(--bi-blue)] text-[var(--bi-canvas)]' : 'bg-[var(--bi-surface-2)] text-[var(--bi-text-3)]'}`}>
                                    <DynamicIcon name={node.icon} className="w-4 h-4" />
                                </div>

                                {/* Texto del Nodo */}
                                {isEditing ? (
                                    <input
                                        type="text"
                                        value={editingText}
                                        onChange={(e) => setEditingText(e.target.value)}
                                        onBlur={() => handleSaveNodeLabel(node.id)}
                                        onKeyDown={(e) => {
                                            if (e.key === 'Enter') handleSaveNodeLabel(node.id);
                                        }}
                                        autoFocus
                                        className="bg-[var(--bi-canvas)] border border-[var(--bi-blue-border)] rounded px-1.5 py-0.5 text-center text-[10px] text-[var(--bi-text-1)] outline-none w-full font-semibold"
                                    />
                                ) : (
                                    <div className="flex flex-col items-center">
                                        <span className={`text-[10px] text-center font-bold tracking-tight leading-snug break-words max-w-[160px] ${isRoot ? 'text-[var(--bi-text-1)]' : 'text-[var(--bi-text-2)]'}`}>
                                            {node.label}
                                        </span>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>

                {/* Controles Flotantes del Lienzo (Esquina inferior derecha) */}
                <div className="absolute bottom-4 right-4 flex items-center gap-1 bg-[var(--bi-surface-0)] border border-[var(--bi-border)] rounded-lg p-1 shadow-md z-20 opacity-70 hover:opacity-100 transition-opacity">
                    <button
                        onClick={handleZoomIn}
                        className="p-1.5 hover:bg-[var(--bi-surface-1)] text-[var(--bi-text-2)] hover:text-[var(--bi-text-1)] rounded-md transition-all cursor-pointer"
                        title="Acercar (Zoom In)"
                    >
                        <ZoomIn className="w-4 h-4" />
                    </button>
                    <button
                        onClick={handleZoomOut}
                        className="p-1.5 hover:bg-[var(--bi-surface-1)] text-[var(--bi-text-2)] hover:text-[var(--bi-text-1)] rounded-md transition-all cursor-pointer"
                        title="Alejar (Zoom Out)"
                    >
                        <ZoomOut className="w-4 h-4" />
                    </button>
                    <button
                        onClick={handleReset}
                        className="p-1.5 hover:bg-[var(--bi-surface-1)] text-[var(--bi-text-2)] hover:text-[var(--bi-text-1)] rounded-md transition-all cursor-pointer"
                        title="Restablecer Lienzo"
                    >
                        <RefreshCw className="w-3.5 h-3.5" />
                    </button>
                    <div className="px-1.5 border-l border-[var(--bi-border)] text-[8px] font-bold text-[var(--bi-text-2)] uppercase tracking-wider">
                        {Math.round(scale * 100)}%
                    </div>
                </div>

                {/* Tooltip instructivo del Canvas (Esquina inferior izquierda) */}
                <div className="absolute bottom-4 left-4 bg-[var(--bi-surface-0)] border border-[var(--bi-border)] rounded-lg py-1 px-2.5 shadow-sm text-[8px] text-[var(--bi-text-3)] font-medium uppercase tracking-wider pointer-events-none select-none z-10">
                    💡 Doble clic para editar • Arrastrar para mover • Rueda para Zoom
                </div>
            </div>
        </div>
    );
}
