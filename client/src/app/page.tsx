'use client';

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Sidebar } from "@/components/Sidebar";
import { Chat } from "@/components/Chat";
import { DashboardView } from "@/components/DashboardView";
import { SettingsView } from "@/components/SettingsView";
import { SimulationSandbox } from "@/components/SimulationSandbox";
import { VisualSummaryView } from "@/features/visual-summary/VisualSummaryView";
import { useDashboard } from "@/context/DashboardContext";
import { Loader2 } from "lucide-react";

export default function Home() {
  const { data: session, status } = useSession();
  const { view } = useDashboard();
  const router = useRouter();

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/login");
    }
  }, [status, router]);

  if (status === "loading") {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    );
  }

  if (!session) return null;

  const renderView = () => {
    switch (view) {
      case 'chat': return <Chat />;
      case 'dashboard': return <DashboardView />;
      case 'settings': return <SettingsView />;
      case 'simulation': return <SimulationSandbox />;
      case 'visual-summary': return <VisualSummaryView />;
      default: return <Chat />;
    }
  };

  return (
    <main className="flex min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)]">
      <Sidebar />
      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        {renderView()}
      </div>
    </main>
  );
}
