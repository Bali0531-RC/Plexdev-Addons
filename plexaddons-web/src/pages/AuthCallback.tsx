import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import './AuthCallback.css';

export default function AuthCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { login, setToken, setUser } = useAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    handleCallback();
  }, []);

  const handleCallback = async () => {
    const token = searchParams.get('token');
    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const errorParam = searchParams.get('error');

    if (errorParam) {
      setError(`Authentication failed: ${errorParam}`);
      return;
    }

    // If we have a token directly (from API redirect), use it
    if (token) {
      try {
        setToken(token);
        const user = await api.getMe();
        setUser(user);
        navigate('/dashboard', { replace: true });
      } catch (err) {
        console.error('Token validation error:', err);
        setError('Failed to validate authentication token. Please try again.');
      }
      return;
    }

    // If we have a code, exchange it for a token
    if (code) {
      try {
        const response = await api.handleCallback(code, state || undefined);
        login(response.access_token, response.user);
        navigate('/dashboard', { replace: true });
      } catch (err) {
        console.error('Auth callback error:', err);
        setError('Failed to complete authentication. Please try again.');
      }
      return;
    }

    setError('No authorization code or token received');
  };

  if (error) {
    return (
      <div className="callback-page">
        <div className="callback-card callback-error">
          <h1>Authentication Failed</h1>
          <p>{error}</p>
          <button onClick={() => navigate('/login')} className="btn btn-primary">
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="callback-page">
      <div className="callback-card">
        <h1>Signing you in...</h1>
        <div className="spinner" />
      </div>
    </div>
  );
}
