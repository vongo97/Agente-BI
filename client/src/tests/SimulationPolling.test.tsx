import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { SimulationSandbox } from '@/components/SimulationSandbox';

const api = vi.hoisted(() => ({
  createSimulation: vi.fn(),
  getSimulations: vi.fn(),
  getSimulationDetails: vi.fn(),
  getSimulationMessages: vi.fn(),
  exportSimulationPdf: vi.fn(),
  getDataSources: vi.fn(),
  getSimulationSuggestions: vi.fn(),
  getSimulationOntology: vi.fn(),
  generateSimulationAgents: vi.fn(),
  getAiProviders: vi.fn(),
}));

const dashboard = vi.hoisted(() => ({
  apiKey: 'key-test',
  mistralKey: '',
  groqKey: '',
  aiProvider: 'gemini',
  setAiProvider: vi.fn(),
  userId: 'user@test.com',
  dataSources: [] as { id?: number; filename: string; columns: string[] }[],
  setSidebarOpen: vi.fn(),
}));

vi.mock('@/lib/api', () => api);

vi.mock('@/context/DashboardContext', () => ({
  useDashboard: () => dashboard,
}));

vi.mock('@/context/ToastContext', () => ({
  useToast: () => ({ addToast: vi.fn() }),
}));

const runningSim = {
  id: 42,
  user_id: 'user@test.com',
  title: 'Ensayo en curso',
  hypothesis: 'hipótesis',
  result_report: null,
  status: 'running',
  provider: 'gemini',
  current_round: 1,
  created_at: '2026-01-01T00:00:00.000Z',
};

/**
 * Timeout de estos tests, en ms.
 *
 * El polling corre **cada 2 s**, así que las esperas tienen que sobrevivir a
 * uno o dos ticks. El default de vitest (5000 ms) era MENOR que el timeout
 * de los `waitFor` internos (6000 ms): el test moría antes de que su propia
 * espera pudiera resolverse, y solo se notaba cuando la suite completa
 * cargaba la máquina y cada test iba más lento (los 3 tests tardaban
 * 2,5-4,3 s en aislamiento, contra un techo de 5 s).
 *
 * 20 s deja margen de sobra para el tick del polling sin convertir un
 * fallo real en un test lento: si el polling no dispara, el `waitFor` interno
 * sigue fallando a los 6 s con su mensaje propio.
 */
const TEST_TIMEOUT_MS = 20_000;

describe('SimulationSandbox · P-30 · el polling no se traga los errores', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.getSimulations.mockResolvedValue([runningSim]);
    api.getDataSources.mockResolvedValue([]);
    api.getSimulationMessages.mockResolvedValue([]);
    api.getAiProviders.mockResolvedValue({ providers: [] });
    api.getSimulationDetails.mockResolvedValue(runningSim);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  /** Carga la simulación "En Curso" del historial → arranca el polling. */
  async function startPolling() {
    render(<SimulationSandbox />);
    const item = await screen.findByText('Ensayo en curso');
    fireEvent.click(item);
    // loadSim es async: espera a que el polling quede montado.
    await waitFor(() => expect(api.getSimulationMessages).toHaveBeenCalled());
  }

  it('un fallo de red durante el polling se registra en vez de quedar en silencio', async () => {
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    // El detalle de la simulación falla por red.
    api.getSimulationDetails.mockRejectedValue(new Error('Failed to fetch'));

    await startPolling();

    // El polling corre cada 2 s. Esperamos a que dispare al menos una vez.
    await waitFor(() => {
      expect(api.getSimulationDetails).toHaveBeenCalled();
    }, { timeout: 6000 });

    // El error queda registrado con console.error: no se traga en silencio.
    await waitFor(() => {
      expect(errorSpy).toHaveBeenCalledWith(
        'Error en el polling de la simulación',
        expect.anything(),
      );
    }, { timeout: 6000 });
    errorSpy.mockRestore();
  }, TEST_TIMEOUT_MS);

  it('el polling sigue activo tras un fallo: el interval no se cancela', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    api.getSimulationDetails.mockRejectedValue(new Error('Failed to fetch'));

    await startPolling();

    await waitFor(() => {
      expect(api.getSimulationDetails).toHaveBeenCalled();
    }, { timeout: 6000 });
    const callsAfterFirstTick = api.getSimulationDetails.mock.calls.length;
    expect(callsAfterFirstTick).toBeGreaterThan(0);

    // Esperamos el siguiente tick: el interval debe seguir vivo.
    await waitFor(() => {
      expect(api.getSimulationDetails.mock.calls.length).toBeGreaterThan(callsAfterFirstTick);
    }, { timeout: 6000 });
  }, TEST_TIMEOUT_MS);

  it('el fallo del polling se muestra al usuario en la interfaz', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    api.getSimulationDetails.mockRejectedValue(new Error('Failed to fetch'));

    await startPolling();

    // El aviso visible para el usuario (no una promesa rechazada sin manejar).
    const alert = await screen.findByRole('alert', undefined, { timeout: 6000 });
    expect(alert).toHaveTextContent(/Se perdió la conexión con la simulación/i);
  }, TEST_TIMEOUT_MS);
});
