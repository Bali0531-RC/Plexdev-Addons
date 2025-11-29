import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Home.css';

export default function Home() {
  const { isAuthenticated } = useAuth();

  return (
    <div className="home">
      <section className="hero">
        <h1>PlexAddons</h1>
        <p className="hero-subtitle">
          Manage your addon versions, changelogs, and releases with ease
        </p>
        <div className="hero-actions">
          {isAuthenticated ? (
            <Link to="/dashboard" className="btn btn-primary">
              Go to Dashboard
            </Link>
          ) : (
            <>
              <Link to="/login" className="btn btn-primary">
                Get Started
              </Link>
              <Link to="/addons" className="btn btn-secondary">
                Browse Addons
              </Link>
            </>
          )}
        </div>
      </section>

      <section className="features">
        <h2>Why PlexAddons?</h2>
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">📦</div>
            <h3>Version Management</h3>
            <p>Track all your addon versions with semantic versioning support and detailed changelogs.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🔄</div>
            <h3>Auto Updates</h3>
            <p>Compatible with PlexInstaller for automatic version checking and updates.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🔐</div>
            <h3>Discord Auth</h3>
            <p>Simple login with your Discord account. No new passwords to remember.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📊</div>
            <h3>Storage Quotas</h3>
            <p>Free tier included. Upgrade to Pro or Premium for more storage and features.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🌐</div>
            <h3>API Access</h3>
            <p>RESTful API for integration with your tools and CI/CD pipelines.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📜</div>
            <h3>Changelog History</h3>
            <p>Keep track of changes across versions. Free users get 5 versions, Pro 10, Premium unlimited.</p>
          </div>
        </div>
      </section>

      <section className="cta">
        <h2>Ready to get started?</h2>
        <p>Create your free account today and start managing your addons.</p>
        {!isAuthenticated && (
          <Link to="/login" className="btn btn-primary btn-large">
            Sign in with Discord
          </Link>
        )}
      </section>
    </div>
  );
}
