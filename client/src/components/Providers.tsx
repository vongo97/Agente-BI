'use client';

import { SessionProvider } from "next-auth/react";
import { DashboardProvider } from "@/context/DashboardContext";
import { ThemeProvider } from "@/context/ThemeContext";
import { ToastProvider } from "@/context/ToastContext";
import { ToastContainer } from "@/components/ToastContainer";
import { ReactNode } from "react";

export function Providers({ children }: { children: ReactNode }) {
    return (
        <SessionProvider>
            <ThemeProvider>
                <ToastProvider>
                    <DashboardProvider>
                        {children}
                        <ToastContainer />
                    </DashboardProvider>
                </ToastProvider>
            </ThemeProvider>
        </SessionProvider>
    );
}

