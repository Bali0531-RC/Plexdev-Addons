import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

const mockUseAuth = vi.fn();
vi.mock('../context/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

import AdminRoute from './AdminRoute';

function renderAdmin(path = '/admin') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/login" element={<div>Login Page</div>} />
        <Route path="/dashboard" element={<div>Dashboard</div>} />
        <Route element={<AdminRoute />}>
          <Route path="/admin" element={<div>Admin Panel</div>} />
        </Route>
      </Routes>
    </MemoryRouter>
  );
}

describe('AdminRoute', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows spinner while loading', () => {
    mockUseAuth.mockReturnValue({ user: null, isAuthenticated: false, isLoading: true });
    const { container } = renderAdmin();
    expect(container.querySelector('.spinner')).toBeInTheDocument();
  });

  it('redirects to login when not authenticated', () => {
    mockUseAuth.mockReturnValue({ user: null, isAuthenticated: false, isLoading: false });
    renderAdmin();
    expect(screen.getByText('Login Page')).toBeInTheDocument();
  });

  it('redirects to dashboard when authenticated but not admin', () => {
    mockUseAuth.mockReturnValue({
      user: { is_admin: false },
      isAuthenticated: true,
      isLoading: false,
    });
    renderAdmin();
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
  });

  it('renders admin content when authenticated as admin', () => {
    mockUseAuth.mockReturnValue({
      user: { is_admin: true },
      isAuthenticated: true,
      isLoading: false,
    });
    renderAdmin();
    expect(screen.getByText('Admin Panel')).toBeInTheDocument();
  });
});
