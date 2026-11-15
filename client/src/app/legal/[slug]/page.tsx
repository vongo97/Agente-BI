import fs from "fs";
import path from "path";
import { notFound } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Link from "next/link";
import { Activity } from "lucide-react";

// Fuentes legales: `client/content/legal/*.md`.
//
// P-20: antes vivían en `docs/legal/`, en la raíz del repositorio, y la página
// los leía con `path.join(process.cwd(), "..", "docs", "legal", ...)`. Eso
// funciona en `npm run dev` (donde `process.cwd()` es `client/`) pero **falla
// en el build standalone / Docker**, donde `process.cwd()` no tiene un `docs/`
// al lado → 404 en las tres páginas legales. Los `.md` ahora viven **dentro de
// `client/`, así que forman parte de la app y se empaquetan siempre**.
//
// P-75: resolver la ruta probando candidatas en un bucle (`fs.existsSync` sobre
// rutas calculadas) hace que Turbopack avise: *"Dynamic filesystem access
// causes tracing of the whole project"* — se empaqueta **todo** el proyecto
// (incluido `public/`) en el output de despliegue, lo que infla el bundle y
// puede disparar los límites de tamaño de Render.
//
// Estas páginas son **SSG** (`generateStaticParams` las prerenderiza en el
// build), así que el contenido se hornea en el HTML y **no hace falta leer
// nada en runtime**. La lectura ocurre una sola vez, en el build, y con una
// ruta **literalmente acotada** a un subdirectorio conocido — que es lo que
// Turbopack pide para poder trazar solo lo necesario.
//
// Cada documento tiene su propia entrada en la tabla: la ruta es un literal,
// no se calcula. Si el fichero no está (build en un checkout raro), `notFound()`
// da el 404 limpio en vez de una excepción sin manejar.
const LEGAL_DOCS: Record<string, { filePath: string; title: string }> = {
    "privacidad": {
        filePath: path.join(process.cwd(), "content", "legal", "politica-privacidad.md"),
        title: "Política de Privacidad",
    },
    "terminos": {
        filePath: path.join(process.cwd(), "content", "legal", "terminos-de-uso.md"),
        title: "Términos y Condiciones de Uso",
    },
    "cookies": {
        filePath: path.join(process.cwd(), "content", "legal", "aviso-cookies.md"),
        title: "Aviso de Cookies",
    },
};

export function generateStaticParams() {
    return Object.keys(LEGAL_DOCS).map((slug) => ({ slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
    const { slug } = await params;
    const doc = LEGAL_DOCS[slug];
    return { title: doc ? `${doc.title} | Vektra BI` : "Legal | Vektra BI" };
}

export default async function LegalPage({ params }: { params: Promise<{ slug: string }> }) {
    const { slug } = await params;
    const doc = LEGAL_DOCS[slug];
    if (!doc) notFound();

    if (!fs.existsSync(/* turbopackIgnore: true */ doc.filePath)) notFound();
    const content = fs.readFileSync(/* turbopackIgnore: true */ doc.filePath, "utf8");

    return (
        <div className="min-h-screen bg-[var(--bi-canvas)] text-[var(--bi-text-1)]">
            <div className="max-w-3xl mx-auto px-4 py-10 sm:py-14">
                {/* Header */}
                <div className="flex items-center gap-2.5 mb-8 pb-6 border-b border-[var(--bi-border)]">
                    <Link href="/" className="flex items-center gap-2.5 hover:opacity-80 transition-opacity">
                        <div className="w-7 h-7 rounded-lg bg-[var(--bi-teal)] flex items-center justify-center">
                            <Activity className="w-3.5 h-3.5 text-black" />
                        </div>
                        <span className="text-base font-semibold tracking-tight">Vektra BI</span>
                    </Link>
                    <span className="text-[10px] text-[var(--bi-text-3)] uppercase tracking-wider ml-1">/ Legal</span>
                </div>

                {/* Contenido del documento */}
                <article className="markdown-content prose-invert max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
                </article>

                {/* Footer legal nav */}
                <nav className="mt-12 pt-6 border-t border-[var(--bi-border)] flex flex-wrap gap-4 text-xs text-[var(--bi-text-2)]">
                    <Link href="/legal/privacidad" className="hover:text-[var(--bi-teal)] transition-colors">Política de Privacidad</Link>
                    <span aria-hidden>·</span>
                    <Link href="/legal/terminos" className="hover:text-[var(--bi-teal)] transition-colors">Términos de Uso</Link>
                    <span aria-hidden>·</span>
                    <Link href="/legal/cookies" className="hover:text-[var(--bi-teal)] transition-colors">Cookies</Link>
                </nav>
            </div>
        </div>
    );
}
