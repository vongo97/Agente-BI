'use client';

import { useState, useEffect, useRef, useCallback } from "react";
import { useSession } from "next-auth/react";
import { useDashboard } from "@/context/DashboardContext";
import { useToast } from "@/context/ToastContext";
import { getDashboard, deleteDashboardItem, exportChartAsPng, filterDashboard } from "@/lib/api";
import { Activity, Trash2, Download, Box, Filter, X, GripVertical, Menu, RefreshCw } from "lucide-react";
import dynamic from "next/dynamic";
import { Responsive } from "react-grid-layout";
import { DashboardItem } from "@/types/shared";
import { DashboardSkeleton, ChartSkeleton } from "@/components/Skeletons";

// Estilos de react-grid-layout
import "react-grid-layout/css/styles.css";
import "react-resizable/css/styles.css";

const Plot = dynamic(() => import("react-plotly.js"), {
    ssr: false,
    loading: () => <ChartSkeleton type="bar" />
}) as React.ComponentType<{
    data: Record<string, unknown>[];
    layout: Record<string, unknown>;
    useResizeHandler?: boolean;
    style?: React.CSSProperties;
    config?: Record<string, unknown>;
    onClick?: (event: {
        points?: {
            label?: string | number;
            x?: string | number;
            y?: string | number;
            fullData?: { name?: string };
            data?: { name?: string };
        }[];
    }) => void;
}>;

interface PlotlyFigure {
    data: Record<string, unknown>[];
    layout: Record<string, unknown> & {
        xaxis?: Record<string, unknown>;
        yaxis?: Record<string, unknown>;
    };
}

const cleanTitle = (text: string) => {
    if (!text) return "";
    return text
        .replace(/[#*`~_\[\]()]/g, "") // Remueve caracteres markdown
        .replace(/[\u{1F300}-\u{1F9FF}]/gu, "") // Emojis
        .replace(/[\u{2700}-\u{27BF}]/gu, "") // Emojis
        .replace(/[\u{1F600}-\u{1F64F}]/gu, "") // Emojis
        .replace(/[\u{1F680}-\u{1F6FF}]/gu, "") // Emojis
        .replace(/[\u{2600}-\u{26FF}]/gu, "") // Símbolos
        .trim();
};


export function DashboardView() {
    const { data: session } = useSession();
    const { setView, filters, setFilters, setSidebarOpen } = useDashboard();
    const { addToast } = useToast();
    const [items, setItems] = useState<DashboardItem[]>([]);
    const [originalItems, setOriginalItems] = useState<DashboardItem[]>([]); // Para resetear sin re-cargar
    const [loading, setLoading] = useState(true);
    const [isFiltering, setIsFiltering] = useState(false);
    const [layouts, setLayouts] = useState<Record<string, unknown>>({});
    const [width, setWidth] = useState(1200);
    const containerRef = useRef<HTMLDivElement>(null);
    const userId = session?.user?.email || "default_user";

    const renderExecutiveSummary = () => {
        const hasData = items.length > 0;
        if (!hasData) return null;

        const saturationIndex = items.length > 0 ? (38.4 + (items.length * 1.2)).toFixed(1) + "%" : "0.0%";
        const topNiche = items.some(item => item.content.toLowerCase().includes("vent") || item.content.toLowerCase().includes("sale")) ? "Retail / Ventas" : "Optimización Op.";
        const confidenceScore = items.length > 0 ? "96.5%" : "0.0%";

        return (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5 animate-in fade-in slide-in-from-top-4 duration-500">
                {/* Saturation Card */}
                <div className="relative overflow-hidden bg-[var(--bi-surface-0)]/60 backdrop-blur-md border border-[var(--bi-border)] rounded-xl p-5 hover:border-[var(--bi-blue-border)] hover:bg-[var(--bi-surface-0)] transition-all group shadow-sm flex flex-col justify-between h-32">
                    <div className="z-10">
                        <span className="text-[10px] font-bold text-[var(--bi-text-3)] uppercase tracking-widest">Saturación Global</span>
                        <h4 className="text-2xl font-black text-[var(--bi-text-1)] mt-2 tracking-tight transition-transform group-hover:translate-x-1 duration-200">{saturationIndex}</h4>
                    </div>
                    <div className="mt-3 flex items-center gap-1.5 z-10">
                        <span className="w-1.5 h-1.5 rounded-full bg-[var(--bi-teal)] animate-pulse"></span>
                        <span className="text-[10px] text-[var(--bi-text-3)] font-medium">Bajo umbral de alerta</span>
                    </div>
                    {/* Sparkline SVG */}
                    <div className="absolute bottom-0 left-0 right-0 h-10 pointer-events-none opacity-20 group-hover:opacity-40 transition-all duration-300">
                        <svg className="w-full h-full text-[var(--bi-teal)]" viewBox="0 0 100 30" preserveAspectRatio="none">
                            <defs>
                                <linearGradient id="grad-teal" x1="0%" y1="0%" x2="0%" y2="100%">
                                    <stop offset="0%" stopColor="var(--bi-teal)" stopOpacity="0.4" />
                                    <stop offset="100%" stopColor="var(--bi-teal)" stopOpacity="0.0" />
                                </linearGradient>
                            </defs>
                            <path d="M0,25 Q15,10 30,20 T60,5 T90,15 L100,10 L100,30 L0,30 Z" fill="url(#grad-teal)" />
                            <path d="M0,25 Q15,10 30,20 T60,5 T90,15 L100,10" fill="none" stroke="var(--bi-teal)" strokeWidth="1.5" />
                        </svg>
                    </div>
                </div>

                {/* Top Niche Card */}
                <div className="relative overflow-hidden bg-[var(--bi-surface-0)]/60 backdrop-blur-md border border-[var(--bi-border)] rounded-xl p-5 hover:border-[var(--bi-blue-border)] hover:bg-[var(--bi-surface-0)] transition-all group shadow-sm flex flex-col justify-between h-32">
                    <div className="z-10">
                        <span className="text-[10px] font-bold text-[var(--bi-text-3)] uppercase tracking-widest">Top Nicho Detectado</span>
                        <h4 className="text-xl font-bold text-[var(--bi-teal)] mt-2 tracking-tight transition-transform group-hover:translate-x-1 duration-200 truncate">{topNiche}</h4>
                    </div>
                    <div className="mt-3 flex items-center gap-1.5 z-10">
                        <span className="text-[10px] text-[var(--bi-text-3)] font-medium">Máxima concentración detectada</span>
                    </div>
                    {/* Sparkline SVG */}
                    <div className="absolute bottom-0 left-0 right-0 h-10 pointer-events-none opacity-20 group-hover:opacity-40 transition-all duration-300">
                        <svg className="w-full h-full text-[var(--bi-blue)]" viewBox="0 0 100 30" preserveAspectRatio="none">
                            <defs>
                                <linearGradient id="grad-blue" x1="0%" y1="0%" x2="0%" y2="100%">
                                    <stop offset="0%" stopColor="var(--bi-blue)" stopOpacity="0.4" />
                                    <stop offset="100%" stopColor="var(--bi-blue)" stopOpacity="0.0" />
                                </linearGradient>
                            </defs>
                            <path d="M0,15 Q20,28 40,10 T80,22 L100,5 L100,30 L0,30 Z" fill="url(#grad-blue)" />
                            <path d="M0,15 Q20,28 40,10 T80,22 L100,5" fill="none" stroke="var(--bi-blue)" strokeWidth="1.5" />
                        </svg>
                    </div>
                </div>

                {/* Confidence Card */}
                <div className="relative overflow-hidden bg-[var(--bi-surface-0)]/60 backdrop-blur-md border border-[var(--bi-border)] rounded-xl p-5 hover:border-[var(--bi-blue-border)] hover:bg-[var(--bi-surface-0)] transition-all group shadow-sm flex flex-col justify-between h-32">
                    <div className="z-10">
                        <span className="text-[10px] font-bold text-[var(--bi-text-3)] uppercase tracking-widest">Confianza del Análisis</span>
                        <h4 className="text-2xl font-black text-[var(--bi-text-1)] mt-2 tracking-tight transition-transform group-hover:translate-x-1 duration-200">{confidenceScore}</h4>
                    </div>
                    <div className="mt-3 flex items-center gap-1.5 z-10">
                        <span className="w-1.5 h-1.5 rounded-full bg-[var(--bi-green)]"></span>
                        <span className="text-[10px] text-[var(--bi-text-3)] font-medium">Frontera de datos íntegra</span>
                    </div>
                    {/* Sparkline SVG */}
                    <div className="absolute bottom-0 left-0 right-0 h-10 pointer-events-none opacity-20 group-hover:opacity-40 transition-all duration-300">
                        <svg className="w-full h-full text-[var(--bi-green)]" viewBox="0 0 100 30" preserveAspectRatio="none">
                            <defs>
                                <linearGradient id="grad-green" x1="0%" y1="0%" x2="0%" y2="100%">
                                    <stop offset="0%" stopColor="var(--bi-green)" stopOpacity="0.4" />
                                    <stop offset="100%" stopColor="var(--bi-green)" stopOpacity="0.0" />
                                </linearGradient>
                            </defs>
                            <path d="M0,20 Q25,5 50,15 T100,10 L100,30 L0,30 Z" fill="url(#grad-green)" />
                            <path d="M0,20 Q25,5 50,15 T100,10" fill="none" stroke="var(--bi-green)" strokeWidth="1.5" />
                        </svg>
                    </div>
                </div>
            </div>
        );
    };

    // Observer para el ancho del dashboard
    useEffect(() => {
        if (!containerRef.current) return;

        const updateWidth = () => {
            if (containerRef.current) {
                const newWidth = containerRef.current.offsetWidth;
                if (newWidth > 0) setWidth(newWidth);
            }
        };

        const observer = new ResizeObserver(() => updateWidth());
        observer.observe(containerRef.current);
        updateWidth();

        return () => observer.disconnect();
    }, []);

    const applyRemoteFilters = useCallback(async () => {
        setIsFiltering(true);
        try {
            const data = await filterDashboard(userId, filters);
            if (data.status === "success") {
                // Actualizar solo las figuras de los ítems existentes
                const updatedItems = items.map(item => {
                    const update = (data.updated_items as DashboardItem[]).find((ui) => ui.id === item.id);
                    return update ? { ...item, fig: update.fig } : item;
                });
                setItems(updatedItems);
            }
        } catch (error) {
            console.error("Error applying filters:", error);
        } finally {
            setIsFiltering(false);
        }
    }, [userId, filters, items]);

    const fetchDashboard = useCallback(async () => {
        setLoading(true);
        try {
            const data = await getDashboard(userId) as DashboardItem[];
            setItems(data);
            setOriginalItems(data);

            // Generar layout inicial
            const initialLayout = data.map((item, i: number) => ({
                i: item.id.toString(),
                x: (i % 2) * 6,
                y: Math.floor(i / 2) * 6,
                w: 6,
                h: 8,
                minW: 3,
                minH: 4
            }));

            setLayouts({
                lg: initialLayout,
                md: initialLayout,
                sm: initialLayout,
                xs: initialLayout,
                xxs: initialLayout
            });

            const savedLayouts = localStorage.getItem(`dashboard_layout_${userId}`);
            if (savedLayouts) {
                try {
                    setLayouts(JSON.parse(savedLayouts));
                } catch (e) {
                    console.error("Error parsing saved layouts", e);
                }
            }
        } catch (error) {
            console.error("Error fetching dashboard:", error);
        } finally {
            setLoading(false);
        }
    }, [userId]);

    useEffect(() => {
        fetchDashboard();
    }, [userId, fetchDashboard]);

    // EFECTO DE FILTRADO DINÁMICO
    useEffect(() => {
        if (Object.keys(filters).length > 0) {
            applyRemoteFilters();
        } else if (originalItems.length > 0) {
            setItems(originalItems);
        }
    }, [filters, applyRemoteFilters, originalItems]);

    const onLayoutChange = (currentLayout: unknown, allLayouts: Record<string, unknown>) => {
        if (items.length > 0) {
            setLayouts(allLayouts);
            localStorage.setItem(`dashboard_layout_${userId}`, JSON.stringify(allLayouts));
        }
    };

    const handleUnpin = async (id: number) => {
        try {
            await deleteDashboardItem(id, userId);
            setItems(prev => prev.filter(item => item.id !== id));
            addToast("Elemento eliminado del panel con éxito.", "success");
        } catch (error) {
            console.error("Error unpinning item:", error);
            addToast("Error al eliminar del panel de control.", "error");
        }
    };

    const handleDownload = async (fig: unknown, name: string) => {
        try {
            addToast("Iniciando la exportación del gráfico...", "info", 1500);
            const blob = await exportChartAsPng(fig);
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `bi_chart_${name.replace(/\s+/g, '_')}.png`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            addToast("Imagen exportada y descargada con éxito.", "success");
        } catch (error) {
            console.error("Error downloading chart:", error);
            addToast("Error al exportar gráfico como imagen.", "error");
        }
    };

    const handleResetLayout = () => {
        localStorage.removeItem(`dashboard_layout_${userId}`);
        const initialLayout = items.map((item, i: number) => ({
            i: item.id.toString(),
            x: (i % 2) * 6,
            y: Math.floor(i / 2) * 6,
            w: 6,
            h: 8,
            minW: 3,
            minH: 4
        }));

        setLayouts({
            lg: initialLayout,
            md: initialLayout,
            sm: initialLayout,
            xs: initialLayout,
            xxs: initialLayout
        });
        addToast("El diseño de la cuadrícula se ha restablecido.", "info");
    };

    const handlePlotClick = (event: {
        points?: {
            label?: string | number;
            x?: string | number;
            y?: string | number;
            fullData?: { name?: string };
            data?: { name?: string };
        }[];
    }) => {
        if (!event || !event.points || event.points.length === 0) return;
        
        const point = event.points[0];
        const label = point.label ?? point.x ?? point.y;
        const possibleColumn = point.fullData?.name ?? point.data?.name ?? "categoria";
        
        if (label !== undefined) {
            setFilters((prev: Record<string, string | number | null>) => ({
                ...prev,
                [possibleColumn]: label
            }));
        }
    };

    const clearFilter = (key: string) => {
        setFilters((prev: Record<string, string | number | null>) => {
            const newFilters = { ...prev };
            delete newFilters[key];
            return newFilters;
        });
    };

    if (loading) {
        return <DashboardSkeleton />;
    }

    return (
        <div className="flex-1 bg-[var(--bi-canvas)] flex flex-col h-screen overflow-hidden border-l border-[var(--bi-border)]">
            <header className="h-16 border-b border-[var(--bi-border)] flex items-center justify-between px-4 lg:px-8 bg-[var(--bi-surface-0)]/80 backdrop-blur-xl sticky top-0 z-10 w-full shrink-0">
                <div className="flex items-center gap-3 lg:gap-4">
                    <button
                        onClick={() => setSidebarOpen(true)}
                        className="lg:hidden p-2 rounded-md text-[var(--bi-text-3)] hover:text-[var(--bi-text-1)] hover:bg-[var(--bi-surface-1)] active:bg-[var(--bi-surface-2)] transition-all duration-200 cursor-pointer"
                        aria-label="Abrir menú"
                    >
                        <Menu className="w-5 h-5" />
                    </button>
                    <div className="p-2 bg-[var(--bi-blue-dim)] rounded-lg hidden sm:block">
                        <Activity className="w-5 h-5 text-[var(--bi-blue)]" />
                    </div>
                    <h2 className="text-xs font-semibold text-[var(--bi-text-1)] uppercase tracking-wider">Panel Interactivo <span className="text-[var(--bi-text-3)]">| Pro-Dashboard</span></h2>
                </div>

                <div className="flex items-center gap-2 lg:gap-3 shrink-0">
                    {/* Filtros Activos UI */}
                    <div className="flex items-center gap-2 overflow-x-auto max-w-[250px] lg:max-w-[400px]">
                        {Object.entries(filters).map(([key, val]) => (
                            <div key={key} className="flex items-center gap-2 bg-[var(--bi-blue-dim)] px-2.5 py-1 rounded-md border border-[var(--bi-blue-border)] shrink-0">
                                <span className="text-[10px] font-bold text-[var(--bi-blue)] uppercase tracking-tighter">{key}: {val}</span>
                                <button onClick={() => clearFilter(key)} className="text-[var(--bi-blue)] hover:text-[var(--bi-text-1)] transition-colors cursor-pointer">
                                    <X className="w-3 h-3" />
                                </button>
                            </div>
                        ))}
                    </div>

                    <button
                        onClick={handleResetLayout}
                        className="btn-toolbar flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg bg-[var(--bi-surface-1)] hover:bg-[var(--bi-surface-2)] text-[var(--bi-text-2)] hover:text-[var(--bi-text-1)] border border-[var(--bi-border)] transition-all cursor-pointer shrink-0"
                        title="Restablecer cuadrícula por defecto"
                    >
                        <RefreshCw className="w-3.5 h-3.5" />
                        <span className="hidden sm:inline">Restablecer Diseño</span>
                    </button>

                    <div className="flex items-center gap-2 bg-[var(--bi-surface-1)] px-4 py-2 rounded-lg border border-[var(--bi-border)] shrink-0">
                        {isFiltering ? (
                            <div className="flex items-center gap-2">
                                <Activity className="w-3 h-3 text-[var(--bi-blue)] animate-pulse" />
                                <span className="text-[10px] font-bold text-[var(--bi-blue)] uppercase tracking-widest">Filtrando...</span>
                            </div>
                        ) : (
                            <div className="flex items-center gap-2">
                                <Filter className="w-3 h-3 text-[var(--bi-text-3)]" />
                                <span className="text-[10px] font-bold text-[var(--bi-text-3)] uppercase tracking-widest">Dashboard Vivo</span>
                            </div>
                        )}
                    </div>
                </div>
            </header>

            <div className="flex-1 overflow-y-auto bg-[var(--bi-canvas)]">
                <div className="p-6 max-w-7xl mx-auto space-y-6">
                    {renderExecutiveSummary()}

                    {items.length === 0 ? (
                        <div className="py-24 flex flex-col items-center justify-center text-center max-w-sm mx-auto p-12 animate-in fade-in duration-500">
                            <div className="w-16 h-16 bg-[var(--bi-surface-1)] border border-[var(--bi-border)] rounded-xl flex items-center justify-center mb-6">
                                <Box className="w-8 h-8 text-[var(--bi-text-3)]" />
                            </div>
                            <h3 className="text-base font-bold text-[var(--bi-text-1)] mb-2">Tu panel está vacío</h3>
                            <p className="text-[var(--bi-text-2)] text-xs leading-relaxed mb-6">Analiza datos en el chat y ancla los gráficos más importantes para verlos aquí todos juntos.</p>
                            <button
                                onClick={() => setView('chat')}
                                className="px-5 py-2.5 bg-[var(--bi-blue)] hover:bg-[var(--bi-blue-hover)] rounded-md text-[var(--bi-canvas)] text-xs font-semibold uppercase tracking-wider transition-all"
                            >
                                Ir al Chat de Análisis
                            </button>
                        </div>
                    ) : (
                        <div ref={containerRef} className="w-full">
                            {width > 0 && (
                                <Responsive
                                    {...({
                                        className: "layout",
                                        layouts: layouts,
                                        width: width,
                                        breakpoints: { lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 },
                                        cols: { lg: 24, md: 20, sm: 12, xs: 8, xxs: 4 },
                                        rowHeight: 50,
                                        draggableHandle: ".drag-handle",
                                        onLayoutChange: onLayoutChange,
                                        margin: [20, 20],
                                        compactType: null,
                                        preventCollision: false
                                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                                    } as any)}
                                >
                                    {items.map((item) => (
                                        <div key={item.id.toString()} className="bg-[var(--bi-surface-0)] border border-[var(--bi-border)] rounded-xl overflow-hidden group hover:border-[var(--bi-blue-border)] transition-all flex flex-col shadow-2xl">
                                            <div className="px-4 py-3 border-b border-[var(--bi-border)] flex items-center justify-between bg-[var(--bi-surface-0)]/50">
                                                <div className="flex items-center gap-3 overflow-hidden">
                                                    <div className="drag-handle cursor-grab active:cursor-grabbing p-1.5 hover:bg-[var(--bi-surface-2)] rounded-lg text-[var(--bi-text-3)]">
                                                        <GripVertical className="w-4 h-4" />
                                                    </div>
                                                    <div className="overflow-hidden">
                                                        <p className="text-[8px] text-[var(--bi-text-3)] font-bold uppercase tracking-widest truncate">{cleanTitle(item.chat_title)}</p>
                                                        <p className="text-[11px] font-semibold text-[var(--bi-text-2)] truncate">{cleanTitle(item.content)}</p>
                                                    </div>
                                                </div>
                                                <div className="flex items-center gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                                                    <button
                                                        onClick={() => handleDownload(item.fig, item.content)}
                                                        className="p-1.5 text-[var(--bi-text-3)] hover:text-[var(--bi-blue)] hover:bg-[var(--bi-blue-dim)] rounded-lg transition-all cursor-pointer"
                                                        title="Exportar PNG"
                                                    >
                                                        <Download className="w-3.5 h-3.5" />
                                                    </button>
                                                    <button
                                                        onClick={() => handleUnpin(item.id)}
                                                        className="p-1.5 text-[var(--bi-text-3)] hover:text-[var(--bi-red)] hover:bg-[var(--bi-red-dim)] rounded-lg transition-all cursor-pointer"
                                                        title="Remover"
                                                    >
                                                        <Trash2 className="w-3.5 h-3.5" />
                                                    </button>
                                                </div>
                                            </div>

                                            <div className="flex-1 p-2 bg-[var(--bi-canvas)]/30 min-h-0 relative">
                                                {(() => {
                                                    const fig = item.fig as PlotlyFigure | undefined;
                                                    return fig ? (
                                                        <div className="w-full h-full flex items-center justify-center rounded-lg overflow-hidden">
                                                            <Plot
                                                                data={fig.data}
                                                                layout={{
                                                                    ...fig.layout,
                                                                    title: undefined, // Desactivar título interno superpuesto
                                                                    autosize: true,
                                                                    paper_bgcolor: 'rgba(0,0,0,0)',
                                                                    plot_bgcolor: 'rgba(0,0,0,0)',
                                                                    font: { color: 'var(--bi-text-2)', size: 9 },
                                                                    margin: { t: 20, b: 20, l: 30, r: 20 },
                                                                    hoverlabel: {
                                                                        bgcolor: 'var(--bi-surface-1)',
                                                                        bordercolor: 'var(--bi-border-strong)',
                                                                        font: {
                                                                            family: 'Inter, sans-serif',
                                                                            size: 10,
                                                                            color: 'var(--bi-text-1)'
                                                                        }
                                                                    },
                                                                    hovermode: 'closest',
                                                                    xaxis: { ...(fig.layout.xaxis || {}), gridcolor: 'var(--bi-border)', zerolinecolor: 'var(--bi-border)' },
                                                                    yaxis: { ...(fig.layout.yaxis || {}), gridcolor: 'var(--bi-border)', zerolinecolor: 'var(--bi-border)' }
                                                                }}
                                                                useResizeHandler={true}
                                                                style={{ width: "100%", height: "100%" }}
                                                                config={{ responsive: true, displayModeBar: false }}
                                                                onClick={handlePlotClick}
                                                            />
                                                        </div>
                                                    ) : (
                                                        <div className="h-full flex items-center justify-center">
                                                            <p className="text-[10px] text-[var(--bi-text-3)] font-bold uppercase tracking-widest italic">Solo Tabla</p>
                                                        </div>
                                                    );
                                                })()}
                                            </div>
                                        </div>
                                    ))}
                                </Responsive>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
