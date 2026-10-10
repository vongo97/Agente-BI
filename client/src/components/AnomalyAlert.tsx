'use client';

import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";

interface Anomaly {
  columna: string;
  valor: number;
  z_score: number;
  media: number;
  severidad: string;
}

interface AnomalyAlertProps {
  anomalies: Anomaly[];
  onIgnore?: (index: number) => void;
  onViewDetail?: (anomaly: Anomaly) => void;
}

function severityColor(severity: string): string {
  switch (severity) {
    case "Alta": return "bg-[var(--bi-red)]";
    case "Media": return "bg-[var(--bi-amber)]";
    default: return "bg-[var(--bi-text-3)]";
  }
}

export default function AnomalyAlert({ anomalies, onIgnore, onViewDetail }: AnomalyAlertProps) {
  const [dismissed, setDismissed] = useState<number[]>([]);

  if (!anomalies || anomalies.length === 0) return null;

  const visible = anomalies.filter((_, i) => !dismissed.includes(i));
  if (visible.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
      className="border-2 border-[var(--bi-amber)]/40 bg-[var(--bi-surface-0)]/60 backdrop-blur-md rounded-xl p-5 shadow-sm"
    >
      <div className="flex items-center gap-3 mb-4">
        <span className="text-xl" role="img" aria-label="alerta">⚠️</span>
        <div>
          <h4 className="text-sm font-bold text-[var(--bi-text-1)]">Alertas de Valor Atípico</h4>
          <p className="text-[10px] text-[var(--bi-text-3)] font-medium">
            {anomalies.length} anomalía{anomalies.length !== 1 ? "s" : ""} detectada{anomalies.length !== 1 ? "s" : ""} — Z-Score &gt; 3σ
          </p>
        </div>
      </div>

      <div className="space-y-2">
        <AnimatePresence>
          {visible.map((anomaly, i) => (
            <motion.div
              key={`${anomaly.columna}-${i}`}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 10, height: 0, marginBottom: 0 }}
              transition={{ duration: 0.25, delay: i * 0.05 }}
              className="flex items-center justify-between gap-4 p-3 rounded-lg bg-[var(--bi-surface-1)]/50 border border-[var(--bi-border)]"
            >
              <div className="flex items-center gap-3 min-w-0">
                <span className={`w-2 h-2 rounded-full shrink-0 ${severityColor(anomaly.severidad)}`} />
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-[var(--bi-text-1)] truncate">
                    {anomaly.columna}
                    <span className="text-[var(--bi-text-3)] font-normal ml-1.5">
                      valor {anomaly.valor.toLocaleString(undefined, { maximumFractionDigits: 2 })} (Z={anomaly.z_score.toFixed(1)})
                    </span>
                  </p>
                  <p className="text-[10px] text-[var(--bi-text-3)]">
                    Media: {anomaly.media.toLocaleString(undefined, { maximumFractionDigits: 2 })} · Severidad: {anomaly.severidad}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-1.5 shrink-0">
                {onViewDetail && (
                  <button
                    onClick={() => onViewDetail(anomaly)}
                    className="px-2.5 py-1.5 text-[10px] font-semibold rounded-md bg-[var(--bi-blue-dim)] text-[var(--bi-blue)] hover:bg-[var(--bi-blue)] hover:text-white transition-all cursor-pointer"
                  >
                    Ver detalle
                  </button>
                )}
                {onIgnore && (
                  <button
                    onClick={() => {
                      setDismissed(prev => [...prev, anomalies.indexOf(anomaly)]);
                      onIgnore(anomalies.indexOf(anomaly));
                    }}
                    className="px-2.5 py-1.5 text-[10px] font-semibold rounded-md text-[var(--bi-text-3)] hover:text-[var(--bi-text-1)] hover:bg-[var(--bi-surface-2)] transition-all cursor-pointer"
                  >
                    Ignorar
                  </button>
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
