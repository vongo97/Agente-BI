import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Sidebar } from '@/components/Sidebar';

const api = vi.hoisted(() => ({
  getHistory: vi.fn(),
  getChatDetails: vi.fn(),
  uploadFile: vi.fn(),
  connectSql: vi.fn(),
  connectGoogleSheets: vi.fn(),
  removeSessionSource: vi.fn(),
  runAudit: vi.fn(),
  setApiAuthToken: vi.fn(),
}));

const dashboard = vi.hoisted(() => ({
  setDataSources: vi.fn(),
  setMessages: vi.fn(),
  setActiveChatId: vi.fn(),
  setSidebarOpen: vi.fn(),
  setView: vi.fn(),
  addDataSource: vi.fn(),
  removeDataSource: vi.fn(),
}));

vi.mock('@/lib/api', () => api);

vi.mock('next-auth/react', () => ({
  useSession: () => ({
    data: { user: { email: 'user@test.com', name: 'Test' }, accessToken: 'token' },
    status: 'authenticated',
  }),
  signOut: vi.fn(),
}));

vi.mock('@/context/DashboardContext', () => ({
  useDashboard: () => ({
    dataSources: [],
    isSidebarOpen: false,
    activeChatId: null,
    view: 'chat',
    ...dashboard,
  }),
}));

vi.mock('@/context/ToastContext', () => ({
  useToast: () => ({ addToast: vi.fn() }),
}));

vi.mock('@/components/ThemeToggle', () => ({
  ThemeToggle: () => null,
}));

describe('Sidebar data source scoping', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.getHistory.mockResolvedValue([
      { id: 7, title: 'Conversación previa', created_at: '2026-10-20T00:00:00Z' },
    ]);
    api.getChatDetails.mockResolvedValue({
      messages: [],
      data_source: { id: 3, name: 'ventas.csv', columns: ['region', 'total'] },
    });
  });

  it('no precarga fuentes guardadas al iniciar sesión', async () => {
    render(<Sidebar />);

    expect(await screen.findByText('Conversación previa')).toBeInTheDocument();
    expect(api.getHistory).toHaveBeenCalledWith('user@test.com');
    expect(dashboard.setDataSources).not.toHaveBeenCalled();
  });

  it('restaura la fuente de una conversación del historial', async () => {
    render(<Sidebar />);

    fireEvent.click(await screen.findByText('Conversación previa'));

    await waitFor(() => {
      expect(api.getChatDetails).toHaveBeenCalledWith(7, 'user@test.com');
    });
    expect(dashboard.setDataSources).toHaveBeenCalledWith([
      { id: 3, filename: 'ventas.csv', columns: ['region', 'total'] },
    ]);
  });

  it('ejecuta auditoría automática tras subir el primer archivo', async () => {
    api.uploadFile.mockResolvedValue({ id: 3, filename: 'ventas.csv', columns: ['region', 'total'] });
    api.runAudit.mockResolvedValue({
      chat_id: 7,
      message_id: 11,
      analysis: 'Auditoría automática completada.',
      figure: null,
      audit: {
        insights: [],
        profile: { rows: 100, columns: 3, column_names: ['region', 'total'], source_name: 'ventas.csv' },
        definitions: [],
        methodology: [],
        source_name: 'ventas.csv',
        generated_at: '2026-10-22T00:00:00Z',
      },
    });

    render(<Sidebar />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(input).toBeDefined();
    const file = new File(['a,b\n1,2'], 'ventas.csv', { type: 'text/csv' });
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(api.runAudit).toHaveBeenCalledWith(undefined, 3);
    });
    expect(dashboard.setMessages).toHaveBeenCalledTimes(1);
    const updater = dashboard.setMessages.mock.calls[0][0];
    const result = typeof updater === 'function' ? updater([]) : updater;
    expect(result).toEqual(expect.arrayContaining([
      expect.objectContaining({ role: 'assistant', audit: expect.any(Object) }),
    ]));
  });
});
