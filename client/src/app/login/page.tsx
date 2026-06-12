'use client';

import { signIn, useSession } from "next-auth/react";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Activity } from "lucide-react";

export default function LoginPage() {
    const { status } = useSession();
    const router = useRouter();

    useEffect(() => {
        if (status === "authenticated") router.push("/");
    }, [status, router]);

    return (
        <div className="min-h-screen bg-[var(--bi-canvas)] flex flex-col items-center justify-center p-4">
            <div className="w-full max-w-sm">

                {/* Brand */}
                <div className="flex items-center justify-center gap-2.5 mb-8">
                    <div className="w-8 h-8 rounded-lg bg-[var(--bi-teal)] flex items-center justify-center">
                        <Activity className="w-4 h-4 text-black" />
                    </div>
                    <span className="text-lg font-semibold text-[var(--bi-text-1)] tracking-tight">Vektra BI</span>
                    <span className="badge badge-teal">v2.5</span>
                </div>

                {/* Card */}
                <div className="panel p-6 space-y-5">
                    <div className="space-y-1">
                        <h1 className="text-base font-semibold text-[var(--bi-text-1)]">Iniciar sesión</h1>
                        <p className="text-sm text-[var(--bi-text-2)]">
                            Accede con tu cuenta de Google para continuar.
                        </p>
                    </div>

                    {/* Google sign-in */}
                    <button
                        onClick={() => signIn("google")}
                        className="w-full flex items-center justify-center gap-2.5 py-2.5 px-4 rounded-md bg-white text-gray-900 text-sm font-semibold hover:bg-gray-100 transition-colors border border-gray-200"
                    >
                        {/* Google logo inline */}
                        <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 48 48">
                            <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
                            <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.13-.45-4.69H24v9.07h12.91c-.58 3-2.26 5.52-4.74 7.19l7.48 5.81c4.35-4 6.83-9.92 6.83-16.38z" />
                            <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
                            <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.48-5.81c-2.12 1.42-4.83 2.26-8.41 2.26-6.42 0-11.83-4.32-13.77-10.16l-8.03 6.22C6.54 42.62 14.64 48 24 48z" />
                        </svg>
                        Continuar con Google
                    </button>

                    {/* Dev-only: credential login */}
                    {process.env.NODE_ENV === 'development' && process.env.NEXT_PUBLIC_VERCEL_ENV !== 'production' && (
                        <>
                            <div className="relative">
                                <div className="absolute inset-0 flex items-center">
                                    <div className="w-full border-t border-[var(--bi-border)]" />
                                </div>
                                <div className="relative flex justify-center">
                                    <span className="px-2 bg-[var(--bi-surface-0)] text-[10px] text-[var(--bi-text-3)] uppercase tracking-wider font-medium">
                                        Solo desarrollo
                                    </span>
                                </div>
                            </div>
                            <button
                                onClick={() => signIn("credentials")}
                                className="btn-primary w-full justify-center"
                            >
                                Entrar como Invitado (Local)
                            </button>
                        </>
                    )}
                </div>

                {/* Footer note */}
                <p className="mt-6 text-center text-[10px] text-[var(--bi-text-3)] uppercase tracking-wider">
                    Análisis de datos con IA · 2026
                </p>
            </div>
        </div>
    );
}
