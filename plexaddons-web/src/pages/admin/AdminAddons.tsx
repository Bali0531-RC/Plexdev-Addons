import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { api } from '../../services/api';
import type { Addon } from '../../types';
import './AdminAddons.css';

export default function AdminAddons() {
  const [addons, setAddons] = useState<Addon[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const perPage = 20;

  useEffect(() => {
    loadAddons();
  }, [page, search]);

  const loadAddons = async () => {
    try {
      setLoading(true);
      const response = await api.listAllAddons(page, perPage, search || undefined);
      setAddons(response.addons);
      setTotal(response.total);
    } catch (err) {
      console.error('Failed to load addons:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (addonId: number, addonName: string) => {
    toast.promise(
      api.adminDeleteAddon(addonId).then(() => loadAddons()),
      {
        loading: `Deleting "${addonName}"...`,
        success: `"${addonName}" deleted successfully`,
        error: 'Failed to delete addon',
      }
    );
  };

  const totalPages = Math.ceil(total / perPage);

  return (
    <div className="admin-addons">
      <h1>Manage Addons</h1>

      <div className="addons-filters">
        <input
          type="text"
          placeholder="Search addons..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="search-input"
        />
      </div>

      {loading && addons.length === 0 ? (
        <div className="loading-page">
          <div className="spinner" />
        </div>
      ) : (
        <>
          <div className="addons-table">
            <div className="table-header">
              <span>Name</span>
              <span>Owner</span>
              <span>Versions</span>
              <span>Status</span>
              <span>Actions</span>
            </div>
            {addons.map(addon => (
              <div key={addon.id} className="table-row">
                <div className="addon-info">
                  <span className="addon-name">
                    {addon.name}
                    {addon.verified && <span className="verified-mark" title="Verified">✓</span>}
                  </span>
                  <span className="addon-slug">{addon.slug}</span>
                </div>
                <span className="addon-owner">{addon.owner_username || 'Unknown'}</span>
                <span>{addon.version_count}</span>
                <span>
                  <span className={`status-badge ${addon.is_active ? 'status-active' : 'status-inactive'}`}>
                    {addon.is_active ? 'Active' : 'Inactive'}
                  </span>
                </span>
                <span className="addon-actions">
                  <Link to={`/admin/addons/${addon.id}`} className="btn btn-sm btn-primary">
                    Edit
                  </Link>
                  <Link to={`/addons/${addon.slug}`} className="btn btn-sm btn-secondary" target="_blank">
                    View
                  </Link>
                  <button 
                    onClick={() => handleDelete(addon.id, addon.name)}
                    className="btn btn-sm btn-danger"
                  >
                    Delete
                  </button>
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
                Page {page} of {totalPages} ({total} addons)
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
