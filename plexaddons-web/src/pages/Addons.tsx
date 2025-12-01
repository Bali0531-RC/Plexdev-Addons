import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import type { Addon, AddonTag } from '../types';
import { ADDON_TAGS } from '../types';
import './Addons.css';

export default function Addons() {
  const [addons, setAddons] = useState<Addon[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [selectedTag, setSelectedTag] = useState<AddonTag | null>(null);

  useEffect(() => {
    loadAddons();
  }, [selectedTag]);

  const loadAddons = async () => {
    try {
      setLoading(true);
      const response = await api.listAddons(1, 100, undefined, selectedTag || undefined);
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

      <div className="tags-filter">
        <button
          className={`tag-chip ${selectedTag === null ? 'active' : ''}`}
          onClick={() => setSelectedTag(null)}
        >
          All
        </button>
        {ADDON_TAGS.map(tag => (
          <button
            key={tag.value}
            className={`tag-chip ${selectedTag === tag.value ? 'active' : ''}`}
            onClick={() => setSelectedTag(tag.value)}
            title={tag.description}
          >
            {tag.label}
          </button>
        ))}
      </div>

      {filteredAddons.length === 0 ? (
        <div className="no-addons">
          <p>No addons found{search && ` matching "${search}"`}{selectedTag && ` in ${ADDON_TAGS.find(t => t.value === selectedTag)?.label}`}</p>
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
                <h3>
                  {addon.name}
                  {addon.verified && (
                    <span className="verified-badge" title="Verified by PlexDevelopment">✓</span>
                  )}
                </h3>
                {addon.latest_version && (
                  <span className="addon-version">v{addon.latest_version}</span>
                )}
              </div>
              {addon.description && (
                <p className="addon-description">{addon.description}</p>
              )}
              {addon.tags && addon.tags.length > 0 && (
                <div className="addon-tags">
                  {addon.tags.slice(0, 3).map(tag => (
                    <span key={tag} className="addon-tag">
                      {ADDON_TAGS.find(t => t.value === tag)?.label || tag}
                    </span>
                  ))}
                  {addon.tags.length > 3 && (
                    <span className="addon-tag addon-tag-more">+{addon.tags.length - 3}</span>
                  )}
                </div>
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
