'use client';

import { useState, useEffect, useRef } from "react";
import { useSession } from "next-auth/react";
import { useDashboard } from "@/context/DashboardContext";
import { getDashboard, deleteDashboardItem, exportChartAsPng } from "@/lib/api";
import { Activity, Trash2, Download, Box, Sparkles, GripVertical } from "lucide-react";
import dynamic from "next/dynamic";
import { Responsive } from "react-grid-layout";

// Estilos de react-grid-layout
import "react-grid-layout/css/styles.css";
import "react-resizable/css/styles.css";

const Plot = dynamic(() => import("react-plotly.js"), {
    ssr: false,
    loading: () => <div className="h-64 flex items-center justify-center bg-white/5 animate-pulse rounded-xl">Cargando gráfico...</div>
}) as any;

export function DashboardView() {
    const { data: session } = useSession();
    const { setView } = useDashboard();
    const [items, setItems] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [layouts, setLayouts] = useState<any>({});
    const [width, setWidth] = useState(1200);
    const containerRef = useRef<HTMLDivElement>(null);
    const userId = session?.user?.email || "default_user";

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

    useEffect(() => {
        fetchDashboard();
    }, [userId]);

    const fetchDashboard = async () => {
        setLoading(true);
        try {
            const data = await getDashboard(userId);
            setItems(data);

            // Generar layout inicial
            const initialLayout = data.map((item: any, i: number) => ({
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
    };

    const onLayoutChange = (currentLayout: any, allLayouts: any) => {
        if (items.length > 0) {
            setLayouts(allLayouts);
            localStorage.setItem(`dashboard_layout_${userId}`, JSON.stringify(allLayouts));
        }
    };

    const handleUnpin = async (id: number) => {
        try {
            await deleteDashboardItem(id, userId);
            setItems(prev => prev.filter(item => item.id !== id));
        } catch (error) {
            alert("Error al eliminar del panel");
        }
    };

    const handleDownload = async (fig: any, name: string) => {
        try {
            const blob = await exportChartAsPng(fig);
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `bi_chart_${name.replace(/\s+/g, '_')}.png`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
        } catch (error) {
            alert("Error al exportar imagen");
        }
    };

    if (loading) {
        return (
            <div className="flex-1 bg-black flex flex-col items-center justify-center">
                <div className="p-4 bg-blue-600/20 rounded-2xl animate-spin mb-4">
                    <Activity className="w-8 h-8 text-blue-500" />
                </div>
                <p className="text-gray-400 font-bold uppercase tracking-[0.2em] animate-pulse">Cargando tu Panel de Control...</p>
            </div>
        );
    }

    return (
        <div className="flex-1 bg-[var(--bg-primary)] flex flex-col h-screen overflow-hidden border-l border-[var(--border-color)]">
            <header className="h-16 border-b border-white/5 flex items-center justify-between px-8 bg-black/40 backdrop-blur-xl sticky top-0 z-10 w-full shrink-0">
                <div className="flex items-center gap-4">
                    <div className="p-2 bg-blue-600/10 rounded-xl">
                        <Activity className="w-5 h-5 text-blue-500" />
                    </div>
                    <h2 className="text-sm font-black text-white uppercase tracking-[0.3em]">Panel Interactiva <span className="text-gray-600">| Pro-Dashboard</span></h2>
                </div>

                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2 bg-blue-600/10 px-3 py-1.5 rounded-full border border-blue-600/20">
                        <Sparkles className="w-3 h-3 text-blue-500" />
                        <span className="text-[10px] font-bold text-blue-400 uppercase tracking-tighter">Arrastra para reordenar</span>
                    </div>
                </div>
            </header>

            <div className="flex-1 relative bg-black">
                <div className="absolute inset-0" ref={containerRef}>
                    {items.length === 0 ? (
                        <div className="h-full flex flex-col items-center justify-center text-center max-w-sm mx-auto p-12">
                            <div className="w-20 h-20 bg-white/[0.02] border border-white/5 rounded-3xl flex items-center justify-center mb-6">
                                <Box className="w-10 h-10 text-gray-700" />
                            </div>
                            <h3 className="text-xl font-bold text-white mb-2">Tu panel está vacío</h3>
                            <p className="text-gray-500 text-sm leading-relaxed mb-6">Analiza datos en el chat y ancla los gráficos más importantes para verlos aquí todos juntos.</p>
                            <button
                                onClick={() => setView('chat')}
                                className="px-6 py-3 bg-blue-600 hover:bg-blue-500 rounded-xl text-white text-xs font-black uppercase tracking-widest transition-all"
                            >
                                Ir al Chat de Análisis
                            </button>
                        </div>
                    ) : (
                        width > 0 && (
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
                                } as any)}
                            >
                                {items.map((item) => (
                                    <div key={item.id.toString()} className="bg-[#0f0f0f] border border-white/5 rounded-3xl overflow-hidden group hover:border-blue-500/20 transition-all flex flex-col shadow-2xl">
                                        <div className="px-4 py-3 border-b border-white/5 flex items-center justify-between bg-white/[0.02]">
                                            <div className="flex items-center gap-3 overflow-hidden">
                                                <div className="drag-handle cursor-grab active:cursor-grabbing p-1.5 hover:bg-white/5 rounded-lg text-gray-600">
                                                    <GripVertical className="w-4 h-4" />
                                                </div>
                                                <div className="overflow-hidden">
                                                    <p className="text-[8px] text-gray-600 font-bold uppercase tracking-widest truncate">{item.chat_title}</p>
                                                    <p className="text-[11px] font-semibold text-gray-300 truncate">{item.content}</p>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-1 shrink-0">
                                                <button
                                                    onClick={() => handleDownload(item.fig, item.content)}
                                                    className="p-1.5 text-gray-600 hover:text-blue-400 hover:bg-blue-600/10 rounded-lg transition-all"
                                                    title="Exportar PNG"
                                                >
                                                    <Download className="w-3.5 h-3.5" />
                                                </button>
                                                <button
                                                    onClick={() => handleUnpin(item.id)}
                                                    className="p-1.5 text-gray-600 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all"
                                                    title="Remover"
                                                >
                                                    <Trash2 className="w-3.5 h-3.5" />
                                                </button>
                                            </div>
                                        </div>

                                        <div className="flex-1 p-2 bg-black/40 min-h-0 relative">
                                            {item.fig ? (
                                                <div className="w-full h-full flex items-center justify-center rounded-2xl overflow-hidden">
                                                    <Plot
                                                        data={item.fig.data}
                                                        layout={{
                                                            ...item.fig.layout,
                                                            autosize: true,
                                                            paper_bgcolor: 'rgba(0,0,0,0)',
                                                            plot_bgcolor: 'rgba(0,0,0,0)',
                                                            font: { color: '#888', size: 9 },
                                                            margin: { t: 20, b: 20, l: 30, r: 20 },
                                                            xaxis: { ...item.fig.layout.xaxis, gridcolor: '#111', zerolinecolor: '#222' },
                                                            yaxis: { ...item.fig.layout.yaxis, gridcolor: '#111', zerolinecolor: '#222' }
                                                        }}
                                                        useResizeHandler={true}
                                                        style={{ width: "100%", height: "100%" }}
                                                        config={{ responsive: true, displayModeBar: false }}
                                                    />
                                                </div>
                                            ) : (
                                                <div className="h-full flex items-center justify-center">
                                                    <p className="text-[10px] text-gray-700 font-bold uppercase tracking-widest italic">Solo Tabla</p>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </Responsive>
                        )
                    )}
                </div>
            </div>
        </div>
    );
}
