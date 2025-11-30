import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../../services/api';
import type { AdminStats } from '../../types';
import './AdminDashboard.css';

export default function AdminDashboard() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const data = await api.getAdminStats();
      setStats(data);
    } catch (err) {
      console.error('Failed to load stats:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="loading-page">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className="admin-dashboard">
      <h1>Admin Dashboard</h1>

      <div className="admin-stats-grid">
        <div className="stat-card">
          <span className="stat-value">{stats?.total_users || 0}</span>
          <span className="stat-label">Total Users</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{stats?.total_addons || 0}</span>
          <span className="stat-label">Total Addons</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{stats?.total_versions || 0}</span>
          <span className="stat-label">Total Versions</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{stats?.active_subscriptions || 0}</span>
          <span className="stat-label">Active Subscriptions</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{stats?.recent_signups || 0}</span>
          <span className="stat-label">Signups (7 days)</span>
        </div>
      </div>

      {stats?.users_by_tier && (
        <div className="admin-card">
          <h2>Users by Tier</h2>
          <div className="tier-breakdown">
            {Object.entries(stats.users_by_tier).map(([tier, count]) => (
              <div key={tier} className="tier-item">
                <span className={`tier-badge tier-${tier}`}>{tier.toUpperCase()}</span>
                <span className="tier-count">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="admin-nav">
        <h2>Quick Actions</h2>
        <div className="admin-nav-grid">
          <Link to="/admin/users" className="admin-nav-item">
            <span className="nav-icon">👥</span>
            <span className="nav-label">Manage Users</span>
          </Link>
          <Link to="/admin/addons" className="admin-nav-item">
            <span className="nav-icon">📦</span>
            <span className="nav-label">Manage Addons</span>
          </Link>
          <Link to="/admin/tickets" className="admin-nav-item">
            <span className="nav-icon">🎫</span>
            <span className="nav-label">Support Tickets</span>
          </Link>
          <Link to="/admin/canned-responses" className="admin-nav-item">
            <span className="nav-icon">📝</span>
            <span className="nav-label">Canned Responses</span>
          </Link>
          <Link to="/admin/audit-log" className="admin-nav-item">
            <span className="nav-icon">📋</span>
            <span className="nav-label">Audit Log</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
