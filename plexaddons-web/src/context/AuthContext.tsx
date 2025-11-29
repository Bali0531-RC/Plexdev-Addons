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
  setToken: (token: string) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = 'plexaddons_token';

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
      // Redirect to Discord OAuth
      api.getAuthUrl().then(({ url }) => {
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

  const setToken = (token: string) => {
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
        setToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
