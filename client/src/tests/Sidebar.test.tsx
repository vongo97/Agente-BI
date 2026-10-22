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
});
