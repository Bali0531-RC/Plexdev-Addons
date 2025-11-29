import { useEffect } from 'react';
import { api } from '../services/api';
import './Login.css';

export default function Login() {
  useEffect(() => {
    // Redirect to Discord OAuth
    redirectToDiscord();
  }, []);

  const redirectToDiscord = async () => {
    try {
      const { url } = await api.getAuthUrl();
      window.location.href = url;
    } catch (err) {
      console.error('Failed to get auth URL:', err);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <h1>Sign In</h1>
        <p>Redirecting to Discord...</p>
        <div className="spinner" />
      </div>
    </div>
  );
}
