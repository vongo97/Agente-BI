import fs from "fs";
import path from "path";
import { notFound } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Link from "next/link";
import { Activity } from "lucide-react";

// Fuentes legales: docs/legal/*.md en la raíz del repositorio
const LEGAL_DOCS: Record<string, { file: string; title: string }> = {
    "privacidad":   { file: "politica-privacidad.md", title: "Política de Privacidad" },
    "terminos":     { file: "terminos-de-uso.md",     title: "Términos y Condiciones de Uso" },
    "cookies":      { file: "aviso-cookies.md",       title: "Aviso de Cookies" },
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

    const filePath = path.join(process.cwd(), "..", "docs", "legal", doc.file);
    if (!fs.existsSync(filePath)) notFound();
    const content = fs.readFileSync(filePath, "utf8");

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
