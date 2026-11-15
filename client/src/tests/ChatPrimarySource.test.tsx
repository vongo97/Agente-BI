import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor } from '@testing-library/react';
import { Chat } from '@/components/Chat';

const api = vi.hoisted(() => ({
  analyzeData: vi.fn(),
  pinToDashboard: vi.fn(),
  exportChartAsPng: vi.fn(),
  generateAutoDashboard: vi.fn(),
  suggestQuestions: vi.fn(),
  cleanData: vi.fn(),
  runAudit: vi.fn(),
}));

const dashboard = vi.hoisted(() => ({
  apiKey: 'key-test',
  mistralKey: '',
  aiProvider: 'gemini',
  dataSources: [] as { id?: number; filename: string; columns: string[] }[],
  setDataSources: vi.fn(),
  setSidebarOpen: vi.fn(),
  messages: [] as { role: string; content: string }[],
  setMessages: vi.fn(),
  activeChatId: null as number | null,
  setActiveChatId: vi.fn(),
  suggestions: [] as string[],
  setSuggestions: vi.fn(),
  loadingSuggestions: false,
  setLoadingSuggestions: vi.fn(),
  showAiSuggestions: true,
  autoSuggestionsEnabled: false,
}));

vi.mock('@/lib/api', () => api);

vi.mock('next-auth/react', () => ({
  useSession: () => ({
    data: { user: { email: 'user@test.com', name: 'Test' } },
    status: 'authenticated',
  }),
}));

vi.mock('@/context/DashboardContext', () => ({
  useDashboard: () => dashboard,
}));

vi.mock('@/context/ToastContext', () => ({
  useToast: () => ({ addToast: vi.fn() }),
}));

describe('Chat · P-29 · fuente principal unificada', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.suggestQuestions.mockResolvedValue({ suggestions: [] });
    dashboard.messages = [];
    dashboard.suggestions = [];
    dashboard.activeChatId = null;
    dashboard.autoSuggestionsEnabled = false;
    // Dos fuentes distintas: la primera es la principal (así la devuelve el
    // backend en `data_source`), la segunda es una secundaria.
    dashboard.dataSources = [
      { id: 111, filename: 'principal.csv', columns: ['a'] },
      { id: 222, filename: 'secundaria.csv', columns: ['b'] },
    ];
  });

  it('las sugerencias se generan sobre la PRIMERA fuente, no sobre la última', async () => {
    render(<Chat />);

    await waitFor(() => {
      expect(api.suggestQuestions).toHaveBeenCalled();
    });

    const [, , sourceId] = api.suggestQuestions.mock.calls[0];
    // Antes del fix se usaba dataSources[dataSources.length - 1].id === 222.
    expect(sourceId).toBe(111);
  });

  it('la fuente principal enviada al análisis es la misma que la de las sugerencias', async () => {
    api.analyzeData.mockResolvedValue({
      chat_id: 7,
      message_id: 9,
      analysis: 'ok',
      figure: null,
    });

    const { getByPlaceholderText } = render(<Chat />);

    await waitFor(() => {
      expect(api.suggestQuestions).toHaveBeenCalled();
    });

    const input = getByPlaceholderText(/pregunta|consulta|escribe/i as unknown as RegExp);
    const { fireEvent } = await import('@testing-library/react');
    fireEvent.change(input, { target: { value: '¿cuánto vendimos?' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

    await waitFor(() => {
      expect(api.analyzeData).toHaveBeenCalled();
    });

    // analyzeData(query, apiKey, userId, chatId, mainSourceId, provider, mistralKey, sourceIds)
    const call = api.analyzeData.mock.calls[0];
    const mainSourceId = call[4];
    const sourceIds = call[7];

    expect(mainSourceId).toBe(111);
    // La fuente principal debe estar incluida en la lista de fuentes
    // seleccionadas: el backend lo exige (analysis.py:82).
    expect(sourceIds).toContain(111);
  });
});
