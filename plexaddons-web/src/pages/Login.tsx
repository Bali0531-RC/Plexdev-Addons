import { useEffect } from 'react';
import { api } from '../services/api';
import './Login.css';

const OAUTH_STATE_KEY = 'plexaddons_oauth_state';

export default function Login() {
  useEffect(() => {
    // Redirect to Discord OAuth
    redirectToDiscord();
  }, []);

  const redirectToDiscord = async () => {
    try {
      const { url, state } = await api.getAuthUrl();
      sessionStorage.setItem(OAUTH_STATE_KEY, state);
      if (!/^https:\/\/(discord\.com|discordapp\.com)\//i.test(url)) {
        console.error('Blocked redirect to untrusted OAuth URL');
        return;
      }
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
