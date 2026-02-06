import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { User } from '../types';
import { api } from '../services/api';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isAdmin: boolean;
  login: (token?: string, userData?: User) => void;
  logout: () => void;
  setUser: (user: User | null) => void;
  /** @internal - only for use by AuthCallback */
  _setToken: (token: string) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = 'plexaddons_token';
const OAUTH_STATE_KEY = 'plexaddons_oauth_state';

function validateOAuthState(state: string | null): boolean {
  if (!state) return false;
  const stored = sessionStorage.getItem(OAUTH_STATE_KEY);
  sessionStorage.removeItem(OAUTH_STATE_KEY);
  return stored === state;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) {
      api.setToken(token);
      loadUser();
    } else {
      setIsLoading(false);
    }
  }, []);

  const loadUser = async () => {
    try {
      const userData = await api.getMe();
      setUser(userData);
    } catch (error) {
      console.error('Failed to load user:', error);
      localStorage.removeItem(TOKEN_KEY);
      api.setToken(null);
    } finally {
      setIsLoading(false);
    }
  };

  const login = (token?: string, userData?: User) => {
    if (token && userData) {
      // Called from OAuth callback with token and user data
      localStorage.setItem(TOKEN_KEY, token);
      api.setToken(token);
      setUser(userData);
    } else {
      // Redirect to Discord OAuth with CSRF state parameter
      api.getAuthUrl().then(({ url, state: serverState }) => {
        // Store state for validation on callback
        sessionStorage.setItem(OAUTH_STATE_KEY, serverState);
        if (!/^https:\/\/(discord\.com|discordapp\.com)\//i.test(url)) {
          console.error('Blocked redirect to untrusted OAuth URL');
          return;
        }
        window.location.href = url;
      }).catch((error) => {
        console.error('Failed to get auth URL:', error);
      });
    }
  };

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY);
    api.setToken(null);
    setUser(null);
    window.location.href = '/';
  };

  const _setToken = (token: string) => {
    localStorage.setItem(TOKEN_KEY, token);
    api.setToken(token);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        isAdmin: user?.is_admin || false,
        login,
        logout,
        setUser,
        _setToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export { OAUTH_STATE_KEY, validateOAuthState };

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
