import { Outlet, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Layout.css';

export default function Layout() {
  const { user, isAuthenticated, isAdmin, login, logout } = useAuth();
  const location = useLocation();

  const getDiscordAvatar = () => {
    if (!user?.discord_avatar) {
      return `https://cdn.discordapp.com/embed/avatars/${parseInt(user?.discord_id || '0') % 5}.png`;
    }
    return `https://cdn.discordapp.com/avatars/${user.discord_id}/${user.discord_avatar}.png`;
  };

  return (
    <div className="layout">
      <div className="migration-banner">
        <span>🔄</span>
        <span>
          <strong>Domain Migration:</strong> We've moved from plexdev.live to plexdev.xyz! 
          Update your bookmarks. The old domain will redirect here until it expires (~60 days).
        </span>
      </div>
      <header className="header">
        <div className="container header-content">
          <Link to="/" className="logo">
            <span className="logo-icon">📦</span>
            <span className="logo-text">PlexAddons</span>
          </Link>

          <nav className="nav">
            <Link to="/addons" className={location.pathname === '/addons' ? 'active' : ''}>
              Addons
            </Link>
            <Link to="/users" className={location.pathname === '/users' ? 'active' : ''}>
              Users
            </Link>
            <Link to="/docs" className={location.pathname === '/docs' ? 'active' : ''}>
              Docs
            </Link>
            <Link to="/pricing" className={location.pathname === '/pricing' ? 'active' : ''}>
              Pricing
            </Link>
            {isAuthenticated && (
              <Link to="/dashboard" className={location.pathname.startsWith('/dashboard') ? 'active' : ''}>
                Dashboard
              </Link>
            )}
            {isAdmin && (
              <Link to="/admin" className={location.pathname.startsWith('/admin') ? 'active' : ''}>
                Admin
              </Link>
            )}
          </nav>

          <div className="header-actions">
            {isAuthenticated ? (
              <div className="user-menu">
                <img src={getDiscordAvatar()} alt={user?.discord_username} className="avatar" />
                <span className="username">{user?.discord_username}</span>
                <svg className="arrow" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
                <div className="dropdown">
                  <Link to="/dashboard">Dashboard</Link>
                  <Link to="/dashboard/analytics">Analytics</Link>
                  <Link to="/dashboard/support">Support</Link>
                  <Link to="/dashboard/settings">Settings</Link>
                  {isAdmin && <Link to="/admin">Admin Panel</Link>}
                  <button onClick={logout}>Logout</button>
                </div>
              </div>
            ) : (
              <button onClick={() => login()} className="btn btn-primary">
                Login with Discord
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="main">
        <Outlet />
      </main>

      <footer className="footer">
        <div className="container footer-content">
          <div className="footer-left">
            <span>© 2025 PlexAddons</span>
            <span className="separator">•</span>
            <span className="version-badge alpha">Alpha</span>
            <span className="separator">•</span>
            <span className="build-info">v0.2.1 · Build {__BUILD_TIME__}</span>
          </div>
          <div className="footer-right">
            <Link to="/terms">Terms</Link>
            <Link to="/privacy">Privacy</Link>
            <Link to="/billing">Billing</Link>
            <Link to="/acceptable-use">Acceptable Use</Link>
            <Link to="/takedown">Takedown</Link>
            <Link to="/legal">Legal</Link>
            <a href="/redocs" target="_blank" rel="noopener noreferrer">
              API Docs
            </a>
            <a href="https://github.com/Bali0531-RC/Plexdev-Addons" target="_blank" rel="noopener noreferrer">
              GitHub
            </a>
            <a href="https://discord.gg/plexdev" target="_blank" rel="noopener noreferrer">
              Discord
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
