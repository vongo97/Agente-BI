'use client';

import { motion } from "framer-motion";

export interface KpiData {
  dataset: { nombre: string; filas: number; columnas: number };
  columnas: { numericas: number; categoricas: number; lista_numericas: string[]; lista_categoricas: string[] };
  saturacion: number;
  nicho_top: string;
  confianza: number;
  completitud: number;
  anomalias: { columna: string; valor: number; z_score: number; media: number; severidad: string }[];
  correlaciones_fuertes: { columna_a: string; columna_b: string; r: number }[];
}

interface KpiCardsProps {
  kpiData: KpiData;
}

function colorClass(value: number): string {
  if (value >= 80) return "text-[var(--bi-green)]";
  if (value >= 50) return "text-[var(--bi-amber)]";
  return "text-[var(--bi-red)]";
}

function bgBarColor(value: number): string {
  if (value >= 80) return "bg-[var(--bi-green)]";
  if (value >= 50) return "bg-[var(--bi-amber)]";
  return "bg-[var(--bi-red)]";
}

function KpiCard({
  title,
  value,
  suffix,
  subtitle,
  progress,
  delay,
}: {
  title: string;
  value: string;
  suffix?: string;
  subtitle: string;
  progress: number;
  delay: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay, ease: "easeOut" }}
      className="relative overflow-hidden bg-[var(--bi-surface-0)]/60 backdrop-blur-md border border-[var(--bi-border)] rounded-xl p-5 hover:border-[var(--bi-blue-border)] hover:bg-[var(--bi-surface-0)] transition-all group shadow-sm flex flex-col justify-between h-36"
    >
      <div className="z-10">
        <span className="text-[10px] font-bold text-[var(--bi-text-3)] uppercase tracking-widest">{title}</span>
        <h4 className={`text-2xl font-black mt-2 tracking-tight transition-transform group-hover:translate-x-1 duration-200 ${colorClass(progress)}`}>
          {value}
          {suffix && <span className="text-sm font-semibold text-[var(--bi-text-3)] ml-1">{suffix}</span>}
        </h4>
      </div>
      <div className="z-10 space-y-2">
        <div className="flex items-center gap-1.5">
          <span className={`w-1.5 h-1.5 rounded-full ${progress >= 80 ? "bg-[var(--bi-green)]" : progress >= 50 ? "bg-[var(--bi-amber)]" : "bg-[var(--bi-red)]"} ${progress >= 80 ? "animate-pulse" : ""}`} />
          <span className="text-[10px] text-[var(--bi-text-3)] font-medium truncate">{subtitle}</span>
        </div>
        <div className="w-full h-1.5 bg-[var(--bi-surface-2)] rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${Math.min(progress, 100)}%` }}
            transition={{ duration: 0.8, delay: delay + 0.2, ease: "easeOut" }}
            className={`h-full rounded-full ${bgBarColor(progress)}`}
          />
        </div>
      </div>
    </motion.div>
  );
}

export default function KpiCards({ kpiData }: KpiCardsProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 animate-in fade-in slide-in-from-top-4 duration-500">
      <KpiCard
        title="Saturación Global"
        value={`${kpiData.saturacion}%`}
        subtitle={`${kpiData.columnas.numericas} numéricas de ${kpiData.dataset.columnas} columnas`}
        progress={kpiData.saturacion}
        delay={0}
      />
      <KpiCard
        title="Top Nicho Detectado"
        value={kpiData.nicho_top.length > 25 ? kpiData.nicho_top.slice(0, 22) + "..." : kpiData.nicho_top}
        subtitle={`${kpiData.columnas.categoricas} categóricas analizadas`}
        progress={kpiData.saturacion}
        delay={0.1}
      />
      <KpiCard
        title="Confianza del Análisis"
        value={`${kpiData.confianza}%`}
        subtitle={`${kpiData.anomalias.length} anomalías detectadas`}
        progress={kpiData.confianza}
        delay={0.2}
      />
      <KpiCard
        title="Completitud"
        value={`${kpiData.completitud}%`}
        subtitle={`${kpiData.dataset.filas.toLocaleString()} registros · ${kpiData.dataset.nombre}`}
        progress={kpiData.completitud}
        delay={0.3}
      />
    </div>
  );
}
