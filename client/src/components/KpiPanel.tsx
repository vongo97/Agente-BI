'use client';

import { useEffect, useState } from "react";
import { getKpiSummary, KpiData } from "@/lib/api";
import KpiCards from "@/components/KpiCards";
import AnomalyAlert from "@/components/AnomalyAlert";
import { useToast } from "@/context/ToastContext";

/**
 * P-23: panel de perfilado del dataset (KPICards + AnomalyAlert).
 *
 * Antes, `KpiCards`, `AnomalyAlert` y el endpoint `/report/kpi-summary` estaban
 * implementados pero nunca conectados: el router no se montaba en `main.py` y
 * los componentes no se importaban en ninguna parte. Ahora el panel se pide al
 * backend para la fuente principal y se pinta con datos reales — nada de
 * números inventados en la UI.
 */
export function KpiPanel({ dataSourceId }: { dataSourceId?: number }) {
    const { addToast } = useToast();
    // Un único estado para los datos **y** su estado de carga, etiquetado con
    // el `dataSourceId` del que proceden. Así el render puede descartar datos
    // obsoletos y derivar `loading` sin escribir estado desde el efecto
    // (regla del linter `react-hooks/set-state-in-effect` y, más importante,
    // regla 10 del registro: nada de efectos que se autoalimentan).
    const [state, setState] = useState<{
        dataSourceId: number;
        data: KpiData | null;
        loading: boolean;
    } | null>(null);

    useEffect(() => {
        if (!dataSourceId) return;

        let cancelled = false;
        getKpiSummary(dataSourceId)
            .then((data) => {
                if (!cancelled) setState({ dataSourceId, data, loading: false });
            })
            .catch((err) => {
                if (cancelled) return;
                console.error("Error cargando el resumen de KPIs:", err);
                setState({ dataSourceId, data: null, loading: false });
                addToast(
                    "No se pudo cargar el perfilado del dataset: " +
                    ((err as Error).message || "Error desconocido"),
                    "warning",
                );
            });

        return () => { cancelled = true; };
    }, [dataSourceId, addToast]);

    // Los datos (y el estado de carga) solo son válidos si pertenecen a la
    // fuente que se está mostrando ahora mismo.
    const current = state?.dataSourceId === dataSourceId ? state : null;
    const kpiData = current?.data ?? null;
    // Mientras no haya respuesta para la fuente actual, se está cargando.
    const loading = Boolean(dataSourceId) && current?.loading !== false;

    if (!dataSourceId || (!loading && !kpiData)) return null;

    return (
        <section className="space-y-5 animate-in fade-in slide-in-from-top-4 duration-500">
            <h3 className="text-xs font-bold text-[var(--bi-text-1)] uppercase tracking-wider flex items-center gap-2">
                Perfilado del Dataset
            </h3>
            {loading ? (
                <div className="h-32 rounded-xl border border-[var(--bi-border)] bg-[var(--bi-surface-0)]/40 animate-pulse" />
            ) : kpiData ? (
                <>
                    <KpiCards kpiData={kpiData} />
                    <AnomalyAlert anomalies={kpiData.anomalias} />
                </>
            ) : null}
        </section>
    );
}
