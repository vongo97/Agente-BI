'use client';

import { Sun, Moon } from 'lucide-react';
import { useTheme } from '@/context/ThemeContext';

export function ThemeToggle() {
    const { theme, toggleTheme } = useTheme();

    return (
        <button
            onClick={toggleTheme}
            className="group relative p-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 hover:border-blue-500/30 transition-all duration-300"
            aria-label="Toggle theme"
        >
            <div className="relative w-5 h-5">
                {/* Sun icon */}
                <Sun
                    className={`absolute inset-0 w-5 h-5 transition-all duration-500 ${theme === 'light'
                            ? 'rotate-0 scale-100 opacity-100 text-amber-500'
                            : 'rotate-90 scale-0 opacity-0 text-gray-500'
                        }`}
                />
                {/* Moon icon */}
                <Moon
                    className={`absolute inset-0 w-5 h-5 transition-all duration-500 ${theme === 'dark'
                            ? 'rotate-0 scale-100 opacity-100 text-blue-400'
                            : '-rotate-90 scale-0 opacity-0 text-gray-500'
                        }`}
                />
            </div>

            {/* Tooltip */}
            <div className="absolute left-full ml-3 top-1/2 -translate-y-1/2 px-3 py-1.5 bg-black/90 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap">
                {theme === 'dark' ? 'Modo Claro' : 'Modo Oscuro'}
            </div>
        </button>
    );
}
