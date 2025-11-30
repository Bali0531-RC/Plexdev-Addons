import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { api } from '../../services/api';
import type { User } from '../../types';
import './AdminUsers.css';

interface TempTierModal {
  userId: number;
  username: string;
  currentTier: string;
}

interface BadgeModal {
  userId: number;
  username: string;
  badges: string[];
}

const AVAILABLE_BADGES = [
  'supporter',
  'premium',
  'addon_creator',
  'early_adopter',
  'contributor',
  'beta_tester',
  'bug_hunter',
  'top_contributor',
];

export default function AdminUsers() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [tierFilter, setTierFilter] = useState('');
  const perPage = 20;

  // Temp tier modal state
  const [tempTierModal, setTempTierModal] = useState<TempTierModal | null>(null);
  const [tempTier, setTempTier] = useState('pro');
  const [tempDays, setTempDays] = useState(7);
  const [tempReason, setTempReason] = useState('');

  // Badge modal state
  const [badgeModal, setBadgeModal] = useState<BadgeModal | null>(null);
  const [newBadge, setNewBadge] = useState('');

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
    toast.promise(
      api.promoteToAdmin(userId).then(() => loadUsers()),
      {
        loading: 'Promoting user...',
        success: 'User promoted to admin',
        error: 'Failed to promote user',
      }
    );
  };

  const handleDemote = async (userId: number) => {
    toast.promise(
      api.demoteFromAdmin(userId).then(() => loadUsers()),
      {
        loading: 'Removing admin privileges...',
        success: 'Admin privileges removed',
        error: 'Failed to demote user',
      }
    );
  };

  const handleUpdateTier = async (userId: number, tier: string) => {
    toast.promise(
      api.updateUser(userId, { subscription_tier: tier }).then(() => loadUsers()),
      {
        loading: 'Updating tier...',
        success: `Tier updated to ${tier}`,
        error: 'Failed to update tier',
      }
    );
  };

  const openTempTierModal = (user: User) => {
    setTempTierModal({
      userId: user.id,
      username: user.discord_username,
      currentTier: user.subscription_tier,
    });
    // Set default temp tier to one level above current
    const tierOrder = ['free', 'pro', 'premium'];
    const currentIndex = tierOrder.indexOf(user.subscription_tier);
    setTempTier(tierOrder[Math.min(currentIndex + 1, 2)]);
    setTempDays(7);
    setTempReason('');
  };

  const handleGrantTempTier = async () => {
    if (!tempTierModal) return;
    
    toast.promise(
      api.grantTempTier(tempTierModal.userId, tempTier, tempDays, tempReason || undefined)
        .then(() => {
          setTempTierModal(null);
          loadUsers();
        }),
      {
        loading: 'Granting temporary tier...',
        success: `Granted ${tempTier} tier for ${tempDays} days`,
        error: (err) => err.message || 'Failed to grant temporary tier',
      }
    );
  };

  const handleRevokeTempTier = async (userId: number) => {
    toast.promise(
      api.revokeTempTier(userId).then(() => loadUsers()),
      {
        loading: 'Revoking temporary tier...',
        success: 'Temporary tier revoked',
        error: 'Failed to revoke temporary tier',
      }
    );
  };

  const openBadgeModal = async (user: User) => {
    try {
      const { badges } = await api.getUserBadges(user.id);
      setBadgeModal({
        userId: user.id,
        username: user.discord_username,
        badges: badges || [],
      });
      setNewBadge('');
    } catch (err) {
      toast.error('Failed to load user badges');
    }
  };

  const handleAddBadge = async () => {
    if (!badgeModal || !newBadge) return;
    
    toast.promise(
      api.addUserBadge(badgeModal.userId, newBadge).then(({ badges }) => {
        setBadgeModal(prev => prev ? { ...prev, badges } : null);
        setNewBadge('');
      }),
      {
        loading: 'Adding badge...',
        success: `Badge "${newBadge}" added`,
        error: 'Failed to add badge',
      }
    );
  };

  const handleRemoveBadge = async (badge: string) => {
    if (!badgeModal) return;
    
    toast.promise(
      api.removeUserBadge(badgeModal.userId, badge).then(({ badges }) => {
        setBadgeModal(prev => prev ? { ...prev, badges } : null);
      }),
      {
        loading: 'Removing badge...',
        success: `Badge "${badge}" removed`,
        error: 'Failed to remove badge',
      }
    );
  };

  const formatTempTierExpiry = (expiresAt: string) => {
    const expires = new Date(expiresAt);
    const now = new Date();
    const diffMs = expires.getTime() - now.getTime();
    const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffDays <= 0) return 'Expired';
    if (diffDays === 1) return '1 day left';
    return `${diffDays} days left`;
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

  const formatStorage = (user: User) => {
    const used = formatBytes(user.storage_used_bytes);
    if (user.is_admin) {
      return `${used} / ∞`;
    }
    return `${used} / ${formatBytes(user.storage_quota_bytes)}`;
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
              <span>Temp Tier</span>
              <span>Storage</span>
              <span>Admin</span>
              <span>Badges</span>
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
                <span className="temp-tier-cell">
                  {user.temp_tier && user.temp_tier_expires_at ? (
                    <div className="temp-tier-info">
                      <span className={`temp-tier-badge tier-${user.temp_tier}`}>
                        {user.temp_tier.toUpperCase()}
                      </span>
                      <span className="temp-tier-expiry">
                        {formatTempTierExpiry(user.temp_tier_expires_at)}
                      </span>
                      <button
                        onClick={() => handleRevokeTempTier(user.id)}
                        className="btn btn-xs btn-danger"
                        title="Revoke temporary tier"
                      >
                        ×
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => openTempTierModal(user)}
                      className="btn btn-xs btn-outline"
                      disabled={user.subscription_tier === 'premium'}
                      title={user.subscription_tier === 'premium' ? 'Already Premium' : 'Grant temporary tier'}
                    >
                      + Grant
                    </button>
                  )}
                </span>
                <span className="storage-info">
                  {formatStorage(user)}
                </span>
                <span>
                  {user.is_admin ? (
                    <span className="admin-badge">Admin</span>
                  ) : '-'}
                </span>
                <span className="badges-cell">
                  <button
                    onClick={() => openBadgeModal(user)}
                    className="btn btn-xs btn-outline"
                    title="Manage badges"
                  >
                    🏷️ {user.badges?.length || 0}
                  </button>
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

      {/* Grant Temp Tier Modal */}
      {tempTierModal && (
        <div className="modal-overlay" onClick={() => setTempTierModal(null)}>
          <div className="modal temp-tier-modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Grant Temporary Tier</h2>
              <button className="modal-close" onClick={() => setTempTierModal(null)}>×</button>
            </div>
            <div className="modal-body">
              <p className="modal-info">
                Granting temporary tier to <strong>{tempTierModal.username}</strong>
                <br />
                <small>Current tier: {tempTierModal.currentTier}</small>
              </p>

              <div className="form-group">
                <label>Tier to Grant</label>
                <select 
                  value={tempTier} 
                  onChange={e => setTempTier(e.target.value)}
                  className="form-input"
                >
                  {tempTierModal.currentTier === 'free' && (
                    <>
                      <option value="pro">Pro</option>
                      <option value="premium">Premium</option>
                    </>
                  )}
                  {tempTierModal.currentTier === 'pro' && (
                    <option value="premium">Premium</option>
                  )}
                </select>
              </div>

              <div className="form-group">
                <label>Duration</label>
                <div className="duration-options">
                  <button 
                    className={`duration-btn ${tempDays === 7 ? 'active' : ''}`}
                    onClick={() => setTempDays(7)}
                  >
                    7 days
                  </button>
                  <button 
                    className={`duration-btn ${tempDays === 14 ? 'active' : ''}`}
                    onClick={() => setTempDays(14)}
                  >
                    14 days
                  </button>
                  <button 
                    className={`duration-btn ${tempDays === 30 ? 'active' : ''}`}
                    onClick={() => setTempDays(30)}
                  >
                    30 days
                  </button>
                  <button 
                    className={`duration-btn ${tempDays === 90 ? 'active' : ''}`}
                    onClick={() => setTempDays(90)}
                  >
                    90 days
                  </button>
                </div>
                <div className="custom-duration">
                  <input
                    type="number"
                    value={tempDays}
                    onChange={e => setTempDays(Math.max(1, Math.min(365, parseInt(e.target.value) || 1)))}
                    min={1}
                    max={365}
                    className="form-input"
                  />
                  <span>days</span>
                </div>
              </div>

              <div className="form-group">
                <label>Reason (optional)</label>
                <input
                  type="text"
                  value={tempReason}
                  onChange={e => setTempReason(e.target.value)}
                  placeholder="e.g., Contest winner, Beta tester..."
                  className="form-input"
                />
              </div>
            </div>
            <div className="modal-footer">
              <button 
                className="btn btn-secondary" 
                onClick={() => setTempTierModal(null)}
              >
                Cancel
              </button>
              <button 
                className="btn btn-primary" 
                onClick={handleGrantTempTier}
              >
                Grant {tempTier.charAt(0).toUpperCase() + tempTier.slice(1)} for {tempDays} days
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Badge Management Modal */}
      {badgeModal && (
        <div className="modal-overlay" onClick={() => setBadgeModal(null)}>
          <div className="modal badge-modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Manage Badges</h2>
              <button className="modal-close" onClick={() => setBadgeModal(null)}>×</button>
            </div>
            <div className="modal-body">
              <p className="modal-info">
                Managing badges for <strong>{badgeModal.username}</strong>
              </p>

              <div className="current-badges">
                <label>Current Badges</label>
                {badgeModal.badges.length === 0 ? (
                  <p className="no-badges">No badges assigned</p>
                ) : (
                  <div className="badge-list">
                    {badgeModal.badges.map(badge => (
                      <span key={badge} className={`badge badge-${badge}`}>
                        {badge.replace(/_/g, ' ')}
                        <button 
                          className="badge-remove"
                          onClick={() => handleRemoveBadge(badge)}
                          title="Remove badge"
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <div className="form-group">
                <label>Add Badge</label>
                <div className="add-badge-row">
                  <select
                    value={newBadge}
                    onChange={e => setNewBadge(e.target.value)}
                    className="form-input"
                  >
                    <option value="">Select a badge...</option>
                    {AVAILABLE_BADGES.filter(b => !badgeModal.badges.includes(b)).map(badge => (
                      <option key={badge} value={badge}>
                        {badge.replace(/_/g, ' ')}
                      </option>
                    ))}
                  </select>
                  <button
                    className="btn btn-primary"
                    onClick={handleAddBadge}
                    disabled={!newBadge}
                  >
                    Add
                  </button>
                </div>
                <div className="custom-badge-row">
                  <input
                    type="text"
                    value={newBadge}
                    onChange={e => setNewBadge(e.target.value)}
                    placeholder="Or enter custom badge name..."
                    className="form-input"
                  />
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button 
                className="btn btn-secondary" 
                onClick={() => setBadgeModal(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
