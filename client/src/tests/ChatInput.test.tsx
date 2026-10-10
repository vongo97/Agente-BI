import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ChatInput } from '@/components/chat/ChatInput';

describe('ChatInput', () => {
  const defaultProps = {
    input: '',
    setInput: vi.fn(),
    handleSend: vi.fn(),
    loading: false,
    dataSourcesCount: 1,
  };

  it('renderiza el textarea con placeholder correcto', () => {
    render(<ChatInput {...defaultProps} />);
    expect(
      screen.getByPlaceholderText(/Escribe tu pregunta sobre los datos/)
    ).toBeInTheDocument();
  });

  it('deshabilita el textarea cuando no hay fuentes de datos', () => {
    render(<ChatInput {...defaultProps} dataSourcesCount={0} />);
    const textarea = screen.getByPlaceholderText(/Sube un archivo de datos/);
    expect(textarea).toBeDisabled();
  });

  it('llama a setInput al escribir en el textarea', () => {
    const setInput = vi.fn();
    render(<ChatInput {...defaultProps} setInput={setInput} />);
    const textarea = screen.getByPlaceholderText(/Escribe tu pregunta/);
    fireEvent.change(textarea, { target: { value: 'consulta de prueba' } });
    expect(setInput).toHaveBeenCalledWith('consulta de prueba');
  });

  it('llama a handleSend al hacer clic en el botón enviar', () => {
    const handleSend = vi.fn();
    render(<ChatInput {...defaultProps} input="test" handleSend={handleSend} />);
    const button = screen.getByTitle('Enviar consulta');
    expect(button).not.toBeDisabled();
    fireEvent.click(button);
    expect(handleSend).toHaveBeenCalledTimes(1);
  });

  it('deshabilita el botón enviar cuando el input está vacío', () => {
    render(<ChatInput {...defaultProps} input="" />);
    expect(screen.getByTitle('Enviar consulta')).toBeDisabled();
  });

  it('deshabilita el botón enviar cuando está cargando', () => {
    render(<ChatInput {...defaultProps} input="test" loading={true} />);
    expect(screen.getByTitle('Enviar consulta')).toBeDisabled();
  });

  it('deshabilita el botón enviar sin fuentes de datos', () => {
    render(<ChatInput {...defaultProps} input="test" dataSourcesCount={0} />);
    expect(screen.getByTitle('Enviar consulta')).toBeDisabled();
  });

  it('envía con Enter sin Shift', () => {
    const handleSend = vi.fn();
    render(<ChatInput {...defaultProps} input="test" handleSend={handleSend} />);
    const textarea = screen.getByPlaceholderText(/Escribe tu pregunta/);
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false });
    expect(handleSend).toHaveBeenCalledTimes(1);
  });

  it('no envía con Shift+Enter', () => {
    const handleSend = vi.fn();
    render(<ChatInput {...defaultProps} input="test" handleSend={handleSend} />);
    const textarea = screen.getByPlaceholderText(/Escribe tu pregunta/);
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true });
    expect(handleSend).not.toHaveBeenCalled();
  });

  it('muestra spinner cuando está cargando', () => {
    render(<ChatInput {...defaultProps} input="test" loading={true} />);
    const button = screen.getByTitle('Enviar consulta');
    expect(button.querySelector('svg')).toBeInTheDocument();
  });

  it('muestra el texto de pie de página', () => {
    render(<ChatInput {...defaultProps} />);
    expect(screen.getByText('Vektra BI · Precision Analysis Engine')).toBeInTheDocument();
  });
});
