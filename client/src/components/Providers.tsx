'use client';

import { SessionProvider } from "next-auth/react";
import { DashboardProvider } from "@/context/DashboardContext";
import { ThemeProvider } from "@/context/ThemeContext";
import { ToastProvider } from "@/context/ToastContext";
import { ToastContainer } from "@/components/ToastContainer";
import { ServerStatusTracker } from "@/components/ServerStatusTracker";
import { ReactNode } from "react";

export function Providers({ children }: { children: ReactNode }) {
    return (
        <SessionProvider>
            <ThemeProvider>
                <ToastProvider>
                    <DashboardProvider>
                        {children}
                        <ToastContainer />
                        {/* P-23: el componente existía pero nunca se montaba, así
                            que el sondeo de salud del servidor (isServerHealthy,
                            cada 30 s) no mostraba nada. Ahora sí se monta. */}
                        <ServerStatusTracker />
                    </DashboardProvider>
                </ToastProvider>
            </ThemeProvider>
        </SessionProvider>
    );
}

