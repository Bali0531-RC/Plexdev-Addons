import { useState, useEffect, useRef } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import NotificationBell from './NotificationBell';
import { PackageIcon, ChevronDownIcon } from './Icons';
import './Layout.css';

export default function Layout() {
  const { user, isAuthenticated, isAdmin, login, logout } = useAuth();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  // Close mobile menu on route change
  useEffect(() => {
    setMenuOpen(false);
    setUserMenuOpen(false);
  }, [location.pathname]);

  // Close the user menu on outside click or Escape
  useEffect(() => {
    if (!userMenuOpen) return;
    const onClick = (e: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setUserMenuOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [userMenuOpen]);

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
            <PackageIcon className="logo-icon" />
            <span className="logo-text">PlexAddons</span>
          </Link>

          <button 
            className={`hamburger ${menuOpen ? 'open' : ''}`} 
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Toggle menu"
          >
            <span />
            <span />
            <span />
          </button>

          <nav className={`nav ${menuOpen ? 'nav-open' : ''}`}>
            <Link to="/addons" className={location.pathname === '/addons' ? 'active' : ''}>
              Addons
            </Link>
            <Link to="/categories" className={location.pathname === '/categories' || location.pathname.startsWith('/addons/category/') ? 'active' : ''}>
              Categories
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
            {isAuthenticated && <NotificationBell />}
            {isAuthenticated ? (
              <div className={`user-menu${userMenuOpen ? ' open' : ''}`} ref={userMenuRef}>
                <button
                  type="button"
                  className="user-menu-trigger"
                  aria-haspopup="menu"
                  aria-expanded={userMenuOpen}
                  onClick={() => setUserMenuOpen((open) => !open)}
                >
                  <img src={getDiscordAvatar()} alt={user?.discord_username} className="avatar" />
                  <span className="username">{user?.discord_username}</span>
                  <ChevronDownIcon className="arrow" />
                </button>
                <div className="dropdown" role="menu">
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
            <span>© {new Date().getFullYear()} PlexAddons</span>
            <span className="separator">•</span>
            <span className="version-badge alpha">Alpha</span>
            <span className="separator">•</span>
            <span className="build-info">v0.3.0 · Build {__BUILD_TIME__}</span>
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
