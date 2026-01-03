'use client';

import { signIn, useSession } from "next-auth/react";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
    const { data: session, status } = useSession();
    const router = useRouter();

    useEffect(() => {
        if (status === "authenticated") {
            router.push("/");
        }
    }, [status, router]);

    return (
        <div className="min-h-screen bg-[#0a0a0a] flex flex-col items-center justify-center p-4">
            <div className="max-w-md w-full bg-[#111] border border-white/10 rounded-2xl p-8 shadow-2xl">
                <div className="text-center mb-10">
                    <div className="inline-block p-3 bg-blue-500/10 rounded-xl mb-4 text-blue-500">
                        <svg xmlns="http://www.w3.org/2000/svg" className="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                        </svg>
                    </div>
                    <h1 className="text-3xl font-bold text-white mb-2">Acceso Restringido</h1>
                    <p className="text-gray-400">Inicia sesión con tu cuenta de Google para acceder al Agente BI.</p>
                </div>

                <button
                    onClick={() => signIn("google")}
                    className="w-full flex items-center justify-center gap-3 bg-white text-black font-semibold py-3.5 px-6 rounded-xl hover:bg-gray-200 transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98]"
                >
                    <svg className="w-5 h-5" viewBox="0 0 48 48">
                        <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
                        <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.13-.45-4.69H24v9.07h12.91c-.58 3-2.26 5.52-4.74 7.19l7.48 5.81c4.35-4 6.83-9.92 6.83-16.38z" />
                        <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
                        <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.48-5.81c-2.12 1.42-4.83 2.26-8.41 2.26-6.42 0-11.83-4.32-13.77-10.16l-8.03 6.22C6.54 42.62 14.64 48 24 48z" />
                    </svg>
                    Continuar con Google
                </button>

                <div className="mt-8 pt-8 border-t border-white/5 text-center">
                    <p className="text-xs text-gray-500 uppercase tracking-widest font-medium">Empoderado por Inteligencia Artificial</p>
                </div>
            </div>
        </div>
    );
}
