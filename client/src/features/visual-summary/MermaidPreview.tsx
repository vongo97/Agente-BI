'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useTheme } from '@/context/ThemeContext';
import { 
    Loader2, 
    AlertTriangle, 
    Check, 
    Copy, 
    ZoomIn, 
    ZoomOut, 
    RefreshCw, 
    Download, 
    Eye 
} from 'lucide-react';

interface MermaidPreviewProps {
    code: string;
}

export function MermaidPreview({ code }: MermaidPreviewProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const svgWrapperRef = useRef<HTMLDivElement>(null);
    const { theme } = useTheme();
    
    // Estados del renderizado
    const [svgContent, setSvgContent] = useState<string>('');
    const [error, setError] = useState<string | null>(null);
    const [rendering, setRendering] = useState<boolean>(false);
    const [copied, setCopied] = useState<boolean>(false);
    const [showExportMenu, setShowExportMenu] = useState<boolean>(false);

    // Estados para Zoom y Pan
    const [scale, setScale] = useState<number>(1);
    const [offset, setOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
    const [isDragging, setIsDragging] = useState<boolean>(false);
    const [dragStart, setDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
    
    // Generar un ID único para la renderización de Mermaid
    const renderId = useRef(`mermaid-${Math.floor(Math.random() * 1000000)}`);

    // Resetear zoom y posición cuando cambia el código
    useEffect(() => {
        setScale(1);
        setOffset({ x: 0, y: 0 });
    }, [code]);

    useEffect(() => {
        let isMounted = true;
        const renderDiagram = async () => {
            if (!code || !code.trim()) {
                setSvgContent('');
                setError(null);
                return;
            }

            setRendering(true);
            setError(null);

            try {
                // Importación dinámica de mermaid en el cliente
                const mermaid = (await import('mermaid')).default;
                
                // Configurar Mermaid basado en el tema 'base' para control total de colores
                const isDark = theme === 'dark';
                mermaid.initialize({
                    startOnLoad: false,
                    theme: 'base',
                    securityLevel: 'loose',
                    themeVariables: {
                        background: 'transparent',
                        primaryColor: isDark ? '#1e293b' : '#f1f5f9', // Fondo de nodos
                        primaryTextColor: isDark ? '#f3f4f6' : '#0f172a', // Texto
                        primaryBorderColor: isDark ? '#334155' : '#cbd5e1', // Bordes
                        lineColor: isDark ? '#475569' : '#94a3b8', // Conexiones
                        
                        // Variables específicas de Mindmap
                        mindmapNodeBkg: isDark ? '#1e293b' : '#f1f5f9',
                        mindmapTextColor: isDark ? '#f3f4f6' : '#0f172a',
                        mindmapLineColor: isDark ? '#475569' : '#94a3b8',
                        
                        // Variables de Flowchart
                        nodeBkg: isDark ? '#1e293b' : '#f1f5f9',
                        nodeBorder: isDark ? '#334155' : '#cbd5e1',
                        clusterBkg: isDark ? '#0f172a' : '#f8fafc',
                        clusterBorder: isDark ? '#334155' : '#cbd5e1',
                        defaultLinkColor: isDark ? '#475569' : '#94a3b8',
                        titleColor: isDark ? '#f3f4f6' : '#0f172a',
                        edgeLabelBackground: isDark ? '#0f172a' : '#ffffff',
                    }
                });

                // Limpiar contenedor previo
                if (containerRef.current) {
                    containerRef.current.innerHTML = '';
                }

                // Renderizar de forma asíncrona
                const { svg } = await mermaid.render(renderId.current, code);
                
                if (isMounted) {
                    // Adaptar el SVG para que sea responsivo y tome el 100%
                    let cleanSvg = svg;
                    cleanSvg = cleanSvg.replace(/width="[^"]+"/, 'width="100%"');
                    cleanSvg = cleanSvg.replace(/style="max-width:[^;]+;"/, 'style="max-width:100%;"');
                    
                    setSvgContent(cleanSvg);
                    setError(null);
                }
            } catch (err: unknown) {
                console.error("Error al renderizar diagrama Mermaid:", err);
                if (isMounted) {
                    setError("No se pudo compilar el diagrama. Verifica la sintaxis de Mermaid generada por la IA.");
                    setSvgContent('');
                }
            } finally {
                if (isMounted) {
                    setRendering(false);
                }
            }
        };

        // Pequeño de bounce para evitar doble renderizado reactivo inmediato
        const timer = setTimeout(() => {
            renderDiagram();
        }, 150);

        return () => {
            isMounted = false;
            clearTimeout(timer);
        };
    }, [code, theme]);

    // Copiar código Mermaid al portapapeles
    const handleCopyCode = async () => {
        try {
            await navigator.clipboard.writeText(code);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (err) {
            console.error("Fallo al copiar código", err);
        }
    };

    // --- Controles de Zoom y Pan ---
    const handleZoomIn = () => {
        setScale(s => Math.min(s * 1.2, 5));
    };

    const handleZoomOut = () => {
        setScale(s => Math.max(s / 1.2, 0.2));
    };

    const handleResetZoom = () => {
        setScale(1);
        setOffset({ x: 0, y: 0 });
    };

    const handleMouseDown = (e: React.MouseEvent) => {
        if (e.button !== 0 || error || !svgContent) return; // Solo arrastrar con click izquierdo y si hay diagrama
        setIsDragging(true);
        setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y });
    };

    const handleMouseMove = (e: React.MouseEvent) => {
        if (!isDragging) return;
        setOffset({
            x: e.clientX - dragStart.x,
            y: e.clientY - dragStart.y
        });
    };

    const handleMouseUpOrLeave = () => {
        setIsDragging(false);
    };

    const handleWheel = (e: React.WheelEvent) => {
        if (error || !svgContent) return;
        // Solo hacer zoom con la rueda si está sobre el área de dibujo
        e.preventDefault();
        const zoomFactor = 1.1;
        const newScale = e.deltaY < 0 ? scale * zoomFactor : scale / zoomFactor;
        setScale(Math.min(Math.max(newScale, 0.2), 5));
    };

    // --- Exportación a Archivos ---
    const handleDownloadSVG = () => {
        if (!svgContent) return;
        const blob = new Blob([svgContent], { type: 'image/svg+xml;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `vektra-diagrama-${Date.now()}.svg`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        setShowExportMenu(false);
    };

    const handleDownloadPNG = () => {
        if (!svgContent || !containerRef.current) return;
        const svgEl = containerRef.current.querySelector('svg');
        if (!svgEl) return;

        const clonedSvg = svgEl.cloneNode(true) as SVGElement;
        
        // Obtener tamaño proporcional del viewBox
        const viewBoxStr = clonedSvg.getAttribute('viewBox');
        let width = 800;
        let height = 600;
        if (viewBoxStr) {
            const parts = viewBoxStr.split(' ');
            if (parts.length === 4) {
                width = parseFloat(parts[2]);
                height = parseFloat(parts[3]);
            }
        } else {
            const bbox = svgEl.getBoundingClientRect();
            width = bbox.width || 800;
            height = bbox.height || 600;
        }

        // Definir dimensiones fijas para la imagen renderizada
        clonedSvg.setAttribute('width', `${width}px`);
        clonedSvg.setAttribute('height', `${height}px`);

        const svgString = new XMLSerializer().serializeToString(clonedSvg);
        const svgBlob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });
        const URL_OBJ = window.URL || window.webkitURL || window;
        const blobURL = URL_OBJ.createObjectURL(svgBlob);
        
        const image = new Image();
        image.onload = () => {
            const canvas = document.createElement('canvas');
            // Escala 2x para resolución Retina y alta densidad
            canvas.width = width * 2;
            canvas.height = height * 2;
            
            const context = canvas.getContext('2d');
            if (context) {
                // Rellenar fondo según el tema
                context.fillStyle = theme === 'dark' ? '#0d1117' : '#ffffff';
                context.fillRect(0, 0, canvas.width, canvas.height);
                
                // Dibujar a 2x
                context.scale(2, 2);
                context.drawImage(image, 0, 0, width, height);
                
                const pngURL = canvas.toDataURL('image/png');
                const downloadLink = document.createElement('a');
                downloadLink.href = pngURL;
                downloadLink.download = `vektra-diagrama-${Date.now()}.png`;
                document.body.appendChild(downloadLink);
                downloadLink.click();
                document.body.removeChild(downloadLink);
            }
            URL_OBJ.revokeObjectURL(blobURL);
        };
        image.src = blobURL;
        setShowExportMenu(false);
    };

    return (
        <div className="flex flex-col h-full bg-[var(--bi-surface-0)] border border-[var(--bi-border)] rounded-lg overflow-hidden shadow-sm relative group/mermaid">
            
            {/* Estilos CSS locales para resolver problemas de contraste y adaptar Mermaid al estilo premium de Vektra */}
            <style dangerouslySetInnerHTML={{ __html: `
                .mermaid-svg-container svg {
                    font-family: 'Inter', sans-serif !important;
                    background: transparent !important;
                }
                
                /* Tipografía Inter obligatoria */
                .mermaid-svg-container text,
                .mermaid-svg-container tspan,
                .mermaid-svg-container .label,
                .mermaid-svg-container span {
                    font-family: 'Inter', sans-serif !important;
                }
                
                /* Forzar contraste del texto en modo oscuro */
                [data-theme="dark"] .mermaid-svg-container text,
                [data-theme="dark"] .mermaid-svg-container tspan,
                [data-theme="dark"] .mermaid-svg-container .label text,
                [data-theme="dark"] .mermaid-svg-container .nodeText,
                [data-theme="dark"] .mermaid-svg-container .mindmap-node text {
                    fill: #f3f4f6 !important;
                    color: #f3f4f6 !important;
                }
                
                /* Forzar contraste del texto en modo claro */
                [data-theme="light"] .mermaid-svg-container text,
                [data-theme="light"] .mermaid-svg-container tspan,
                [data-theme="light"] .mermaid-svg-container .label text,
                [data-theme="light"] .mermaid-svg-container .nodeText,
                [data-theme="light"] .mermaid-svg-container .mindmap-node text {
                    fill: #0f172a !important;
                    color: #0f172a !important;
                }
                
                /* Corregir contraste específico del nodo central (depth-0) de Mindmaps */
                [data-theme="dark"] .mermaid-svg-container .mindmap-node.depth-0 text {
                    fill: #ffffff !important;
                }
                [data-theme="light"] .mermaid-svg-container .mindmap-node.depth-0 text {
                    fill: #000000 !important;
                }
                
                /* Bordes nítidos para nodos */
                .mermaid-svg-container .mindmap-node circle,
                .mermaid-svg-container .mindmap-node rect,
                .mermaid-svg-container .mindmap-node path,
                .mermaid-svg-container .node rect,
                .mermaid-svg-container .node circle,
                .mermaid-svg-container .node polygon {
                    stroke-width: 1.5px !important;
                    transition: fill 0.2s ease, stroke 0.2s ease;
                }
                
                /* Estilos sutiles y elegantes para nodos en modo oscuro */
                [data-theme="dark"] .mermaid-svg-container .mindmap-node.depth-1 rect,
                [data-theme="dark"] .mermaid-svg-container .mindmap-node.depth-1 circle,
                [data-theme="dark"] .mermaid-svg-container .mindmap-node.depth-2 rect,
                [data-theme="dark"] .mermaid-svg-container .mindmap-node.depth-2 circle,
                [data-theme="dark"] .mermaid-svg-container .node rect,
                [data-theme="dark"] .mermaid-svg-container .node circle,
                [data-theme="dark"] .mermaid-svg-container .node polygon {
                    fill: #1e293b !important;
                    stroke: #334155 !important;
                }
                
                [data-theme="dark"] .mermaid-svg-container .mindmap-node.depth-0 circle,
                [data-theme="dark"] .mermaid-svg-container .mindmap-node.depth-0 rect {
                    fill: #0f172a !important;
                    stroke: var(--bi-blue) !important;
                    stroke-width: 3px !important;
                }
                
                /* Estilos sutiles y elegantes para nodos en modo claro */
                [data-theme="light"] .mermaid-svg-container .mindmap-node.depth-1 rect,
                [data-theme="light"] .mermaid-svg-container .mindmap-node.depth-1 circle,
                [data-theme="light"] .mermaid-svg-container .mindmap-node.depth-2 rect,
                [data-theme="light"] .mermaid-svg-container .mindmap-node.depth-2 circle,
                [data-theme="light"] .mermaid-svg-container .node rect,
                [data-theme="light"] .mermaid-svg-container .node circle,
                [data-theme="light"] .mermaid-svg-container .node polygon {
                    fill: #f8fafc !important;
                    stroke: #cbd5e1 !important;
                }
                
                [data-theme="light"] .mermaid-svg-container .mindmap-node.depth-0 circle,
                [data-theme="light"] .mermaid-svg-container .mindmap-node.depth-0 rect {
                    fill: #ffffff !important;
                    stroke: var(--bi-blue) !important;
                    stroke-width: 3px !important;
                }
                
                /* Caminos de conexión (Aristas) */
                .mermaid-svg-container .mindmap-edge {
                    stroke: var(--bi-border) !important;
                    stroke-opacity: 0.8 !important;
                    stroke-width: 2px !important;
                }
                
                .mermaid-svg-container .edgePath .path {
                    stroke: var(--bi-border) !important;
                    stroke-width: 1.5px !important;
                }
            ` }} />

            {/* Cabecera del Diagrama */}
            <div className="flex justify-between items-center px-5 py-3 border-b border-[var(--bi-border)] bg-[var(--bi-surface-0)] z-10 shrink-0">
                <span className="text-[10px] font-bold text-[var(--bi-text-3)] uppercase tracking-wider flex items-center gap-1.5">
                    <Eye className="w-3.5 h-3.5 text-[var(--bi-blue)]" /> Diagrama Generado
                </span>
                
                <div className="flex items-center gap-2">
                    {/* Copiar código Mermaid */}
                    <button
                        onClick={handleCopyCode}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-[var(--bi-surface-1)] hover:bg-[var(--bi-surface-2)] text-[var(--bi-text-2)] hover:text-[var(--bi-text-1)] border border-[var(--bi-border)] rounded-md text-[10px] font-semibold uppercase tracking-wider transition-all cursor-pointer"
                        title="Copiar sintaxis de Mermaid"
                    >
                        {copied ? (
                            <>
                                <Check className="w-3.5 h-3.5 text-emerald-400" />
                                <span>Copiado</span>
                            </>
                        ) : (
                            <>
                                <Copy className="w-3.5 h-3.5" />
                                <span>Copiar código</span>
                            </>
                        )}
                    </button>

                    {/* Menú de exportación PNG/SVG */}
                    {svgContent && !error && (
                        <div className="relative">
                            <button
                                onClick={() => setShowExportMenu(!showExportMenu)}
                                className="flex items-center gap-1.5 px-3 py-1.5 bg-[var(--bi-blue)] hover:bg-[var(--bi-blue-hover)] text-[var(--bi-canvas)] rounded-md text-[10px] font-semibold uppercase tracking-wider transition-all cursor-pointer"
                            >
                                <Download className="w-3.5 h-3.5" />
                                <span>Exportar</span>
                            </button>
                            
                            {showExportMenu && (
                                <div className="absolute right-0 mt-1.5 w-36 bg-[var(--bi-surface-0)] border border-[var(--bi-border)] rounded-lg shadow-lg py-1.5 z-50 animate-in fade-in slide-in-from-top-1">
                                    <button
                                        onClick={handleDownloadPNG}
                                        className="w-full text-left px-4 py-2 text-[10px] font-medium text-[var(--bi-text-2)] hover:text-[var(--bi-text-1)] hover:bg-[var(--bi-surface-1)] transition-all cursor-pointer uppercase tracking-wider"
                                    >
                                        Descargar PNG
                                    </button>
                                    <button
                                        onClick={handleDownloadSVG}
                                        className="w-full text-left px-4 py-2 text-[10px] font-medium text-[var(--bi-text-2)] hover:text-[var(--bi-text-1)] hover:bg-[var(--bi-surface-1)] transition-all cursor-pointer uppercase tracking-wider"
                                    >
                                        Descargar SVG
                                    </button>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* Área de Visualización y Controles de Zoom/Pan */}
            <div 
                className="flex-1 min-h-[380px] bg-[var(--bi-canvas)] overflow-hidden relative select-none"
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUpOrLeave}
                onMouseLeave={handleMouseUpOrLeave}
                onWheel={handleWheel}
            >
                {/* Cargando */}
                {rendering && (
                    <div className="absolute inset-0 bg-[var(--bi-canvas)]/80 backdrop-blur-sm flex flex-col items-center justify-center gap-3 z-10">
                        <Loader2 className="w-8 h-8 text-[var(--bi-blue)] animate-spin" />
                        <span className="text-[10px] text-[var(--bi-text-3)] font-bold uppercase tracking-wider">Compilando Diagrama...</span>
                    </div>
                )}

                {/* Error de Sintaxis */}
                {error ? (
                    <div className="absolute inset-0 flex flex-col items-center justify-center text-center p-8 z-10 bg-[var(--bi-canvas)] overflow-y-auto">
                        <div className="p-3 bg-[var(--bi-red-dim)] border border-[var(--bi-red-border)]/20 rounded-lg mb-4 text-[var(--bi-red)]">
                            <AlertTriangle className="w-7 h-7" />
                        </div>
                        <div className="space-y-2 max-w-md">
                            <h4 className="text-xs font-bold text-[var(--bi-text-1)] uppercase tracking-wider">Error de Sintaxis</h4>
                            <p className="text-[11px] text-[var(--bi-text-2)] leading-relaxed">{error}</p>
                        </div>
                        <pre className="mt-4 text-[9px] font-mono bg-[var(--bi-surface-1)] border border-[var(--bi-border)] p-3 rounded-lg w-full max-w-md text-left overflow-x-auto text-[var(--bi-text-2)] max-h-32 custom-scrollbar">
                            {code}
                        </pre>
                    </div>
                ) : svgContent ? (
                    /* Visor del SVG con Zoom y Drag */
                    <div 
                        ref={svgWrapperRef}
                        className="mermaid-svg-container w-full h-full flex items-center justify-center p-6"
                    >
                        <div
                            style={{
                                transform: `translate(${offset.x}px, ${offset.y}px) scale(${scale})`,
                                transformOrigin: 'center center',
                                cursor: isDragging ? 'grabbing' : 'grab',
                                transition: isDragging ? 'none' : 'transform 0.1s ease-out',
                                width: '100%',
                                height: '100%',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center'
                            }}
                            dangerouslySetInnerHTML={{ __html: svgContent }}
                        />
                    </div>
                ) : (
                    <div className="absolute inset-0 flex items-center justify-center p-8">
                        <p className="text-[10px] text-[var(--bi-text-3)] uppercase font-semibold tracking-widest">Esperando diagrama para renderizar</p>
                    </div>
                )}

                {/* Barra de Herramientas Flotante (Zoom y Reset) */}
                {svgContent && !error && (
                    <div className="absolute bottom-4 right-4 flex items-center gap-1 bg-[var(--bi-surface-0)] border border-[var(--bi-border)] rounded-lg p-1 shadow-md z-10 opacity-70 hover:opacity-100 transition-opacity">
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
                            onClick={handleResetZoom}
                            className="p-1.5 hover:bg-[var(--bi-surface-1)] text-[var(--bi-text-2)] hover:text-[var(--bi-text-1)] rounded-md transition-all cursor-pointer"
                            title="Restablecer Escala (100%)"
                        >
                            <RefreshCw className="w-3.5 h-3.5" />
                        </button>
                        <div className="px-1.5 border-l border-[var(--bi-border)] text-[8px] font-bold text-[var(--bi-text-2)] uppercase tracking-wider">
                            {Math.round(scale * 100)}%
                        </div>
                    </div>
                )}
            </div>

            {/* Contenedor invisible para renderizar temporalmente y exportar a canvas */}
            <div ref={containerRef} className="hidden" />
        </div>
    );
}
