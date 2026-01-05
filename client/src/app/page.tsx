'use client';

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Sidebar } from "@/components/Sidebar";
import { Chat } from "@/components/Chat";
import { DashboardView } from "@/components/DashboardView";
import { useDashboard } from "@/context/DashboardContext";
import { Loader2 } from "lucide-react";
import { ServerStatusTracker } from "@/components/ServerStatusTracker";

export default function Home() {
  const { data: session, status } = useSession();
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

  const { view } = useDashboard();

  return (
    <main className="flex min-h-screen bg-black text-white">
      <Sidebar />
      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        {view === 'chat' ? <Chat /> : <DashboardView />}
      </div>
      <ServerStatusTracker />
    </main>
  );
}
