import React from 'react';
import dynamic from 'next/dynamic';
import { 
    LayoutDashboard, 
    AlertTriangle, 
    Pin, 
    Check, 
    TrendingUp, 
    Users, 
    DollarSign, 
    Activity, 
    PieChart, 
    BarChart, 
    Layers,
    ArrowUpRight,
    Search
} from 'lucide-react';
import { useState } from 'react';
import { pinCustomDashboardItem } from '@/lib/api';

const Plot = dynamic(() => import("react-plotly.js"), {
    ssr: false,
    loading: () => <div className="h-64 bg-[var(--bg-tertiary)] rounded-xl animate-pulse"></div>
});

// Mapeo de iconos comunes para métricas
const ICON_MAP: Record<string, any> = {
    'trending-up': TrendingUp,
    'users': Users,
    'dollar': DollarSign,
    'activity': Activity,
    'pie-chart': PieChart,
    'bar-chart': BarChart,
    'layers': Layers,
};

interface Metric {
    label: string;
    value: string | number;
    description?: string;
    icon?: string;
}

interface AutoDashItem {
    title: string;
    fig?: any;
    insight?: string;
    error?: string;
}

interface AutoDashGridProps {
    items: AutoDashItem[];
    metrics?: Metric[];
    userId: string;
}

export default function AutoDashGrid({ items, metrics = [], userId }: AutoDashGridProps) {
    const [pinnedIndices, setPinnedIndices] = useState<number[]>([]);

    const handlePin = async (item: AutoDashItem, idx: number) => {
        try {
            await pinCustomDashboardItem(userId, item);
            setPinnedIndices(prev => [...prev, idx]);
        } catch (error) {
            alert("Error al anclar ítem");
        }
    };

    const getIcon = (iconName?: string) => {
        const IconComponent = iconName ? ICON_MAP[iconName.toLowerCase()] : Activity;
        return IconComponent || Activity;
    };

    return (
        <div className="w-full mt-6 space-y-8 animate-in fade-in slide-in-from-bottom-6 duration-700">
            
            {/* SECCIÓN DE MÉTRICAS (KPIs) */}
            {metrics.length > 0 && (
                <div className="space-y-4">
                    <div className="flex items-center gap-2 px-1">
                        <div className="w-1 h-4 bg-[var(--bi-blue)] rounded-full"></div>
                        <h3 className="text-[10px] font-black text-[var(--text-tertiary)] uppercase tracking-[0.2em]">Métricas de Impacto</h3>
                    </div>
                    
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                        {metrics.map((metric, idx) => {
                            const Icon = getIcon(metric.icon);
                            return (
                                <div key={idx} className="relative group bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg p-5 hover:border-[var(--bi-blue-border)] transition-all overflow-hidden">
                                    <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                                        <Icon className="w-16 h-16" />
                                    </div>
                                    <div className="relative flex flex-col gap-3">
                                        <div className="flex items-center justify-between">
                                            <div className="p-2 bg-[var(--bi-blue-dim)] rounded-lg">
                                                <Icon className="w-5 h-5 text-[var(--bi-blue)]" />
                                            </div>
                                            <ArrowUpRight className="w-4 h-4 text-[var(--text-tertiary)] opacity-0 group-hover:opacity-100 transition-all translate-y-1 group-hover:translate-y-0" />
                                        </div>
                                        <div>
                                            <p className="text-[10px] font-bold text-[var(--text-tertiary)] uppercase tracking-wider mb-1">{metric.label}</p>
                                            <h4 className="text-2xl font-black text-[var(--text-primary)] tracking-tight">{metric.value}</h4>
                                        </div>
                                        {metric.description && (
                                            <p className="text-[10px] text-[var(--text-secondary)] leading-relaxed italic border-t border-[var(--border-color)] pt-3 mt-1">
                                                {metric.description}
                                            </p>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* SECCIÓN DE GRÁFICOS */}
            {items.length > 0 && (
                <div className="space-y-4">
                    <div className="flex items-center gap-2 px-1">
                        <div className="w-1 h-4 bg-[var(--bi-blue)] rounded-full"></div>
                        <h3 className="text-[10px] font-black text-[var(--text-tertiary)] uppercase tracking-[0.2em]">Análisis Visual</h3>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {items.map((item, idx) => (
                            <div key={idx} className="relative bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg overflow-hidden shadow-2xl p-4 flex flex-col hover:border-[var(--bi-blue-border)] transition-all group">
                                
                                <div className="absolute top-4 right-4 z-20 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <button
                                        onClick={() => handlePin(item, idx)}
                                        disabled={pinnedIndices.includes(idx)}
                                        className={`p-2 rounded-lg shadow-lg backdrop-blur-md border transition-all ${pinnedIndices.includes(idx)
                                                ? 'bg-green-500/20 border-green-500/30 text-green-400'
                                                : 'bg-white/10 hover:bg-white/20 border-white/10 text-white'
                                            }`}
                                        title="Anclar al Dashboard personal"
                                    >
                                        {pinnedIndices.includes(idx) ? <Check className="w-4 h-4" /> : <Pin className="w-4 h-4" />}
                                    </button>
                                </div>

                                <div className="mb-4 px-2 pr-12">
                                    <h4 className="font-bold text-sm text-[var(--text-primary)] tracking-tight truncate" title={item.title}>{item.title}</h4>
                                </div>

                                <div className="flex-1 min-h-[300px] relative rounded-lg overflow-hidden bg-[var(--bg-primary)]/50 border border-[var(--border-color)]/50">
                                    {item.fig ? (
                                        <Plot
                                            data={item.fig.data}
                                            layout={{
                                                ...item.fig.layout,
                                                width: undefined,
                                                height: undefined,
                                                autosize: true,
                                                paper_bgcolor: 'transparent',
                                                plot_bgcolor: 'transparent',
                                                font: { 
                                                    color: 'var(--text-tertiary)',
                                                    family: 'Inter, sans-serif'
                                                },
                                                margin: { l: 40, r: 20, t: 40, b: 40 },
                                                xaxis: { ...(item.fig.layout.xaxis || {}), gridcolor: 'var(--bi-border)' },
                                                yaxis: { ...(item.fig.layout.yaxis || {}), gridcolor: 'var(--bi-border)' },
                                            }}
                                            style={{ width: '100%', height: '100%' }}
                                            useResizeHandler={true}
                                            config={{ displayModeBar: false, responsive: true }}
                                        />
                                    ) : (
                                        <div className="absolute inset-0 flex items-center justify-center flex-col text-[var(--text-tertiary)] gap-3">
                                            <div className="w-12 h-12 bg-[var(--bg-tertiary)] rounded-lg flex items-center justify-center border border-[var(--border-color)]">
                                                <AlertTriangle className="w-6 h-6 opacity-40 text-orange-500" />
                                            </div>
                                            <span className="text-[10px] uppercase font-bold tracking-widest">{item.error || 'Fallo en renderizado'}</span>
                                        </div>
                                    )}
                                </div>

                                {item.insight && (
                                    <div className="mt-4 text-[11px] text-[var(--text-secondary)] bg-[var(--bi-blue-dim)] p-4 rounded-lg border border-[var(--bi-blue-border)] flex gap-3">
                                        <div className="mt-0.5">
                                            <Search className="w-3 h-3 text-[var(--bi-blue)] opacity-60" />
                                        </div>
                                        <p className="leading-relaxed italic">{item.insight}</p>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {items.length === 0 && metrics.length === 0 && (
                <div className="flex flex-col items-center justify-center py-20 text-center space-y-4">
                    <div className="w-16 h-16 bg-[var(--bg-secondary)] rounded-lg flex items-center justify-center border border-[var(--border-color)] shadow-inner">
                        <LayoutDashboard className="w-8 h-8 text-[var(--text-tertiary)] opacity-20" />
                    </div>
                    <p className="text-xs text-[var(--text-tertiary)] font-bold uppercase tracking-widest">No se pudieron extraer métricas automáticas</p>
                </div>
            )}
        </div>
    );
}
