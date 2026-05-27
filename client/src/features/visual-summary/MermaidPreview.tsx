'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Loader2, AlertTriangle, Check, Copy } from 'lucide-react';

interface MermaidPreviewProps {
    code: string;
}

export function MermaidPreview({ code }: MermaidPreviewProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const [svgContent, setSvgContent] = useState<string>('');
    const [error, setError] = useState<string | null>(null);
    const [rendering, setRendering] = useState<boolean>(false);
    const [copied, setCopied] = useState<boolean>(false);
    
    // Generar un ID único para la renderización de Mermaid
    const renderId = useRef(`mermaid-${Math.floor(Math.random() * 1000000)}`);

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
                
                // Configurar Mermaid
                mermaid.initialize({
                    startOnLoad: false,
                    theme: 'dark', // Podemos cambiarlo según el tema actual
                    securityLevel: 'loose',
                    themeVariables: {
                        background: '#0d1117',
                        primaryColor: '#1f6feb',
                        primaryTextColor: '#c9d1d9',
                        lineColor: '#30363d',
                    }
                });

                // Limpiar contenedor previo
                if (containerRef.current) {
                    containerRef.current.innerHTML = '';
                }

                // Renderizar de forma asíncrona
                const { svg } = await mermaid.render(renderId.current, code);
                
                if (isMounted) {
                    setSvgContent(svg);
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

        // Pequeño debounce para evitar doble renderizado reactivo inmediato
        const timer = setTimeout(() => {
            renderDiagram();
        }, 150);

        return () => {
            isMounted = false;
            clearTimeout(timer);
        };
    }, [code]);

    const handleCopyCode = async () => {
        try {
            await navigator.clipboard.writeText(code);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (err) {
            console.error("Fallo al copiar código", err);
        }
    };

    return (
        <div className="flex flex-col h-full bg-[var(--bg-tertiary)] border border-[var(--border-color)] rounded-3xl overflow-hidden shadow-2xl relative">
            <div className="flex justify-between items-center px-6 py-4 border-b border-[var(--border-color)] bg-black/10">
                <span className="text-xs font-black text-blue-400 uppercase tracking-widest">Diagrama Generado</span>
                <button
                    onClick={handleCopyCode}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-white/5 hover:bg-white/10 text-gray-300 hover:text-white rounded-xl text-[10px] font-black uppercase tracking-wider transition-all"
                >
                    {copied ? (
                        <>
                            <Check className="w-3.5 h-3.5 text-emerald-400" />
                            <span>Copiado</span>
                        </>
                    ) : (
                        <>
                            <Copy className="w-3.5 h-3.5" />
                            <span>Copiar Mermaid</span>
                        </>
                    )}
                </button>
            </div>

            <div className="flex-1 p-6 flex items-center justify-center min-h-[350px] overflow-auto custom-scrollbar relative">
                {rendering && (
                    <div className="absolute inset-0 bg-[var(--bg-tertiary)]/80 backdrop-blur-sm flex flex-col items-center justify-center gap-3 z-10">
                        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
                        <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Compilando Diagrama...</span>
                    </div>
                )}

                {error ? (
                    <div className="flex flex-col items-center justify-center text-center p-8 max-w-md gap-4 animate-in fade-in">
                        <div className="p-3 bg-amber-500/10 rounded-2xl">
                            <AlertTriangle className="w-8 h-8 text-amber-400" />
                        </div>
                        <div className="space-y-2">
                            <h4 className="text-sm font-bold text-white uppercase tracking-wider">Error de Sintaxis</h4>
                            <p className="text-xs text-gray-400 leading-relaxed">{error}</p>
                        </div>
                        <pre className="text-[9px] bg-black/30 border border-white/5 p-3 rounded-lg w-full text-left overflow-x-auto text-amber-300 max-h-32 custom-scrollbar">
                            {code}
                        </pre>
                    </div>
                ) : svgContent ? (
                    <div 
                        className="w-full flex justify-center items-center select-none"
                        dangerouslySetInnerHTML={{ __html: svgContent }} 
                    />
                ) : (
                    <div className="text-center p-8">
                        <p className="text-xs text-gray-500 uppercase font-black tracking-widest">Esperando diagrama para renderizar</p>
                    </div>
                )}
            </div>

            {/* Contenedor invisible de respaldo para renderizado de Mermaid */}
            <div ref={containerRef} className="hidden" />
        </div>
    );
}
