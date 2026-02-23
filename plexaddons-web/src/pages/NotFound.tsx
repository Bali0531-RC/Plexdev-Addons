import { Link } from 'react-router-dom';

export default function NotFound() {
  return (
    <div className="container" style={{ 
      textAlign: 'center', 
      padding: '4rem 1rem',
      maxWidth: '600px',
      margin: '0 auto',
    }}>
      <h1 style={{ fontSize: '4rem', marginBottom: '0.5rem', color: 'var(--text-muted)' }}>404</h1>
      <h2 style={{ marginBottom: '1rem' }}>Page Not Found</h2>
      <p style={{ color: 'var(--text-muted)', marginBottom: '2rem' }}>
        The page you're looking for doesn't exist or has been moved.
      </p>
      <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
        <Link to="/" className="btn btn-primary">Go Home</Link>
        <Link to="/addons" className="btn btn-secondary">Browse Addons</Link>
      </div>
    </div>
  );
}
