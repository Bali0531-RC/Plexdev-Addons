import { useState, useEffect } from 'react';
import { api } from '../../services/api';
import type { User } from '../../types';
import './AdminUsers.css';

export default function AdminUsers() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [tierFilter, setTierFilter] = useState('');
  const perPage = 20;

  useEffect(() => {
    loadUsers();
  }, [page, search, tierFilter]);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const response = await api.listUsers(
        page, 
        perPage, 
        search || undefined, 
        tierFilter || undefined
      );
      setUsers(response.users);
      setTotal(response.total);
    } catch (err) {
      console.error('Failed to load users:', err);
    } finally {
      setLoading(false);
    }
  };

  const handlePromote = async (userId: number) => {
    if (!confirm('Are you sure you want to promote this user to admin?')) return;
    try {
      await api.promoteToAdmin(userId);
      loadUsers();
    } catch (err) {
      console.error('Failed to promote user:', err);
      alert('Failed to promote user');
    }
  };

  const handleDemote = async (userId: number) => {
    if (!confirm('Are you sure you want to remove admin privileges?')) return;
    try {
      await api.demoteFromAdmin(userId);
      loadUsers();
    } catch (err) {
      console.error('Failed to demote user:', err);
      alert('Failed to demote user');
    }
  };

  const handleUpdateTier = async (userId: number, tier: string) => {
    try {
      await api.updateUser(userId, { subscription_tier: tier });
      loadUsers();
    } catch (err) {
      console.error('Failed to update tier:', err);
      alert('Failed to update tier');
    }
  };

  const totalPages = Math.ceil(total / perPage);

  const formatBytes = (bytes: number) => {
    if (bytes >= 1024 * 1024 * 1024) {
      return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
    }
    if (bytes >= 1024 * 1024) {
      return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    }
    return `${(bytes / 1024).toFixed(2)} KB`;
  };

  return (
    <div className="admin-users">
      <h1>Manage Users</h1>

      <div className="users-filters">
        <input
          type="text"
          placeholder="Search users..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="search-input"
        />
        <select 
          value={tierFilter} 
          onChange={(e) => { setTierFilter(e.target.value); setPage(1); }}
          className="tier-filter"
        >
          <option value="">All Tiers</option>
          <option value="free">Free</option>
          <option value="pro">Pro</option>
          <option value="premium">Premium</option>
        </select>
      </div>

      {loading && users.length === 0 ? (
        <div className="loading-page">
          <div className="spinner" />
        </div>
      ) : (
        <>
          <div className="users-table">
            <div className="table-header">
              <span>User</span>
              <span>Tier</span>
              <span>Storage</span>
              <span>Admin</span>
              <span>Actions</span>
            </div>
            {users.map(user => (
              <div key={user.id} className="table-row">
                <div className="user-info">
                  <span className="user-name">{user.discord_username}</span>
                  <span className="user-id">{user.discord_id}</span>
                </div>
                <span>
                  <select
                    value={user.subscription_tier}
                    onChange={(e) => handleUpdateTier(user.id, e.target.value)}
                    className="tier-select"
                  >
                    <option value="free">Free</option>
                    <option value="pro">Pro</option>
                    <option value="premium">Premium</option>
                  </select>
                </span>
                <span className="storage-info">
                  {formatBytes(user.storage_used_bytes)} / {formatBytes(user.storage_quota_bytes)}
                </span>
                <span>
                  {user.is_admin ? (
                    <span className="admin-badge">Admin</span>
                  ) : '-'}
                </span>
                <span className="user-actions">
                  {user.is_admin ? (
                    <button 
                      onClick={() => handleDemote(user.id)}
                      className="btn btn-sm btn-danger"
                    >
                      Demote
                    </button>
                  ) : (
                    <button 
                      onClick={() => handlePromote(user.id)}
                      className="btn btn-sm btn-secondary"
                    >
                      Promote
                    </button>
                  )}
                </span>
              </div>
            ))}
          </div>

          {totalPages > 1 && (
            <div className="pagination">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="btn btn-secondary"
              >
                Previous
              </button>
              <span className="page-info">
                Page {page} of {totalPages} ({total} users)
              </span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="btn btn-secondary"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
