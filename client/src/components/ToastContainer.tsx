'use client';

import React from 'react';
import { useToast, Toast } from '@/context/ToastContext';
import { CheckCircle2, AlertCircle, Info, AlertTriangle, X } from 'lucide-react';

export function ToastContainer() {
    const { toasts, removeToast } = useToast();

    if (toasts.length === 0) return null;

    const getIcon = (type: string) => {
        switch (type) {
            case 'success':
                return <CheckCircle2 className="w-4 h-4 text-[var(--bi-teal)] shrink-0" />;
            case 'error':
                return <AlertCircle className="w-4 h-4 text-[var(--bi-red)] shrink-0" />;
            case 'warning':
                return <AlertTriangle className="w-4 h-4 text-[var(--bi-amber)] shrink-0" />;
            case 'info':
            default:
                return <Info className="w-4 h-4 text-[var(--bi-blue)] shrink-0" />;
        }
    };

    const getBorderClass = (type: string) => {
        switch (type) {
            case 'success':
                return 'border-[var(--bi-teal-border)] shadow-[0_0_12px_rgba(45,212,191,0.1)]';
            case 'error':
                return 'border-[var(--bi-red-border)] shadow-[0_0_12px_rgba(248,113,113,0.1)]';
            case 'warning':
                return 'border-amber-500/20 shadow-[0_0_12px_rgba(251,191,36,0.1)]';
            case 'info':
            default:
                return 'border-[var(--bi-blue-border)] shadow-[0_0_12px_rgba(96,165,250,0.1)]';
        }
    };

    return (
        <div className="fixed bottom-6 right-6 z-[100] flex flex-col gap-3 max-w-sm w-full pointer-events-none">
            {toasts.map((toast: Toast) => (
                <div
                    key={toast.id}
                    className={`pointer-events-auto flex items-start justify-between gap-3 p-4 rounded-lg bg-[var(--bi-surface-0)]/80 backdrop-blur-md border text-[var(--bi-text-1)] transition-all duration-300 animate-in slide-in-from-bottom-4 ${getBorderClass(toast.type)}`}
                >
                    <div className="flex gap-3">
                        <div className="mt-0.5">{getIcon(toast.type)}</div>
                        <div className="flex flex-col gap-0.5">
                            <span className="text-xs font-semibold leading-relaxed">{toast.message}</span>
                        </div>
                    </div>
                    <button
                        onClick={() => removeToast(toast.id)}
                        className="text-[var(--bi-text-3)] hover:text-[var(--bi-text-1)] hover:bg-[var(--bi-surface-2)] p-1 rounded-md transition-colors cursor-pointer shrink-0"
                    >
                        <X className="w-3.5 h-3.5" />
                    </button>
                </div>
            ))}
        </div>
    );
}
