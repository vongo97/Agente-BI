'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';

type Theme = 'light' | 'dark';

interface ThemeContextType {
    theme: Theme;
    toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: ReactNode }) {
    // P-45 · Dark-first y **consistente entre servidor y cliente**.
    //
    // Antes el estado se inicializaba con un *lazy initializer* que leía
    // `localStorage` en el primer render. En el servidor eso devuelve siempre
    // 'dark', pero en el cliente devuelve el tema guardado: si el usuario tenía
    // 'light', el HTML del servidor y el primer render del React **no
    // coincidían** → error de hidratación. Y el tema no es solo pintura: lo
    // usan `MermaidPreview` e `InteractiveCanvas` para generar markup.
    //
    // El primer render debe ser **idéntico** en servidor y cliente, así que
    // aquí siempre empieza en 'dark'. El tema guardado se aplica en el
    // `useEffect` de abajo (que corre tras la hidratación). El atributo
    // `data-theme` del `<html>` lo aplica el script inline de `layout.tsx`
    // **antes del primer pintado**, así que no hay destello.
    const [theme, setTheme] = useState<Theme>('dark');
    const [mounted, setMounted] = useState(false);

    // Leer el tema guardado DESPUÉS de la hidratación.
    useEffect(() => {
        let saved: Theme | null = null;
        try {
            const raw = localStorage.getItem('vektra-theme') as Theme | null;
            saved = (raw === 'light' || raw === 'dark') ? raw : null;
        } catch {
            // localStorage puede estar bloqueado (modo privado, permisos).
            // Se mantiene el tema por defecto en vez de romper la app.
            saved = null;
        }
        if (saved) setTheme(saved);
        setMounted(true);
    }, []);

    useEffect(() => {
        // dark = :root (no attribute needed), light = [data-theme="light"]
        document.documentElement.setAttribute('data-theme', theme);
        // No se escribe en `localStorage` hasta que la app está montada: si no,
        // el primer efecto sobrescribiría el tema guardado con 'dark'.
        if (!mounted) return;
        try {
            localStorage.setItem('vektra-theme', theme);
        } catch {
            // Sin persistencia (almacenamiento bloqueado): el tema sigue
            // funcionando en memoria, solo no se recuerda al recargar.
        }
    }, [theme, mounted]);

    const toggleTheme = () => setTheme(prev => prev === 'dark' ? 'light' : 'dark');

    return (
        <ThemeContext.Provider value={{ theme, toggleTheme }}>
            {children}
        </ThemeContext.Provider>
    );
}

export function useTheme() {
    const context = useContext(ThemeContext);
    if (!context) throw new Error('useTheme must be used within a ThemeProvider');
    return context;
}
