'use client';

import { SessionProvider } from "next-auth/react";
import { DashboardProvider } from "@/context/DashboardContext";
import { ThemeProvider } from "@/context/ThemeContext";
import { ReactNode } from "react";

export function Providers({ children }: { children: ReactNode }) {
    return (
        <SessionProvider>
            <ThemeProvider>
                <DashboardProvider>
                    {children}
                </DashboardProvider>
            </ThemeProvider>
        </SessionProvider>
    );
}
