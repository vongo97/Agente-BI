import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { DashboardProvider, useDashboard } from '@/context/DashboardContext';

const mocks = vi.hoisted(() => ({
  sessionData: {
    user: { email: 'user@test.com', name: 'Test' },
    accessToken: 'access-token',
  } as { user: { email: string; name: string }; accessToken: string } | null,
  getUserConfig: vi.fn(),
  setUserConfig: vi.fn(),
  setApiAuthToken: vi.fn(),
}));

vi.mock('next-auth/react', () => ({
  useSession: () => ({ data: mocks.sessionData }),
}));

vi.mock('@/lib/api', () => ({
  BACKEND_BASE_URL: 'https://api.test',
  getUserConfig: mocks.getUserConfig,
  setUserConfig: mocks.setUserConfig,
  setApiAuthToken: mocks.setApiAuthToken,
}));

vi.mock('@/context/ToastContext', () => ({
  useToast: () => ({ addToast: vi.fn() }),
}));

function ConfigProbe() {
  const { temperature, setTemperature } = useDashboard();
  return (
    <>
      <output data-testid="temperature">{temperature}</output>
      <button onClick={() => setTemperature(0.7)}>change temperature</button>
    </>
  );
}

describe('DashboardProvider config hydration', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    localStorage.clear();
    mocks.sessionData = {
      user: { email: 'user@test.com', name: 'Test' },
      accessToken: 'access-token',
    };
    mocks.getUserConfig.mockReset();
    mocks.setUserConfig.mockReset().mockResolvedValue(undefined);
    mocks.setApiAuthToken.mockReset();
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true }));
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('does not autosave defaults while the server configuration is still loading', async () => {
    let resolveConfig!: (value: Record<string, unknown>) => void;
    mocks.getUserConfig.mockReturnValue(new Promise((resolve) => { resolveConfig = resolve; }));

    render(
      <DashboardProvider>
        <ConfigProbe />
      </DashboardProvider>,
    );

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2_000);
    });
    expect(mocks.setUserConfig).not.toHaveBeenCalled();

    await act(async () => {
      resolveConfig({ temperature: 0.7, report_org_name: 'Acme Analytics' });
      await Promise.resolve();
    });
    expect(screen.getByTestId('temperature')).toHaveTextContent('0.7');

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_200);
    });
    expect(mocks.setUserConfig).toHaveBeenCalledTimes(1);
    expect(mocks.setUserConfig.mock.calls[0][0]).toBe('user@test.com');
    expect(mocks.setUserConfig.mock.calls[0][6]).toBe(0.7);
  });

  it('keeps autosave disabled if loading the server configuration fails', async () => {
    const error = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    mocks.getUserConfig.mockRejectedValue(new Error('network unavailable'));

    render(
      <DashboardProvider>
        <ConfigProbe />
      </DashboardProvider>,
    );

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2_000);
    });
    expect(mocks.setUserConfig).not.toHaveBeenCalled();
    error.mockRestore();
  });

  it('autosaves user changes after successful hydration', async () => {
    mocks.getUserConfig.mockResolvedValue({ temperature: 0.2 });

    render(
      <DashboardProvider>
        <ConfigProbe />
      </DashboardProvider>,
    );

    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    fireEvent.click(screen.getByRole('button', { name: 'change temperature' }));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_200);
    });
    expect(mocks.setUserConfig).toHaveBeenCalled();
    expect(mocks.setUserConfig.mock.calls.at(-1)?.[6]).toBe(0.7);
  });
});
