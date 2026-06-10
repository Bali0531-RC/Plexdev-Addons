import { useState, useRef, useEffect } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { PackageIcon, RefreshIcon, MenuIcon, XIcon, ChevronDownIcon } from './Icons';
import './Layout.css';

export default function Layout() {
  const { user, isAuthenticated, isAdmin, login, logout } = useAuth();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const [navOpen, setNavOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  // Close menus on navigation
  useEffect(() => {
    setMenuOpen(false);
    setNavOpen(false);
  }, [location.pathname]);

  // Close the user menu on outside click or Escape
  useEffect(() => {
    if (!menuOpen) return;
    const onClick = (e: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMenuOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [menuOpen]);

  const getDiscordAvatar = () => {
    if (!user?.discord_avatar) {
      return `https://cdn.discordapp.com/embed/avatars/${parseInt(user?.discord_id || '0') % 5}.png`;
    }
    return `https://cdn.discordapp.com/avatars/${user.discord_id}/${user.discord_avatar}.png`;
  };

  const navLinks = (
    <>
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
    </>
  );

  return (
    <div className="layout">
      <div className="migration-banner">
        <RefreshIcon className="banner-icon" />
        <span>
          <strong>Domain migration:</strong> We've moved from plexdev.live to plexdev.xyz.
          Update your bookmarks — the old domain will redirect here until it expires (~60 days).
        </span>
      </div>
      <header className="header">
        <div className="container header-content">
          <Link to="/" className="logo">
            <PackageIcon className="logo-icon" />
            <span className="logo-text">PlexAddons</span>
          </Link>

          <nav className="nav">{navLinks}</nav>

          <div className="header-actions">
            {isAuthenticated ? (
              <div className={`user-menu${menuOpen ? ' open' : ''}`} ref={userMenuRef}>
                <button
                  type="button"
                  className="user-menu-trigger"
                  aria-haspopup="menu"
                  aria-expanded={menuOpen}
                  onClick={() => setMenuOpen((open) => !open)}
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
            <button
              type="button"
              className="nav-toggle"
              aria-label={navOpen ? 'Close menu' : 'Open menu'}
              aria-expanded={navOpen}
              onClick={() => setNavOpen((open) => !open)}
            >
              {navOpen ? <XIcon /> : <MenuIcon />}
            </button>
          </div>
        </div>
        {navOpen && <nav className="nav-mobile">{navLinks}</nav>}
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
