import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

const mockSetToken = vi.fn();
const mockLogin = vi.fn();
const mockNavigate = vi.fn();

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    _setToken: mockSetToken,
    login: mockLogin,
  }),
  OAUTH_STATE_KEY: 'plexaddons_oauth_state',
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock('../services/api', () => ({
  api: {
    getMe: vi.fn().mockResolvedValue({ id: 1, discord_username: 'test' }),
  },
}));

import AuthCallback from '../pages/AuthCallback';

function renderCallback(search: string) {
  return render(
    <MemoryRouter initialEntries={[`/auth/callback${search}`]}>
      <AuthCallback />
    </MemoryRouter>
  );
}

describe('AuthCallback', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  it('shows error when error param present', async () => {
    renderCallback('?error=access_denied');
    await waitFor(() => {
      expect(screen.getByText(/access_denied/)).toBeInTheDocument();
    });
  });

  it('shows error when no token received', async () => {
    renderCallback('');
    await waitFor(() => {
      expect(screen.getByText(/No authorization token received/)).toBeInTheDocument();
    });
  });

  it('shows spinner while processing', () => {
    renderCallback('?token=jwt123&state=abc');
    expect(screen.getByText('Signing you in...')).toBeInTheDocument();
  });

  it('rejects mismatched state', async () => {
    sessionStorage.setItem('plexaddons_oauth_state', 'expected_state');
    renderCallback('?token=jwt123&state=wrong_state');
    await waitFor(() => {
      expect(screen.getByText(/state mismatch/)).toBeInTheDocument();
    });
  });

  it('cleans up sessionStorage on error', async () => {
    sessionStorage.setItem('plexaddons_oauth_state', 'some_state');
    renderCallback('?error=access_denied');
    await waitFor(() => {
      expect(sessionStorage.getItem('plexaddons_oauth_state')).toBeNull();
    });
  });
});
