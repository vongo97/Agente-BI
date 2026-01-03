'use client';

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { useDashboard } from "@/context/DashboardContext";
import { getDashboard, deleteDashboardItem, exportChartAsPng } from "@/lib/api";
import { Activity, Trash2, Download, Box, Clock, MessageSquare, ExternalLink, Sparkles } from "lucide-react";
import dynamic from "next/dynamic";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false, loading: () => <div className="h-64 flex items-center justify-center bg-white/5 animate-pulse rounded-xl">Cargando gráfico...</div> });

export function DashboardView() {
    const { data: session } = useSession();
    const { setView } = useDashboard();
    const [items, setItems] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const userId = session?.user?.email || "default_user";

    useEffect(() => {
        fetchDashboard();
    }, [userId]);

    const fetchDashboard = async () => {
        setLoading(true);
        try {
            const data = await getDashboard(userId);
            setItems(data);
        } catch (error) {
            console.error("Error fetching dashboard:", error);
        } finally {
            setLoading(false);
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
        <div className="flex-1 bg-black flex flex-col h-screen overflow-hidden border-l border-white/5">
            <header className="h-16 border-b border-white/5 flex items-center justify-between px-8 bg-black/40 backdrop-blur-xl sticky top-0 z-10 w-full">
                <div className="flex items-center gap-4">
                    <div className="p-2 bg-blue-600/10 rounded-xl">
                        <Activity className="w-5 h-5 text-blue-500" />
                    </div>
                    <h2 className="text-sm font-black text-white uppercase tracking-[0.3em]">Panel de Control <span className="text-gray-600">| Curated Insights</span></h2>
                </div>

                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2 bg-blue-600/10 px-3 py-1.5 rounded-full border border-blue-600/20">
                        <Sparkles className="w-3 h-3 text-blue-500" />
                        <span className="text-[10px] font-bold text-blue-400 uppercase tracking-tighter">Business Intelligence Mode</span>
                    </div>
                </div>
            </header>

            <div className="flex-1 overflow-y-auto p-4 lg:p-8 custom-scrollbar">
                {items.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-center max-w-sm mx-auto">
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
                    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 pb-20">
                        {items.map((item) => (
                            <div key={item.id} className="bg-white/[0.02] border border-white/5 rounded-3xl overflow-hidden group hover:border-white/10 transition-all flex flex-col">
                                <div className="p-5 border-b border-white/5 flex items-center justify-between bg-white/[0.01]">
                                    <div className="flex items-center gap-4 overflow-hidden">
                                        <div className="p-2.5 bg-blue-600/20 rounded-xl hidden sm:block">
                                            <MessageSquare className="w-4 h-4 text-blue-400" />
                                        </div>
                                        <div className="overflow-hidden">
                                            <p className="text-[10px] text-gray-500 font-bold uppercase tracking-widest mb-0.5 truncate">{item.chat_title}</p>
                                            <p className="text-sm font-semibold text-white truncate max-w-[200px] sm:max-w-xs">{item.content}</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <button
                                            onClick={() => handleDownload(item.fig, item.content)}
                                            className="p-2 text-gray-500 hover:text-blue-400 hover:bg-blue-600/10 rounded-lg transition-all"
                                            title="Exportar como PNG"
                                        >
                                            <Download className="w-4 h-4" />
                                        </button>
                                        <button
                                            onClick={() => handleUnpin(item.id)}
                                            className="p-2 text-gray-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all"
                                            title="Remover del panel"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </div>
                                </div>

                                <div className="p-6 bg-black">
                                    {item.fig ? (
                                        <div className="w-full h-full min-h-[300px] flex items-center justify-center rounded-2xl overflow-hidden border border-white/5 bg-white/[0.01]">
                                            <Plot
                                                data={item.fig.data}
                                                layout={{
                                                    ...item.fig.layout,
                                                    autosize: true,
                                                    paper_bgcolor: 'rgba(0,0,0,0)',
                                                    plot_bgcolor: 'rgba(0,0,0,0)',
                                                    font: { color: '#888' },
                                                    margin: { t: 30, b: 30, l: 30, r: 30 },
                                                    xaxis: { ...item.fig.layout.xaxis, gridcolor: '#111', zerolinecolor: '#222' },
                                                    yaxis: { ...item.fig.layout.yaxis, gridcolor: '#111', zerolinecolor: '#222' }
                                                }}
                                                useResizeHandler={true}
                                                style={{ width: "100%", height: "100%", minHeight: "340px" }}
                                                config={{ responsive: true, displayModeBar: false }}
                                            />
                                        </div>
                                    ) : (
                                        <div className="h-64 flex items-center justify-center bg-white/[0.02] rounded-2xl border border-white/5">
                                            <p className="text-xs text-gray-600 font-black uppercase tracking-widest italic">Solo Tabla (Próximamente soporte visual)</p>
                                        </div>
                                    )}
                                </div>

                                <div className="px-6 py-4 bg-white/[0.01] border-t border-white/5 mt-auto flex items-center justify-between text-[10px] text-gray-600 font-bold uppercase tracking-widest">
                                    <div className="flex items-center gap-2">
                                        <Clock className="w-3.5 h-3.5" />
                                        <span>Anclado el {new Date(item.pinned_at).toLocaleDateString()}</span>
                                    </div>
                                    <span className="opacity-0 group-hover:opacity-100 transition-opacity text-blue-500">Curated by Gemini</span>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
