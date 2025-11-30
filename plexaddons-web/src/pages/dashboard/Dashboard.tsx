import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import type { StorageInfo, Addon } from '../../types';
import './Dashboard.css';

export default function Dashboard() {
  const { user } = useAuth();
  const [storage, setStorage] = useState<StorageInfo | null>(null);
  const [recentAddons, setRecentAddons] = useState<Addon[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      const [storageData, addonsData] = await Promise.all([
        api.getMyStorage(),
        api.listMyAddons(1, 5),
      ]);
      setStorage(storageData);
      setRecentAddons(addonsData.addons);
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes >= 1024 * 1024 * 1024) {
      return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
    }
    if (bytes >= 1024 * 1024) {
      return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    }
    if (bytes >= 1024) {
      return `${(bytes / 1024).toFixed(2)} KB`;
    }
    return `${bytes} B`;
  };

  const getTierBadgeClass = (tier: string, isAdmin?: boolean) => {
    if (isAdmin) return 'badge-admin';
    switch (tier) {
      case 'premium': return 'badge-premium';
      case 'pro': return 'badge-pro';
      default: return 'badge-free';
    }
  };

  const getTierLabel = (tier: string, isAdmin?: boolean) => {
    if (isAdmin) return 'ADMIN';
    return tier?.toUpperCase() || 'FREE';
  };

  if (loading) {
    return (
      <div className="loading-page">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div className="welcome">
          <h1>Welcome, {user?.discord_username || 'User'}</h1>
          <span className={`badge ${getTierBadgeClass(user?.subscription_tier || 'free', user?.is_admin)}`}>
            {getTierLabel(user?.subscription_tier || 'free', user?.is_admin)}
          </span>
        </div>
        <Link to="/dashboard/addons/new" className="btn btn-primary">
          + New Addon
        </Link>
      </div>

      <div className="dashboard-grid">
        {/* Storage Card */}
        <div className="dashboard-card storage-card">
          <h2>Storage Usage</h2>
          {storage && (
            <>
              <div className="storage-bar">
                <div 
                  className="storage-bar-fill" 
                  style={{ width: user?.is_admin ? '0%' : `${Math.min(storage.storage_used_percent, 100)}%` }}
                />
              </div>
              <div className="storage-info">
                <span>
                  {formatBytes(storage.storage_used_bytes)} / {user?.is_admin ? '∞' : formatBytes(storage.storage_quota_bytes)}
                </span>
                <span>{user?.is_admin ? 'Unlimited' : `${storage.storage_used_percent.toFixed(1)}%`}</span>
              </div>
              <div className="storage-stats">
                <div className="stat">
                  <span className="stat-value">{storage.addon_count}</span>
                  <span className="stat-label">Addons</span>
                </div>
                <div className="stat">
                  <span className="stat-value">{storage.version_count}</span>
                  <span className="stat-label">Versions</span>
                </div>
              </div>
            </>
          )}
          {!user?.is_admin && user?.subscription_tier === 'free' && (
            <Link to="/pricing" className="upgrade-link">
              Upgrade for more storage →
            </Link>
          )}
        </div>

        {/* Recent Addons Card */}
        <div className="dashboard-card addons-card">
          <div className="card-header">
            <h2>Recent Addons</h2>
            <Link to="/dashboard/addons" className="view-all">View All</Link>
          </div>
          {recentAddons.length === 0 ? (
            <div className="empty-state">
              <p>No addons yet</p>
              <Link to="/dashboard/addons/new" className="btn btn-secondary">
                Create your first addon
              </Link>
            </div>
          ) : (
            <div className="addon-list">
              {recentAddons.map(addon => (
                <Link 
                  key={addon.id} 
                  to={`/dashboard/addons/${addon.slug}`}
                  className="addon-list-item"
                >
                  <div className="addon-list-info">
                    <span className="addon-list-name">{addon.name}</span>
                    {addon.latest_version && (
                      <span className="addon-list-version">v{addon.latest_version}</span>
                    )}
                  </div>
                  <span className="addon-list-count">{addon.version_count} versions</span>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Quick Actions Card */}
        <div className="dashboard-card actions-card">
          <h2>Quick Actions</h2>
          <div className="actions-list">
            <Link to="/dashboard/addons/new" className="action-item">
              <span className="action-icon">📦</span>
              <span>Create Addon</span>
            </Link>
            <Link to="/dashboard/support" className="action-item">
              <span className="action-icon">🎫</span>
              <span>Support</span>
            </Link>
            <Link to="/dashboard/settings" className="action-item">
              <span className="action-icon">⚙️</span>
              <span>Settings</span>
            </Link>
            <Link to="/dashboard/subscription" className="action-item">
              <span className="action-icon">💳</span>
              <span>Subscription</span>
            </Link>
            {user?.is_admin && (
              <Link to="/admin" className="action-item">
                <span className="action-icon">🛡️</span>
                <span>Admin Panel</span>
              </Link>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
