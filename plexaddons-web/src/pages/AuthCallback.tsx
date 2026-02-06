import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import './AuthCallback.css';

export default function AuthCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { _setToken, login } = useAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    handleCallback();
  }, []);

  const handleCallback = async () => {
    const token = searchParams.get('token');
    const errorParam = searchParams.get('error');

    if (errorParam) {
      setError(`Authentication failed: ${errorParam}`);
      return;
    }

    // The backend already exchanged the Discord code and created a JWT.
    // It redirects here with ?token=JWT — we just need to store it and load the user.
    if (token) {
      try {
        _setToken(token);
        const user = await api.getMe();
        login(token, user);
        navigate('/dashboard', { replace: true });
      } catch (err) {
        console.error('Auth callback error:', err);
        setError('Failed to complete authentication. Please try again.');
      }
      return;
    }

    setError('No authorization token received');
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
