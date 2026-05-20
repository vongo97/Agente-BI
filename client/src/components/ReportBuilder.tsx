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
            alert(`Error al exportar el reporte profesional a ${format.toUpperCase()}`);
        } finally {
            if (format === 'pdf') setExporting(false);
            else setExportingPptx(false);
        }
    };

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-300">
            <div className="bg-[#111] border border-white/10 w-full max-w-2xl rounded-3xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
                <header className="p-6 border-b border-white/5 flex items-center justify-between bg-white/[0.02]">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-blue-600/20 rounded-xl">
                            <FileText className="w-5 h-5 text-blue-500" />
                        </div>
                        <div>
                            <h3 className="text-lg font-bold text-white tracking-tight">Constructor de Reporte Profesional</h3>
                            <p className="text-[10px] text-gray-500 uppercase tracking-widest font-black">Estándar Ejecutivo • 2026</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-full text-gray-400 transition-colors">
                        <X className="w-5 h-5" />
                    </button>
                </header>

                <div className="flex-1 overflow-y-auto p-8 space-y-8 custom-scrollbar">
                    {/* Título del Reporte */}
                    <div className="space-y-3">
                        <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Título del Informe</label>
                        <input
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition-all font-medium"
                            placeholder="Ej: Análisis Trimestral de Ventas"
                        />
                    </div>

                    {/* Resumen Ejecutivo */}
                    <div className="space-y-3">
                        <div className="flex items-center justify-between">
                            <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Resumen Estratégico AI</label>
                            <button
                                onClick={handleGenerateSummary}
                                disabled={generatingSummary}
                                className="flex items-center gap-2 text-[10px] font-black text-blue-500 hover:text-blue-400 uppercase tracking-widest transition-colors disabled:opacity-50"
                            >
                                {generatingSummary ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
                                {summary ? "Regenerar" : "Generar con IA"}
                            </button>
                        </div>
                        <textarea
                            value={summary}
                            onChange={(e) => setSummary(e.target.value)}
                            rows={4}
                            className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-gray-300 text-sm focus:outline-none focus:border-blue-500 transition-all resize-none leading-relaxed"
                            placeholder="Un informe profesional necesita un resumen sólido..."
                        />
                    </div>

                    {/* Selección de Mensajes */}
                    <div className="space-y-4">
                        <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Selecciona Hallazgos ({selectedMessageIds.length})</label>
                        {assistantMessages.length === 0 ? (
                            <div className="p-8 text-center border-2 border-dashed border-white/5 rounded-2xl">
                                <p className="text-gray-500 text-sm italic">No hay análisis disponibles en este chat.</p>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 gap-3">
                                {assistantMessages.map((m) => (
                                    <button
                                        key={m.id}
                                        onClick={() => toggleMessage(m.id!)}
                                        className={`flex items-center gap-4 p-4 rounded-2xl border transition-all text-left group ${selectedMessageIds.includes(m.id!)
                                                ? 'bg-blue-600/10 border-blue-500/50 shadow-lg shadow-blue-500/5'
                                                : 'bg-white/[0.02] border-white/5 hover:border-white/10'
                                            }`}
                                    >
                                        <div className={`w-5 h-5 rounded-md flex items-center justify-center transition-colors ${selectedMessageIds.includes(m.id!) ? 'bg-blue-500 text-white' : 'bg-white/10 text-transparent'
                                            }`}>
                                            <CheckCircle2 className="w-3.5 h-3.5" />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className={`text-xs font-bold truncate ${selectedMessageIds.includes(m.id!) ? 'text-white' : 'text-gray-400 group-hover:text-gray-300'}`}>
                                                {m.content.length > 60 ? m.content.slice(0, 60) + "..." : m.content}
                                            </p>
                                        </div>
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                <footer className="p-6 bg-white/[0.02] border-t border-white/5 flex items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                        <label className="text-xs font-bold text-gray-400 uppercase tracking-widest">Plantilla PPTX:</label>
                        <select 
                            value={selectedTemplate}
                            onChange={(e) => setSelectedTemplate(e.target.value as "general" | "legal")}
                            className="bg-slate-800 border border-white/10 text-white text-xs font-bold rounded-lg px-3 py-2 outline-none focus:border-blue-500 transition-colors"
                        >
                            <option value="general">Vektra General</option>
                            <option value="legal">Firma Legal</option>
                        </select>
                    </div>
                    
                    <div className="flex items-center gap-3">
                        <button onClick={onClose} className="px-4 py-2.5 text-xs font-black text-gray-500 uppercase tracking-widest hover:text-white transition-colors">
                            Cancelar
                        </button>
                        <button
                            onClick={() => handleExport('pdf')}
                            disabled={exporting || exportingPptx || selectedMessageIds.length === 0}
                            className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 disabled:bg-gray-800 disabled:text-gray-600 text-white font-bold px-6 py-3 rounded-xl transition-all font-sans text-xs uppercase tracking-widest border border-white/10"
                        >
                            {exporting ? (
                                <>
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    PDF...
                                </>
                            ) : (
                                <>
                                    <Download className="w-4 h-4" />
                                    Exportar PDF
                                </>
                            )}
                        </button>
                        <button
                            onClick={() => handleExport('pptx')}
                            disabled={exporting || exportingPptx || selectedMessageIds.length === 0}
                            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-800 disabled:text-gray-600 text-white font-bold px-6 py-3 rounded-xl shadow-xl shadow-blue-500/20 transition-all font-sans text-xs uppercase tracking-widest"
                        >
                            {exportingPptx ? (
                                <>
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    PPTX...
                                </>
                            ) : (
                                <>
                                    <Download className="w-4 h-4" />
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
