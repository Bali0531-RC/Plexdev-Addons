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
                <div className="dropdown">
                  <Link to="/dashboard">Dashboard</Link>
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
            <span className="build-info">v0.1.1 · Build {__BUILD_TIME__}</span>
          </div>
          <div className="footer-right">
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
