import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ChatSuggestions } from '@/components/chat/ChatSuggestions';

describe('ChatSuggestions', () => {
  const defaultProps = {
    showAiSuggestions: true,
    loadingSuggestions: false,
    suggestions: [],
    setInput: vi.fn(),
    handleSendAsQuery: vi.fn(),
    fetchSuggestions: vi.fn(),
  };

  it('retorna null cuando showAiSuggestions es false', () => {
    const { container } = render(
      <ChatSuggestions {...defaultProps} showAiSuggestions={false} />
    );
    expect(container.innerHTML).toBe('');
  });

  it('muestra spinner cuando loadingSuggestions es true', () => {
    render(<ChatSuggestions {...defaultProps} loadingSuggestions={true} />);
    expect(screen.getByText('Generando sugerencias…')).toBeInTheDocument();
  });

  it('renderiza lista de sugerencias', () => {
    const suggestions = ['Pregunta 1', 'Pregunta 2', 'Pregunta 3'];
    render(<ChatSuggestions {...defaultProps} suggestions={suggestions} />);
    expect(screen.getByText('Pregunta 1')).toBeInTheDocument();
    expect(screen.getByText('Pregunta 2')).toBeInTheDocument();
    expect(screen.getByText('Pregunta 3')).toBeInTheDocument();
  });

  it('llama a setInput y handleSendAsQuery al hacer clic en sugerencia', () => {
    vi.useFakeTimers();
    const setInput = vi.fn();
    const handleSendAsQuery = vi.fn();
    render(
      <ChatSuggestions
        {...defaultProps}
        suggestions={['Sugerencia de prueba']}
        setInput={setInput}
        handleSendAsQuery={handleSendAsQuery}
      />
    );

    fireEvent.click(screen.getByText('Sugerencia de prueba'));

    expect(setInput).toHaveBeenCalledWith('Sugerencia de prueba');

    vi.advanceTimersByTime(80);
    expect(handleSendAsQuery).toHaveBeenCalledWith('Sugerencia de prueba');

    vi.useRealTimers();
  });

  it('muestra botón de regenerar sugerencias cuando hay sugerencias', () => {
    render(
      <ChatSuggestions {...defaultProps} suggestions={['Pregunta 1']} />
    );
    expect(screen.getByTitle('Regenerar sugerencias')).toBeInTheDocument();
  });

  it('llama a fetchSuggestions al hacer clic en regenerar', () => {
    const fetchSuggestions = vi.fn();
    render(
      <ChatSuggestions
        {...defaultProps}
        suggestions={['Pregunta']}
        fetchSuggestions={fetchSuggestions}
      />
    );
    fireEvent.click(screen.getByTitle('Regenerar sugerencias'));
    expect(fetchSuggestions).toHaveBeenCalledTimes(1);
  });

  it('muestra botón de sugerir análisis cuando la lista está vacía', () => {
    render(<ChatSuggestions {...defaultProps} suggestions={[]} />);
    expect(
      screen.getByText('Sugerir análisis sobre mis datos')
    ).toBeInTheDocument();
  });

  it('muestra el título de la sección', () => {
    render(
      <ChatSuggestions {...defaultProps} suggestions={['Pregunta 1']} />
    );
    expect(screen.getByText('Preguntas sugeridas')).toBeInTheDocument();
  });
});
