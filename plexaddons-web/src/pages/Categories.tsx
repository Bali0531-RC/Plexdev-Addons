import { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import type { Addon, AddonTag } from '../types';
import { ADDON_TAGS } from '../types';
import './Categories.css';
import './Addons.css';

const TAG_ICONS: Record<AddonTag, string> = {
  utility: '🔧',
  media: '🎬',
  automation: '⚙️',
  moderation: '🛡️',
  fun: '🎮',
  economy: '💰',
  music: '🎵',
  leveling: '📈',
  logging: '📋',
  integration: '🔗',
  other: '📦',
};

/** Category index — shows all tag cards */
export function CategoriesIndex() {
  const [addons, setAddons] = useState<Addon[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listAddons(1, 500).then(res => {
      setAddons(res.addons);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const countByTag = (tag: AddonTag) =>
    addons.filter(a => a.tags?.includes(tag)).length;

  if (loading) {
    return (
      <div className="loading-page">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className="categories-page">
      <div className="categories-header">
        <h1>Categories</h1>
        <p>Browse addons by category</p>
      </div>
      <div className="categories-grid">
        {ADDON_TAGS.map(tag => (
          <Link
            key={tag.value}
            to={`/addons/category/${tag.value}`}
            className="category-card"
          >
            <div className="category-icon">{TAG_ICONS[tag.value]}</div>
            <h2>{tag.label}</h2>
            <p>{tag.description}</p>
            <span className="category-count">
              {countByTag(tag.value)} addon{countByTag(tag.value) !== 1 ? 's' : ''}
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}

/** Category detail — shows addons filtered by a single tag */
export function CategoryAddons() {
  const { tag } = useParams<{ tag: string }>();
  const navigate = useNavigate();
  const [addons, setAddons] = useState<Addon[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  const tagInfo = ADDON_TAGS.find(t => t.value === tag);

  useEffect(() => {
    if (!tagInfo) {
      navigate('/categories', { replace: true });
      return;
    }
    setLoading(true);
    api.listAddons(1, 200, undefined, tag as AddonTag).then(res => {
      setAddons(res.addons);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [tag]);

  const filtered = addons.filter(a =>
    a.name.toLowerCase().includes(search.toLowerCase()) ||
    a.description?.toLowerCase().includes(search.toLowerCase())
  );

  if (loading) {
    return (
      <div className="loading-page">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className="addons-page">
      <div className="addons-header">
        <Link to="/categories" style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '0.5rem', display: 'inline-block' }}>
          ← All Categories
        </Link>
        <h1>{TAG_ICONS[tag as AddonTag] || '📦'} {tagInfo?.label || tag}</h1>
        <p>{tagInfo?.description}</p>
      </div>

      <div className="addons-search">
        <input
          type="text"
          placeholder={`Search ${tagInfo?.label || ''} addons...`}
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="search-input"
        />
      </div>

      {filtered.length === 0 ? (
        <div className="no-addons">
          <p>No addons found in this category{search && ` matching "${search}"`}</p>
        </div>
      ) : (
        <div className="addons-grid">
          {filtered.map(addon => (
            <Link key={addon.id} to={`/addons/${addon.slug}`} className="addon-card">
              <div className="addon-card-header">
                <h3 className="addon-title">
                  <span className="addon-title-text">{addon.name}</span>
                  {addon.verified && (
                    <span className="verified-badge" title="Verified by PlexDevelopment">✓</span>
                  )}
                </h3>
                {addon.latest_version && (
                  <span className="addon-version">v{addon.latest_version}</span>
                )}
              </div>
              {addon.description && <p className="addon-description">{addon.description}</p>}
              {addon.tags && addon.tags.length > 0 && (
                <div className="addon-tags">
                  {addon.tags.slice(0, 3).map(t => (
                    <span key={t} className="addon-tag">
                      {ADDON_TAGS.find(at => at.value === t)?.label || t}
                    </span>
                  ))}
                </div>
              )}
              <div className="addon-card-footer">
                {addon.external && <span className="badge badge-external">External</span>}
                <span className="addon-author">{addon.owner_username || 'Unknown'}</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
