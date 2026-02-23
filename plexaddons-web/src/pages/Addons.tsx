import { useState, useEffect, useCallback } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import type { Addon, AddonTag } from '../types';
import { ADDON_TAGS } from '../types';
import './Addons.css';

type SortOption = 'updated' | 'newest' | 'oldest' | 'name_asc' | 'name_desc';

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: 'updated', label: 'Recently Updated' },
  { value: 'newest', label: 'Newest First' },
  { value: 'oldest', label: 'Oldest First' },
  { value: 'name_asc', label: 'Name (A–Z)' },
  { value: 'name_desc', label: 'Name (Z–A)' },
];

const PER_PAGE = 20;

export default function Addons() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [addons, setAddons] = useState<Addon[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  // Derive state from URL search params for shareable/bookmarkable URLs
  const page = parseInt(searchParams.get('page') || '1', 10);
  const search = searchParams.get('q') || '';
  const selectedTag = (searchParams.get('tag') as AddonTag) || null;
  const sortBy = (searchParams.get('sort') as SortOption) || 'updated';

  const loadAddons = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.listAddons(
        page,
        PER_PAGE,
        search || undefined,
        selectedTag || undefined,
        sortBy,
      );
      setAddons(response.addons);
      setTotal(response.total);
    } catch (err) {
      setError('Failed to load addons');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [page, search, selectedTag, sortBy]);

  useEffect(() => {
    loadAddons();
  }, [loadAddons]);

  // Helper to update URL params without losing others
  const updateParams = (updates: Record<string, string | null>) => {
    const next = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(updates)) {
      if (value === null || value === '') {
        next.delete(key);
      } else {
        next.set(key, value);
      }
    }
    setSearchParams(next, { replace: true });
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const input = (e.target as HTMLFormElement).querySelector<HTMLInputElement>('input');
    updateParams({ q: input?.value || null, page: null });
  };

  const handleTagChange = (tag: AddonTag | null) => {
    updateParams({ tag: tag, page: null });
  };

  const handleSortChange = (sort: SortOption) => {
    updateParams({ sort: sort === 'updated' ? null : sort, page: null });
  };

  const handlePageChange = (newPage: number) => {
    updateParams({ page: newPage === 1 ? null : String(newPage) });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const totalPages = Math.ceil(total / PER_PAGE);

  if (error && addons.length === 0) {
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

      <div className="addons-toolbar">
        <form className="addons-search" onSubmit={handleSearch}>
          <input
            type="text"
            placeholder="Search addons..."
            defaultValue={search}
            className="search-input"
          />
          <button type="submit" className="btn btn-primary">Search</button>
        </form>

        <div className="addons-sort">
          <select
            value={sortBy}
            onChange={(e) => handleSortChange(e.target.value as SortOption)}
            className="sort-select"
          >
            {SORT_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="tags-filter">
        <button
          className={`tag-chip ${selectedTag === null ? 'active' : ''}`}
          onClick={() => handleTagChange(null)}
        >
          All
        </button>
        {ADDON_TAGS.map(tag => (
          <button
            key={tag.value}
            className={`tag-chip ${selectedTag === tag.value ? 'active' : ''}`}
            onClick={() => handleTagChange(tag.value)}
            title={tag.description}
          >
            {tag.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="addons-grid">
          {Array.from({ length: PER_PAGE }).map((_, i) => (
            <div key={i} className="addon-card skeleton">
              <div className="skeleton-title" />
              <div className="skeleton-text" />
              <div className="skeleton-text short" />
              <div className="skeleton-footer" />
            </div>
          ))}
        </div>
      ) : addons.length === 0 ? (
        <div className="no-addons">
          <p>No addons found{search && ` matching "${search}"`}{selectedTag && ` in ${ADDON_TAGS.find(t => t.value === selectedTag)?.label}`}</p>
        </div>
      ) : (
        <>
          <div className="addons-results-info">
            <span>{total} addon{total !== 1 ? 's' : ''} found</span>
          </div>
          <div className="addons-grid">
            {addons.map(addon => (
              <Link
                key={addon.id}
                to={`/addons/${addon.slug}`}
                className="addon-card"
              >
                <div className="addon-card-header">
                  {addon.icon_url && (
                    <img src={addon.icon_url} alt="" className="addon-icon" />
                  )}
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
                  {addon.is_paid && (
                    <span className="badge badge-paid">
                      {addon.price_cents ? `$${(addon.price_cents / 100).toFixed(2)}` : 'Paid'}
                    </span>
                  )}
                  {addon.download_count > 0 && (
                    <span className="addon-downloads" title="Total downloads">
                      ⬇ {addon.download_count.toLocaleString()}
                    </span>
                  )}
                  <span 
                    className="addon-author addon-author-link"
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      if (addon.owner_discord_id) {
                        navigate(`/u/${addon.owner_discord_id}`);
                      }
                    }}
                  >
                    by {addon.owner_username || 'Unknown'}
                    {addon.owner_verified_developer && (
                      <span className="verified-dev-badge-sm" title="Verified Developer">✓</span>
                    )}
                  </span>
                </div>
              </Link>
            ))}
          </div>

          {totalPages > 1 && (
            <div className="pagination">
              <button
                onClick={() => handlePageChange(Math.max(1, page - 1))}
                disabled={page === 1}
                className="btn btn-secondary"
              >
                Previous
              </button>
              <div className="page-numbers">
                {Array.from({ length: totalPages }, (_, i) => i + 1)
                  .filter(p => p === 1 || p === totalPages || Math.abs(p - page) <= 2)
                  .reduce<(number | 'ellipsis')[]>((acc, p, i, arr) => {
                    if (i > 0 && p - (arr[i - 1] as number) > 1) acc.push('ellipsis');
                    acc.push(p);
                    return acc;
                  }, [])
                  .map((item, idx) =>
                    item === 'ellipsis' ? (
                      <span key={`e-${idx}`} className="page-ellipsis">…</span>
                    ) : (
                      <button
                        key={item}
                        onClick={() => handlePageChange(item)}
                        className={`btn btn-page ${page === item ? 'active' : ''}`}
                      >
                        {item}
                      </button>
                    )
                  )}
              </div>
              <button
                onClick={() => handlePageChange(Math.min(totalPages, page + 1))}
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
