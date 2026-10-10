import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ChatHeader } from '@/components/chat/ChatHeader';

describe('ChatHeader', () => {
  const defaultProps = {
    setSidebarOpen: vi.fn(),
    dataSources: [],
    cleaningData: false,
    handleCleanData: vi.fn(),
    loadingAutoDash: false,
    handleAutoDash: vi.fn(),
    messages: [],
    setReportBuilderOpen: vi.fn(),
    activeChatId: null,
    userId: 'test-user',
    handleNewChat: vi.fn(),
    aiProvider: 'gemini',
  };

  it('renderiza el nombre del asistente', () => {
    render(<ChatHeader {...defaultProps} />);
    expect(screen.getByText('Analista BI')).toBeInTheDocument();
  });

  it('renderiza el badge del proveedor Gemini', () => {
    render(<ChatHeader {...defaultProps} />);
    expect(screen.getByText('Gemini 2.5')).toBeInTheDocument();
  });

  it('renderiza botón de nuevo chat', () => {
    render(<ChatHeader {...defaultProps} />);
    expect(screen.getByTitle('Iniciar nueva conversación')).toBeInTheDocument();
  });

  it('muestra botones de datos cuando hay fuentes', () => {
    render(
      <ChatHeader
        {...defaultProps}
        dataSources={[{ filename: 'test.csv', columns: ['a', 'b'] }]}
      />
    );
    expect(screen.getByTitle('Magic Clean — limpia y normaliza el dataset con IA')).toBeInTheDocument();
    expect(screen.getByTitle('Auto-Dashboard — genera panel automático con métricas clave')).toBeInTheDocument();
  });

  it('no muestra botones de datos sin fuentes', () => {
    render(<ChatHeader {...defaultProps} />);
    expect(screen.queryByTitle(/Magic Clean/)).not.toBeInTheDocument();
    expect(screen.queryByTitle(/Auto-Dashboard/)).not.toBeInTheDocument();
  });

  it('muestra botón de informe cuando hay mensajes', () => {
    render(
      <ChatHeader
        {...defaultProps}
        messages={[{ id: 1, role: 'user', content: 'Hola' }]}
      />
    );
    expect(screen.getByTitle('Generar informe ejecutivo desde esta conversación')).toBeInTheDocument();
  });

  it('muestra botón PDF cuando hay un chat activo', () => {
    render(<ChatHeader {...defaultProps} activeChatId={42} />);
    expect(screen.getByTitle('Exportar conversación como PDF')).toBeInTheDocument();
  });

  it('deshabilita botón PDF durante descarga', () => {
    render(<ChatHeader {...defaultProps} activeChatId={42} />);
    const pdfBtn = screen.getByTitle('Exportar conversación como PDF');
    expect(pdfBtn).not.toBeDisabled();
  });
});
