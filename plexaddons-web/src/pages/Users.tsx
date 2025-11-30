import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import './Users.css';

interface PublicUser {
  discord_id: string;
  discord_username: string;
  discord_avatar: string | null;
  subscription_tier: string;
  profile_slug: string | null;
  badges: string[];
  bio: string | null;
  addon_count: number;
  created_at: string;
}

const TIER_COLORS: Record<string, string> = {
  free: '#666',
  pro: '#f59e0b',
  premium: '#8b5cf6',
};

const BADGE_LABELS: Record<string, string> = {
  staff: '🛡️ Staff',
  supporter: '💎 Supporter',
  premium: '👑 Premium',
  early_adopter: '🌟 Early Adopter',
  beta_tester: '🧪 Beta Tester',
  addon_creator: '🔧 Addon Creator',
  contributor: '🤝 Contributor',
};

export default function Users() {
  const [users, setUsers] = useState<PublicUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const perPage = 24;

  useEffect(() => {
    loadUsers();
  }, [page]);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const response = await api.listPublicUsers(page, perPage, search || undefined);
      setUsers(response.users);
      setTotal(response.total);
    } catch (err) {
      setError('Failed to load users');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadUsers();
  };

  const getAvatarUrl = (user: PublicUser) => {
    if (user.discord_avatar) {
      return `https://cdn.discordapp.com/avatars/${user.discord_id}/${user.discord_avatar}.png?size=128`;
    }
    return `https://cdn.discordapp.com/embed/avatars/${parseInt(user.discord_id) % 5}.png`;
  };

  const getProfileUrl = (user: PublicUser) => {
    return `/u/${user.profile_slug || user.discord_id}`;
  };

  const isStaff = (user: PublicUser) => user.badges?.includes('staff');

  const totalPages = Math.ceil(total / perPage);

  if (loading && users.length === 0) {
    return (
      <div className="loading-page">
        <div className="spinner" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-page">
        <p>{error}</p>
        <button onClick={loadUsers} className="btn btn-primary">
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="users-page">
      <div className="users-header">
        <h1>Community</h1>
        <p>Browse PlexAddons community members</p>
      </div>

      <form className="users-search" onSubmit={handleSearch}>
        <input
          type="text"
          placeholder="Search users..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="search-input"
        />
        <button type="submit" className="btn btn-primary">Search</button>
      </form>

      {users.length === 0 ? (
        <div className="no-users">
          <p>No users found{search && ` matching "${search}"`}</p>
        </div>
      ) : (
        <>
          <div className="users-grid">
            {users.map(user => (
              <Link
                key={user.discord_id}
                to={getProfileUrl(user)}
                className="user-card"
              >
                <img 
                  src={getAvatarUrl(user)} 
                  alt={user.discord_username}
                  className="user-avatar"
                />
                <div className="user-info">
                  <div className="user-name-row">
                    <h3 className="user-name">{user.discord_username}</h3>
                    <span 
                      className="user-tier"
                      style={{ 
                        backgroundColor: isStaff(user) ? '#ef4444' : TIER_COLORS[user.subscription_tier] 
                      }}
                    >
                      {isStaff(user) ? 'Admin' : user.subscription_tier.charAt(0).toUpperCase() + user.subscription_tier.slice(1)}
                    </span>
                  </div>
                  
                  {user.badges && user.badges.length > 0 && (
                    <div className="user-badges">
                      {user.badges.slice(0, 3).map((badge, i) => (
                        <span key={i} className="user-badge" title={BADGE_LABELS[badge] || badge}>
                          {BADGE_LABELS[badge]?.split(' ')[0] || '🏅'}
                        </span>
                      ))}
                      {user.badges.length > 3 && (
                        <span className="user-badge-more">+{user.badges.length - 3}</span>
                      )}
                    </div>
                  )}
                  
                  {user.bio && (
                    <p className="user-bio">{user.bio}</p>
                  )}
                  
                  <div className="user-stats">
                    <span className="user-stat">
                      📦 {user.addon_count} addon{user.addon_count !== 1 ? 's' : ''}
                    </span>
                  </div>
                </div>
              </Link>
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
                Page {page} of {totalPages}
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
