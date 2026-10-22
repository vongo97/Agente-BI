'use client';

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { Chat } from "@/components/Chat";
import { DashboardView } from "@/components/DashboardView";
import { SettingsView } from "@/components/SettingsView";
import { SimulationSandbox } from "@/components/SimulationSandbox";
import { VisualSummaryView } from "@/features/visual-summary/VisualSummaryView";
import { useDashboard } from "@/context/DashboardContext";
import { Loader2 } from "lucide-react";
import { isAuthorizedEmail, getAuthorizedEmails, hasAuthorizedEmailsConfigured } from "@/lib/auth-allowlist";
import { AlertCircle, LogOut } from "lucide-react";

export default function Home() {
  const { data: session, status } = useSession();
  const { view } = useDashboard();
  const router = useRouter();
  const [emailDenied, setEmailDenied] = useState(false);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/login");
      return;
    }

    // P-15: allowlist de emails autorizados en el cliente.
    // Si el email no está en la lista, bloquear el acceso y mostrar mensaje claro.
    if (status === "authenticated" && session?.user?.email) {
      const email = session.user.email;
      if (hasAuthorizedEmailsConfigured() && !isAuthorizedEmail(email)) {
        setEmailDenied(true);
      }
    }
  }, [status, session, router]);

  // P-15: pantalla de acceso denegado cuando el email no está en la allowlist.
  if (emailDenied) {
    const emails = getAuthorizedEmails();
    return (
      <div className="min-h-screen bg-[var(--bi-canvas)] flex flex-col items-center justify-center p-4">
        <div className="w-full max-w-md">
          <div className="panel p-6 space-y-4 border border-[var(--bi-red-border)] rounded-xl bg-[var(--bi-red-dim)]/10">
            <AlertCircle className="w-5 h-5 text-[var(--bi-red)] flex-shrink-0" />
            <div className="space-y-1">
              <h2 className="text-base font-semibold text-[var(--bi-red)]">Acceso denegado</h2>
              <p className="text-sm text-[var(--bi-text-2)]">
                Tu cuenta ({session?.user?.email}) no está autorizada para usar Vektra BI.
              </p>
              {emails.length > 0 && (
                <p className="text-xs text-[var(--bi-text-3)]">
                  Correos autorizados: {emails.join(", ")}.
                </p>
              )}
              <p className="text-xs text-[var(--bi-text-3)]">
                Contacta al administrador para solicitar acceso.
              </p>
            </div>
            <button
              onClick={() => {
                // Cerrar sesión y volver al login
                void fetch("/api/auth/signout", { method: "POST" }).then(() => {
                  router.push("/login");
                });
              }}
              className="w-full btn-primary text-xs"
            >
              <LogOut className="w-3 h-3" /> Cerrar sesión
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (status === "loading") {
    return (
      <div className="min-h-screen bg-[var(--bi-canvas)] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-6 h-6 text-[var(--bi-teal)] animate-spin" />
          <span className="text-xs text-[var(--bi-text-3)]">Cargando workspace…</span>
        </div>
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
