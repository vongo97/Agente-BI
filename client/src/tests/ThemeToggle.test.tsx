import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { screen, fireEvent } from '@testing-library/react';
import { renderWithTheme } from './test-utils';
import { ThemeToggle } from '@/components/ThemeToggle';

const origMatchMedia = window.matchMedia;

beforeEach(() => {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
});

afterEach(() => {
  window.matchMedia = origMatchMedia;
});

describe('ThemeToggle', () => {
  it('renderiza el botón de cambio de tema', () => {
    renderWithTheme(<ThemeToggle />);
    const button = screen.getByRole('button');
    expect(button).toBeInTheDocument();
  });

  it('cambia el tema al hacer clic', () => {
    renderWithTheme(<ThemeToggle />);
    const button = screen.getByRole('button');
    const initialLabel = button.getAttribute('aria-label');

    fireEvent.click(button);

    const newLabel = button.getAttribute('aria-label');
    expect(newLabel).not.toBe(initialLabel);
  });

  it('muestra el texto de modo claro por defecto (dark first)', () => {
    renderWithTheme(<ThemeToggle />);
    expect(screen.getByText('Modo oscuro')).toBeInTheDocument();
  });
});
