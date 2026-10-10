import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MessageItem } from '@/components/chat/MessageItem';

vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => (
    <div data-testid="markdown">{children}</div>
  ),
}));

vi.mock('remark-gfm', () => ({
  default: () => {},
}));

vi.mock('next/dynamic', () => ({
  __esModule: true,
  default: () => {
    const MockComponent = () => <div data-testid="plotly-mock" />;
    MockComponent.displayName = 'MockPlot';
    return MockComponent;
  },
}));

vi.mock('../AutoDashGrid', () => ({
  default: () => <div data-testid="autodash-grid" />,
}));

describe('MessageItem', () => {
  const defaultProps = {
    userId: 'test-user',
    handleExportPng: vi.fn(),
    handlePin: vi.fn(),
  };

  it('renderiza un mensaje de usuario', () => {
    const msg = { id: 1, role: 'user' as const, content: 'Hola desde el usuario' };
    render(<MessageItem msg={msg} {...defaultProps} />);
    expect(screen.getByText('Hola desde el usuario')).toBeInTheDocument();
  });

  it('renderiza un mensaje del asistente', () => {
    const msg = { id: 2, role: 'assistant' as const, content: 'Respuesta del asistente' };
    render(<MessageItem msg={msg} {...defaultProps} />);
    expect(screen.getByText('Respuesta del asistente')).toBeInTheDocument();
  });

  it('renderiza mensaje con gráfico (fig)', () => {
    const msg = {
      id: 3,
      role: 'assistant' as const,
      content: 'Aquí tienes el gráfico',
      fig: { data: [{ x: [1, 2], y: [3, 4] }], layout: { title: 'Test' } },
    };
    render(<MessageItem msg={msg} {...defaultProps} />);
    expect(screen.getByText('Visualización')).toBeInTheDocument();
    expect(screen.getByTestId('plotly-mock')).toBeInTheDocument();
  });

  it('muestra badge de anomalía para contenido con ⚠️', () => {
    const msg = { id: 4, role: 'assistant' as const, content: '⚠️ Se detectó una anomalía' };
    render(<MessageItem msg={msg} {...defaultProps} />);
    expect(screen.getByText('Anomalía detectada')).toBeInTheDocument();
  });

  it('muestra badge de anomalía para Auditor de Datos', () => {
    const msg = { id: 5, role: 'assistant' as const, content: 'Auditor de Datos: análisis completo' };
    render(<MessageItem msg={msg} {...defaultProps} />);
    expect(screen.getByText('Anomalía detectada')).toBeInTheDocument();
  });

  it('renderiza botones CTA para mensajes del asistente', () => {
    const msg = { id: 6, role: 'assistant' as const, content: 'Las ventas aumentaron 20%' };
    render(
      <MessageItem
        msg={msg}
        {...defaultProps}
        handleSendAsQuery={vi.fn()}
      />
    );
    expect(screen.getByText('Simular ROI de ventas')).toBeInTheDocument();
    expect(screen.getByText('Ver tendencia de ventas')).toBeInTheDocument();
  });

  it('muestra botón de pin cuando msg.id existe', () => {
    const msg = {
      id: 7,
      role: 'assistant' as const,
      content: 'test',
      fig: { data: [], layout: {} },
    };
    render(<MessageItem msg={msg} {...defaultProps} />);
    const pinButtons = screen.getAllByTitle('Anclar al panel');
    expect(pinButtons.length).toBeGreaterThanOrEqual(1);
  });
});
