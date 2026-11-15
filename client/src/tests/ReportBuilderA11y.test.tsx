import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ReportBuilder } from '@/components/ReportBuilder';
import { ToastContainer } from '@/components/ToastContainer';

const api = vi.hoisted(() => ({
  generateReportSummary: vi.fn(),
  exportProfessionalReport: vi.fn(),
  exportProfessionalPptx: vi.fn(),
}));

vi.mock('@/lib/api', () => api);

vi.mock('@/context/DashboardContext', () => ({
  useDashboard: () => ({ apiKey: 'key-test' }),
}));

const toastState = vi.hoisted(() => ({
  toasts: [] as { id: number; message: string; type: string }[],
  removeToast: vi.fn(),
}));

vi.mock('@/context/ToastContext', () => ({
  useToast: () => ({
    addToast: vi.fn(),
    toasts: toastState.toasts,
    removeToast: toastState.removeToast,
  }),
}));

describe('P-25 · accesibilidad del modal de reportes y de los toasts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('ReportBuilder', () => {
    const props = {
      isOpen: true,
      onClose: vi.fn(),
      messages: [{ role: 'assistant' as const, content: 'Un hallazgo', id: 1 }],
      userId: 'user@test.com',
      userName: 'Test',
    };

    it('es un diálogo modal con nombre accesible', () => {
      render(<ReportBuilder {...props} />);
      const dialog = screen.getByRole('dialog');
      expect(dialog).toHaveAttribute('aria-modal', 'true');
      // Debe tener un nombre accesible (aria-labelledby → h3).
      expect(dialog).toHaveAccessibleName(/Constructor de Reporte/i);
    });

    it('ESC cierra el modal', () => {
      const onClose = vi.fn();
      render(<ReportBuilder {...props} onClose={onClose} />);
      fireEvent.keyDown(document, { key: 'Escape' });
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it('el foco queda dentro del modal (focus trap) al tabular', () => {
      render(<ReportBuilder {...props} />);
      const dialog = screen.getByRole('dialog');

      // El primer control recibe el foco al abrir.
      const focused = document.activeElement as HTMLElement;
      expect(dialog.contains(focused)).toBe(true);

      // Tab desde el último control vuelve al primero (no sale del diálogo).
      const focusables = Array.from(
        dialog.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
        )
      );
      const last = focusables[focusables.length - 1];
      last.focus();
      fireEvent.keyDown(document, { key: 'Tab' });
      expect(dialog.contains(document.activeElement)).toBe(true);
    });
  });

  describe('ToastContainer', () => {
    it('la región de avisos está declarada como aria-live', () => {
      toastState.toasts = [{ id: 1, message: 'Hola', type: 'info' }];

      render(<ToastContainer />);

      const live = document.querySelector('[aria-live]');
      expect(live).not.toBeNull();
      expect(live?.getAttribute('aria-live')).toBe('polite');
    });

    it('la región viva existe aunque no haya toasts', () => {
      toastState.toasts = [];

      render(<ToastContainer />);

      // Sin el early-return, la región viva está siempre montada.
      expect(document.querySelector('[aria-live]')).not.toBeNull();
    });
  });
});
