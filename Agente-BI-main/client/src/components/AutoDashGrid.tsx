import React from 'react';
import dynamic from 'next/dynamic';
import { LayoutDashboard, AlertTriangle } from 'lucide-react';

const Plot = dynamic(() => import("react-plotly.js"), {
    ssr: false,
    loading: () => <div className="h-64 bg-[var(--bg-tertiary)] rounded-xl animate-pulse"></div>
});

interface AutoDashItem {
    title: string;
    fig?: any;
    insight?: string;
    error?: string;
}

interface AutoDashGridProps {
    items: AutoDashItem[];
    userId: string; // Nuevo prop necesario para pin
}

import { pinCustomDashboardItem } from '@/lib/api';
import { Pin, Check } from 'lucide-react';
import { useState } from 'react';

export default function AutoDashGrid({ items, userId }: AutoDashGridProps) {
    if (!items || items.length === 0) return null;

    // Estado local para trackear qué items han sido anclados visualmente
    const [pinnedIndices, setPinnedIndices] = useState<number[]>([]);

    const handlePin = async (item: AutoDashItem, idx: number) => {
        try {
            await pinCustomDashboardItem(userId, item);
            setPinnedIndices(prev => [...prev, idx]);
        } catch (error) {
            alert("Error al anclar ítem");
        }
    };

    return (
        <div className="w-full mt-4 space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex items-center gap-2 mb-2">
                <LayoutDashboard className="w-5 h-5 text-blue-500" />
                <h3 className="text-sm font-bold text-[var(--text-primary)] uppercase tracking-wider">Dashboard Generado Automáticamente</h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {items.map((item, idx) => (
                    <div key={idx} className="relative bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl overflow-hidden shadow-lg p-3 flex flex-col hover:border-blue-500/30 transition-colors group">

                        <div className="absolute top-2 right-2 z-20 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button
                                onClick={() => handlePin(item, idx)}
                                disabled={pinnedIndices.includes(idx)}
                                className={`p-1.5 rounded-lg shadow-sm backdrop-blur-md border transition-all ${pinnedIndices.includes(idx)
                                        ? 'bg-green-500/20 border-green-500/30 text-green-400'
                                        : 'bg-white/10 hover:bg-white/20 border-white/10 text-white'
                                    }`}
                                title="Anclar al Dashboard personal"
                            >
                                {pinnedIndices.includes(idx) ? <Check className="w-3.5 h-3.5" /> : <Pin className="w-3.5 h-3.5" />}
                            </button>
                        </div>

                        <div className="mb-2 px-1 pr-8">
                            <h4 className="font-semibold text-sm text-[var(--text-primary)] truncate" title={item.title}>{item.title}</h4>
                        </div>

                        <div className="flex-1 min-h-[250px] relative rounded-lg overflow-hidden bg-[var(--bg-primary)]">
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
                                        font: { color: 'var(--text-tertiary)' },
                                        margin: { l: 40, r: 20, t: 30, b: 40 },
                                    }}
                                    style={{ width: '100%', height: '100%' }}
                                    useResizeHandler={true}
                                    config={{ displayModeBar: false, responsive: true }}
                                />
                            ) : (
                                <div className="absolute inset-0 flex items-center justify-center flex-col text-[var(--text-tertiary)] gap-2">
                                    <AlertTriangle className="w-8 h-8 opacity-50" />
                                    <span className="text-xs">{item.error || 'No se pudo generar el gráfico'}</span>
                                </div>
                            )}
                        </div>

                        {item.insight && (
                            <div className="mt-3 text-xs text-[var(--text-secondary)] bg-[var(--bg-tertiary)]/50 p-2 rounded-lg border border-[var(--border-color)]">
                                {item.insight}
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}
