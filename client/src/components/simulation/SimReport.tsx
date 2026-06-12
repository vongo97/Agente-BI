import { Activity, Download, Loader2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { exportSimulationPdf } from "@/lib/api";
import { useState } from "react";

interface SimReportProps {
    activeSim: any;
    userId: string;
    polling: boolean;
}

export function SimReport({ activeSim, userId, polling }: SimReportProps) {
    const [downloadingPdf, setDownloadingPdf] = useState(false);

    const handleDownloadPdf = async () => {
        if (!activeSim?.id) return;
        setDownloadingPdf(true);
        try {
            const blob = await exportSimulationPdf(activeSim.id, userId);
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `veredicto_sim_${activeSim.id}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();
        } catch (err) {
            console.error("Error al descargar PDF de simulación:", err);
            alert("Error al descargar el veredicto en PDF de forma segura.");
        } finally {
            setDownloadingPdf(false);
        }
    };

    return (
        <div className="col-span-12 lg:col-span-5 h-fit lg:sticky lg:top-0">
            {activeSim.result_report ? (
                <div className="bg-[var(--bi-surface-0)] border border-[var(--sim-border)] rounded-lg p-6 lg:p-8 shadow-2xl shadow-[var(--sim-accent-soft)]/5 animate-in fade-in slide-in-from-right-8 duration-700">
                    <div className="flex items-center justify-between mb-6">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-[var(--sim-accent-soft)] border border-[var(--sim-border)]/50 rounded-md">
                                <Activity className="w-4 h-4 text-[var(--sim-accent)]" />
                            </div>
                            <h2 className="text-[10px] font-bold text-[var(--sim-accent)] uppercase tracking-[0.25em]">Veredicto Estratégico</h2>
                        </div>
                        <button 
                            onClick={handleDownloadPdf}
                            disabled={downloadingPdf}
                            className="p-2 hover:bg-[var(--bi-surface-2)] rounded-md text-[var(--sim-accent)] transition-all disabled:opacity-50 cursor-pointer"
                            title="Descargar PDF"
                        >
                            {downloadingPdf ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                        </button>
                    </div>
                    <div className="markdown-content prose prose-invert prose-sm max-w-none">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {activeSim.result_report}
                        </ReactMarkdown>
                    </div>
                    
                    <div className="mt-6 pt-6 border-t border-[var(--bi-border)] flex items-center justify-between">
                        <div className="flex flex-col">
                            <span className="text-[8px] text-[var(--bi-text-3)] font-semibold uppercase tracking-widest">Motor Utilizado</span>
                            <span className="text-[10px] text-[var(--sim-accent)] font-bold uppercase tracking-tight">{activeSim.provider}</span>
                        </div>
                        <div className="flex flex-col items-end">
                            <span className="text-[8px] text-[var(--bi-text-3)] font-semibold uppercase tracking-widest">Estado</span>
                            <span className="text-[10px] text-[var(--bi-green)] font-bold uppercase tracking-tight">Consolidado</span>
                        </div>
                    </div>
                </div>
            ) : polling ? (
                <div className="bg-[var(--bi-surface-0)] border border-dashed border-[var(--bi-border)] rounded-lg p-8 text-center space-y-4">
                    <Loader2 className="w-6 h-6 text-[var(--sim-accent)]/40 animate-spin mx-auto" />
                    <p className="text-[10px] font-bold text-[var(--bi-text-2)] uppercase tracking-[0.2em]">Esperando Síntesis Final</p>
                    <p className="text-[9px] text-[var(--bi-text-3)] max-w-[200px] mx-auto italic leading-relaxed">El estratega está procesando las rondas de debate para emitir el veredicto final.</p>
                </div>
            ) : null}
        </div>
    );
}
