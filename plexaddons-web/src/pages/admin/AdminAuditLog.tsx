import { useState, useEffect } from 'react';
import { api } from '../../services/api';
import type { AuditLogEntry } from '../../types';
import './AdminAuditLog.css';

export default function AdminAuditLog() {
  const [entries, setEntries] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const perPage = 50;

  useEffect(() => {
    loadAuditLog();
  }, [page]);

  const loadAuditLog = async () => {
    try {
      setLoading(true);
      const response = await api.getAuditLog(page, perPage);
      setEntries(response.entries);
      setTotal(response.total);
    } catch (err) {
      console.error('Failed to load audit log:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCleanup = async () => {
    if (!confirm('This will delete all audit log entries older than 90 days. Continue?')) {
      return;
    }
    try {
      const result = await api.cleanupAuditLog();
      alert(`Cleanup complete. ${result.deleted_count} entries deleted.`);
      loadAuditLog();
    } catch (err) {
      console.error('Failed to cleanup:', err);
      alert('Failed to cleanup audit log');
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString();
  };

  const totalPages = Math.ceil(total / perPage);

  return (
    <div className="admin-audit-log">
      <div className="audit-header">
        <h1>Audit Log</h1>
        <button onClick={handleCleanup} className="btn btn-secondary">
          Cleanup Old Entries
        </button>
      </div>

      <p className="audit-note">
        Showing admin actions. Entries are automatically purged after 90 days.
      </p>

      {loading && entries.length === 0 ? (
        <div className="loading-page">
          <div className="spinner" />
        </div>
      ) : entries.length === 0 ? (
        <div className="empty-state">
          <p>No audit log entries found.</p>
        </div>
      ) : (
        <>
          <div className="audit-table">
            <div className="table-header">
              <span>Timestamp</span>
              <span>Admin</span>
              <span>Action</span>
              <span>Target</span>
              <span>Details</span>
            </div>
            {entries.map(entry => (
              <div key={entry.id} className="table-row">
                <span className="entry-time">{formatDate(entry.created_at)}</span>
                <span className="entry-admin">{entry.admin_username || 'System'}</span>
                <span className="entry-action">{entry.action}</span>
                <span className="entry-target">
                  {entry.target_type && entry.target_id 
                    ? `${entry.target_type}:${entry.target_id}` 
                    : '-'}
                </span>
                <span className="entry-details" title={entry.details || undefined}>
                  {entry.details || '-'}
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
                Page {page} of {totalPages} ({total} entries)
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
