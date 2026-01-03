'use client';

import { SessionProvider } from "next-auth/react";
import { DashboardProvider } from "@/context/DashboardContext";
import { ReactNode } from "react";

export function Providers({ children }: { children: ReactNode }) {
    return (
        <SessionProvider>
            <DashboardProvider>
                {children}
            </DashboardProvider>
        </SessionProvider>
    );
}
