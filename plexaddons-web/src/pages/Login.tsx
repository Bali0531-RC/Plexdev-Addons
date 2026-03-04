import { useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import './Login.css';

export default function Login() {
  const { login } = useAuth();

  useEffect(() => {
    // Delegate to AuthContext.login() which handles OAuth URL, CSRF state, and redirect
    login();
  }, []);

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
