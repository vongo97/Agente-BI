import { Activity, Download, Loader2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { getSimulationPdfUrl } from "@/lib/api";

interface SimReportProps {
    activeSim: any;
    userId: string;
    polling: boolean;
}

export function SimReport({ activeSim, userId, polling }: SimReportProps) {
    return (
        <div className="col-span-12 lg:col-span-5 h-fit lg:sticky lg:top-0">
            {activeSim.result_report ? (
                <div className="bg-gradient-to-br from-purple-900/20 to-indigo-900/10 border border-purple-500/20 rounded-3xl p-8 shadow-2xl shadow-purple-900/20 animate-in fade-in slide-in-from-right-8 duration-700">
                    <div className="flex items-center justify-between mb-8">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-purple-500/20 rounded-lg">
                                <Activity className="w-4 h-4 text-purple-400" />
                            </div>
                            <h2 className="text-[10px] font-black text-purple-400 uppercase tracking-[0.3em]">Veredicto Estratégico</h2>
                        </div>
                        <a 
                            href={getSimulationPdfUrl(activeSim.id, userId)} 
                            target="_blank"
                            className="p-2 hover:bg-white/5 rounded-lg text-purple-400 transition-all"
                            title="Descargar PDF"
                        >
                            <Download className="w-4 h-4" />
                        </a>
                    </div>
                    <div className="markdown-content prose prose-invert prose-sm prose-purple max-w-none">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {activeSim.result_report}
                        </ReactMarkdown>
                    </div>
                    
                    <div className="mt-8 pt-8 border-t border-purple-500/10 flex items-center justify-between">
                        <div className="flex flex-col">
                            <span className="text-[8px] text-gray-500 font-black uppercase tracking-widest">Motor Utilizado</span>
                            <span className="text-[10px] text-purple-300 font-bold uppercase tracking-tight">{activeSim.provider}</span>
                        </div>
                        <div className="flex flex-col items-end">
                            <span className="text-[8px] text-gray-500 font-black uppercase tracking-widest">Estado</span>
                            <span className="text-[10px] text-green-400 font-bold uppercase tracking-tight">Consolidado</span>
                        </div>
                    </div>
                </div>
            ) : polling ? (
                <div className="bg-white/[0.02] border border-dashed border-white/10 rounded-3xl p-12 text-center space-y-4">
                    <Loader2 className="w-8 h-8 text-white/10 animate-spin mx-auto" />
                    <p className="text-[10px] font-black text-gray-500 uppercase tracking-[0.2em]">Esperando Síntesis Final</p>
                    <p className="text-[9px] text-gray-600 max-w-[200px] mx-auto italic">El estratega está procesando las 3 rondas de debate para emitir el veredicto final.</p>
                </div>
            ) : null}
        </div>
    );
}
