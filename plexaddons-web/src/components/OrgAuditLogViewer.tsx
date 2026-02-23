import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { api } from '../services/api';
import type { OrgAuditLog } from '../types';

interface Props {
  orgSlug: string;
}

export default function OrgAuditLogViewer({ orgSlug }: Props) {
  const [logs, setLogs] = useState<OrgAuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadLogs();
  }, [orgSlug, page]);

  const loadLogs = async () => {
    try {
      setLoading(true);
      const res = await api.getOrgAuditLogs(orgSlug, page, 25);
      setLogs(res.logs);
      setTotal(res.total);
    } catch (err: any) {
      toast.error(err.message || 'Failed to load audit logs');
    } finally {
      setLoading(false);
    }
  };

  const formatAction = (action: string) => {
    const labels: Record<string, string> = {
      'org.created': 'Organization created',
      'org.deleted': 'Organization deleted',
      'settings.updated': 'Settings updated',
      'member.invited': 'Member invited',
      'member.removed': 'Member removed',
      'member.left': 'Member left',
      'member.role_updated': 'Member role updated',
      'member.permissions_updated': 'Permissions updated',
      'api_key.created': 'API key created',
      'api_key.deleted': 'API key deleted',
    };
    return labels[action] || action;
  };

  const totalPages = Math.ceil(total / 25);

  return (
    <div className="audit-log-viewer">
      <h3>Audit Log</h3>
      {loading ? (
        <div className="spinner" />
      ) : logs.length === 0 ? (
        <p className="no-data">No audit log entries yet.</p>
      ) : (
        <>
          <div className="audit-log-list">
            {logs.map(log => (
              <div key={log.id} className="audit-log-entry">
                <div className="audit-log-action">
                  <strong>{formatAction(log.action)}</strong>
                  <span className="audit-log-user">
                    by {log.username || `User #${log.user_id}`}
                  </span>
                </div>
                {log.details && Object.keys(log.details).length > 0 && (
                  <div className="audit-log-details">
                    {Object.entries(log.details).map(([k, v]) => (
                      <span key={k} className="detail-tag">
                        {k}: {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                      </span>
                    ))}
                  </div>
                )}
                <span className="audit-log-time">
                  {new Date(log.created_at).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
          {totalPages > 1 && (
            <div className="pagination">
              <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
                Previous
              </button>
              <span>Page {page} of {totalPages}</span>
              <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
