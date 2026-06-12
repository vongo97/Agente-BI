'use client';

import { Sun, Moon } from 'lucide-react';
import { useTheme } from '@/context/ThemeContext';

export function ThemeToggle() {
    const { theme, toggleTheme } = useTheme();
    const isDark = theme === 'dark';

    return (
        <button
            onClick={toggleTheme}
            className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-md text-xs font-medium text-[var(--bi-text-2)] hover:text-[var(--bi-text-1)] hover:bg-[var(--bi-surface-1)] border border-[var(--bi-border)] transition-colors"
            aria-label={isDark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
            title={isDark ? 'Modo claro' : 'Modo oscuro'}
        >
            {isDark
                ? <Sun className="w-3.5 h-3.5 text-[var(--bi-amber)]" />
                : <Moon className="w-3.5 h-3.5 text-[var(--bi-blue)]" />
            }
            <span>{isDark ? 'Modo claro' : 'Modo oscuro'}</span>
        </button>
    );
}
