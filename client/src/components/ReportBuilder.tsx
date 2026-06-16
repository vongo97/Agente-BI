'use client';

import { useState } from "react";
import { X, FileText, Download, Sparkles, Loader2, CheckCircle2 } from "lucide-react";
import { generateReportSummary, exportProfessionalReport, exportProfessionalPptx } from "@/lib/api";
import { useDashboard, Message } from "@/context/DashboardContext";

interface ReportBuilderProps {
    isOpen: boolean;
    onClose: () => void;
    messages: Message[];
    userId: string;
    userName: string;
}

export function ReportBuilder({ isOpen, onClose, messages, userId, userName }: ReportBuilderProps) {
    const { apiKey } = useDashboard();
    const [title, setTitle] = useState("Informe Ejecutivo de Análisis BI");
    const [summary, setSummary] = useState("");
    const [generatingSummary, setGeneratingSummary] = useState(false);
    const [exporting, setExporting] = useState(false);
    const [exportingPptx, setExportingPptx] = useState(false);
    const [selectedTemplate, setSelectedTemplate] = useState<"general" | "legal">("general");
    const [selectedMessageIds, setSelectedMessageIds] = useState<number[]>([]);

    if (!isOpen) return null;

    // Todos los mensajes del asistente que tengan ID (guardados en BD)
    const assistantMessages = messages.filter(m => m.role === 'assistant' && m.id);

    const toggleMessage = (id: number) => {
        setSelectedMessageIds(prev =>
            prev.includes(id) ? prev.filter(mid => mid !== id) : [...prev, id]
        );
    };

    const handleGenerateSummary = async () => {
        setGeneratingSummary(true);
        try {
            // Usamos el título y el contexto de los mensajes seleccionados (o todos si no hay ninguno)
            const query = selectedMessageIds.length > 0
                ? `Analiza estos puntos: ${messages.filter(m => selectedMessageIds.includes(m.id!)).map(m => m.content).join(". ")}`
                : "Genera un resumen estratégico de los datos analizados hasta ahora.";

            const res = await generateReportSummary(query, apiKey, userId);
            setSummary(res.summary);
        } catch (error) {
            console.error("Error generating report summary:", error);
            alert("Error generando resumen estratégico");
        } finally {
            setGeneratingSummary(false);
        }
    };

    const handleExport = async (format: 'pdf' | 'pptx' = 'pdf') => {
        if (selectedMessageIds.length === 0) {
            alert("Selecciona al menos un gráfico para el reporte.");
            return;
        }

        if (format === 'pdf') setExporting(true);
        else setExportingPptx(true);
        
        try {
            const items = messages
                .filter(m => selectedMessageIds.includes(m.id!))
                .map(m => ({
                    content: m.content,
                    fig: m.fig
                }));

            const reportData = {
                user_id: userId,
                user_name: userName,
                title,
                summary,
                items,
                template: selectedTemplate
            };

            let blob;
            if (format === 'pdf') {
                blob = await exportProfessionalReport(reportData);
            } else {
                blob = await exportProfessionalPptx(reportData);
            }
            
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `reporte_profesional_${Date.now()}.${format}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            onClose();
        } catch (error) {
            console.error(`Error exporting report to ${format.toUpperCase()}:`, error);
            alert(`Error al exportar el reporte profesional a ${format.toUpperCase()}`);
        } finally {
            if (format === 'pdf') setExporting(false);
            else setExportingPptx(false);
        }
    };

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-300">
            <div className="bg-[var(--bi-surface-0)] border border-[var(--bi-border)] w-full max-w-2xl rounded-lg overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
                <header className="p-6 border-b border-[var(--bi-border)] flex items-center justify-between bg-[var(--bi-surface-0)]/50">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-[var(--bi-blue-dim)] rounded-lg">
                            <FileText className="w-5 h-5 text-[var(--bi-blue)]" />
                        </div>
                        <div>
                            <h3 className="text-base font-bold text-[var(--bi-text-1)] tracking-tight">Constructor de Reporte Profesional</h3>
                            <p className="text-[10px] text-[var(--bi-text-3)] uppercase tracking-widest font-semibold">Estándar Ejecutivo • 2026</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-[var(--bi-surface-2)] rounded-full text-[var(--bi-text-3)] hover:text-[var(--bi-text-1)] transition-colors cursor-pointer">
                        <X className="w-5 h-5" />
                    </button>
                </header>

                <div className="flex-1 overflow-y-auto p-6 lg:p-8 space-y-6 lg:space-y-8 custom-scrollbar">
                    {/* Título del Reporte */}
                    <div className="space-y-2">
                        <label className="text-[10px] font-semibold text-[var(--bi-text-3)] uppercase tracking-widest">Título del Informe</label>
                        <input
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            className="w-full bg-[var(--bi-canvas)] border border-[var(--bi-border)] rounded-lg px-4 py-2.5 text-xs text-[var(--bi-text-1)] focus:outline-none focus:border-[var(--bi-blue-border)] transition-all font-medium"
                            placeholder="Ej: Análisis Trimestral de Ventas"
                        />
                    </div>

                    {/* Resumen Ejecutivo */}
                    <div className="space-y-2">
                        <div className="flex items-center justify-between">
                            <label className="text-[10px] font-semibold text-[var(--bi-text-3)] uppercase tracking-widest">Resumen Estratégico AI</label>
                            <button
                                onClick={handleGenerateSummary}
                                disabled={generatingSummary}
                                className="flex items-center gap-1.5 text-[10px] font-semibold text-[var(--bi-blue)] hover:text-[var(--bi-blue-hover)] uppercase tracking-wider transition-colors disabled:opacity-50 cursor-pointer"
                            >
                                {generatingSummary ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
                                {summary ? "Regenerar" : "Generar con IA"}
                            </button>
                        </div>
                        <textarea
                            value={summary}
                            onChange={(e) => setSummary(e.target.value)}
                            rows={4}
                            className="w-full bg-[var(--bi-canvas)] border border-[var(--bi-border)] rounded-lg px-4 py-3 text-[var(--bi-text-2)] text-sm focus:outline-none focus:border-[var(--bi-blue-border)] transition-all resize-none leading-relaxed"
                            placeholder="Un informe profesional necesita un resumen sólido..."
                        />
                    </div>

                    {/* Selección de Mensajes */}
                    <div className="space-y-3">
                        <label className="text-[10px] font-semibold text-[var(--bi-text-3)] uppercase tracking-widest">Selecciona Hallazgos ({selectedMessageIds.length})</label>
                        {assistantMessages.length === 0 ? (
                            <div className="p-8 text-center border border-dashed border-[var(--bi-border)] rounded-lg bg-[var(--bi-canvas)]/30">
                                <p className="text-[var(--bi-text-3)] text-xs italic">No hay análisis disponibles en este chat.</p>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 gap-2.5 max-h-[220px] overflow-y-auto pr-2 custom-scrollbar">
                                {assistantMessages.map((m) => (
                                    <button
                                        key={m.id}
                                        onClick={() => toggleMessage(m.id!)}
                                        className={`flex items-center gap-4 p-3.5 rounded-lg border transition-all text-left group cursor-pointer ${
                                            selectedMessageIds.includes(m.id!)
                                                ? 'bg-[var(--bi-blue-dim)] border-[var(--bi-blue-border)] shadow-lg shadow-[var(--bi-blue-dim)]/5'
                                                : 'bg-[var(--bi-surface-1)] border-[var(--bi-border)] hover:border-[var(--bi-border-strong)]'
                                        }`}
                                    >
                                        <div className={`w-5 h-5 rounded-md flex items-center justify-center border transition-all ${
                                            selectedMessageIds.includes(m.id!) 
                                                ? 'bg-[var(--bi-blue)] border-[var(--bi-blue)] text-[var(--bi-canvas)]' 
                                                : 'border-[var(--bi-border-strong)] text-transparent bg-[var(--bi-canvas)]'
                                        }`}>
                                            <CheckCircle2 className="w-3.5 h-3.5" />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className={`text-xs font-semibold truncate ${selectedMessageIds.includes(m.id!) ? 'text-[var(--bi-text-1)]' : 'text-[var(--bi-text-2)] group-hover:text-[var(--bi-text-1)]'}`}>
                                                {m.content.length > 80 ? m.content.slice(0, 80) + "..." : m.content}
                                            </p>
                                        </div>
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                <footer className="p-6 bg-[var(--bi-surface-0)]/50 border-t border-[var(--bi-border)] flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                        <label className="text-[10px] font-semibold text-[var(--bi-text-3)] uppercase tracking-wider">Plantilla PPTX:</label>
                        <select 
                            value={selectedTemplate}
                            onChange={(e) => setSelectedTemplate(e.target.value as "general" | "legal")}
                            className="bg-[var(--bi-canvas)] border border-[var(--bi-border)] text-[var(--bi-text-1)] text-xs font-semibold rounded-md px-3 py-1.5 outline-none focus:border-[var(--bi-blue-border)] transition-colors cursor-pointer"
                        >
                            <option value="general">Vektra General</option>
                            <option value="legal">Firma Legal</option>
                        </select>
                    </div>
                    
                    <div className="flex items-center justify-end gap-3">
                        <button onClick={onClose} className="px-3 py-2 text-xs font-semibold text-[var(--bi-text-3)] uppercase tracking-wider hover:text-[var(--bi-text-1)] transition-colors cursor-pointer">
                            Cancelar
                        </button>
                        <button
                            onClick={() => handleExport('pdf')}
                            disabled={exporting || exportingPptx || selectedMessageIds.length === 0}
                            className="flex items-center gap-1.5 bg-[var(--bi-surface-1)] border border-[var(--bi-border)] hover:bg-[var(--bi-surface-2)] text-[var(--bi-text-1)] font-semibold px-4 py-2.5 rounded-lg text-xs uppercase tracking-wider disabled:opacity-40 disabled:cursor-not-allowed transition-all cursor-pointer"
                        >
                            {exporting ? (
                                <>
                                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                    PDF...
                                </>
                            ) : (
                                <>
                                    <Download className="w-3.5 h-3.5" />
                                    Exportar PDF
                                </>
                            )}
                        </button>
                        <button
                            onClick={() => handleExport('pptx')}
                            disabled={exporting || exportingPptx || selectedMessageIds.length === 0}
                            className="flex items-center gap-1.5 bg-[var(--bi-blue)] hover:bg-[var(--bi-blue-hover)] text-[var(--bi-canvas)] font-semibold px-4 py-2.5 rounded-lg text-xs uppercase tracking-wider disabled:opacity-40 disabled:cursor-not-allowed transition-all cursor-pointer"
                        >
                            {exportingPptx ? (
                                <>
                                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                    PPTX...
                                </>
                            ) : (
                                <>
                                    <Download className="w-3.5 h-3.5" />
                                    Exportar PPTX
                                </>
                            )}
                        </button>
                    </div>
                </footer>
            </div>
        </div>
    );
}
