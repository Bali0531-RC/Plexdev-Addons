import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../../services/api';
import type { Addon } from '../../types';
import './MyAddons.css';

export default function MyAddons() {
  const [addons, setAddons] = useState<Addon[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const perPage = 10;

  useEffect(() => {
    loadAddons();
  }, [page]);

  const loadAddons = async () => {
    try {
      setLoading(true);
      const response = await api.listMyAddons(page, perPage);
      setAddons(response.addons);
      setTotal(response.total);
    } catch (err) {
      console.error('Failed to load addons:', err);
    } finally {
      setLoading(false);
    }
  };

  const totalPages = Math.ceil(total / perPage);

  if (loading && addons.length === 0) {
    return (
      <div className="loading-page">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className="my-addons">
      <div className="my-addons-header">
        <h1>My Addons</h1>
        <Link to="/dashboard/addons/new" className="btn btn-primary">
          + New Addon
        </Link>
      </div>

      {addons.length === 0 ? (
        <div className="empty-state">
          <h2>No addons yet</h2>
          <p>Create your first addon to get started</p>
          <Link to="/dashboard/addons/new" className="btn btn-primary">
            Create Addon
          </Link>
        </div>
      ) : (
        <>
          <div className="addons-table">
            <div className="table-header">
              <span>Name</span>
              <span>Latest Version</span>
              <span>Versions</span>
              <span>Status</span>
              <span>Actions</span>
            </div>
            {addons.map(addon => (
              <div key={addon.id} className="table-row">
                <span className="addon-name">
                  <Link to={`/dashboard/addons/${addon.slug}`}>{addon.name}</Link>
                </span>
                <span className="addon-version">
                  {addon.latest_version ? `v${addon.latest_version}` : '-'}
                </span>
                <span className="addon-count">{addon.version_count}</span>
                <span className="addon-status">
                  <span className={`status-badge ${addon.is_active ? 'status-active' : 'status-inactive'}`}>
                    {addon.is_active ? 'Active' : 'Inactive'}
                  </span>
                </span>
                <span className="addon-actions">
                  <Link to={`/dashboard/addons/${addon.slug}`} className="btn btn-sm btn-secondary">
                    Edit
                  </Link>
                  <Link to={`/dashboard/addons/${addon.slug}/versions/new`} className="btn btn-sm btn-primary">
                    + Version
                  </Link>
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
