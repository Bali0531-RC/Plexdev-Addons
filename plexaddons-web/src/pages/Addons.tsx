import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import type { Addon } from '../types';
import './Addons.css';

export default function Addons() {
  const [addons, setAddons] = useState<Addon[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  useEffect(() => {
    loadAddons();
  }, []);

  const loadAddons = async () => {
    try {
      setLoading(true);
      const response = await api.listAddons();
      setAddons(response.addons);
    } catch (err) {
      setError('Failed to load addons');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const filteredAddons = addons.filter(addon =>
    addon.name.toLowerCase().includes(search.toLowerCase()) ||
    addon.description?.toLowerCase().includes(search.toLowerCase())
  );

  if (loading) {
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
        <button onClick={loadAddons} className="btn btn-primary">
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="addons-page">
      <div className="addons-header">
        <h1>Browse Addons</h1>
        <p>Discover addons available through PlexAddons</p>
      </div>

      <div className="addons-search">
        <input
          type="text"
          placeholder="Search addons..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="search-input"
        />
      </div>

      {filteredAddons.length === 0 ? (
        <div className="no-addons">
          <p>No addons found{search && ` matching "${search}"`}</p>
        </div>
      ) : (
        <div className="addons-grid">
          {filteredAddons.map(addon => (
            <Link
              key={addon.id}
              to={`/addons/${addon.slug}`}
              className="addon-card"
            >
              <div className="addon-card-header">
                <h3>{addon.name}</h3>
                {addon.latest_version && (
                  <span className="addon-version">v{addon.latest_version}</span>
                )}
              </div>
              {addon.description && (
                <p className="addon-description">{addon.description}</p>
              )}
              <div className="addon-card-footer">
                {addon.external && (
                  <span className="badge badge-external">External</span>
                )}
                <span 
                  className="addon-author addon-author-link"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    if (addon.owner_discord_id) {
                      window.location.href = `/u/${addon.owner_discord_id}`;
                    }
                  }}
                >
                  by {addon.owner_username || 'Unknown'}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
