import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { api } from '../services/api';
import type { OrgAnalyticsSummary } from '../types';

interface Props {
  orgSlug: string;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

export default function OrgAnalytics({ orgSlug }: Props) {
  const [data, setData] = useState<OrgAnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAnalytics();
  }, [orgSlug]);

  const loadAnalytics = async () => {
    try {
      setLoading(true);
      const res = await api.getOrgAnalytics(orgSlug);
      setData(res);
    } catch (err: any) {
      toast.error(err.message || 'Failed to load analytics');
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="spinner" />;
  if (!data) return <p className="no-data">Unable to load analytics.</p>;

  return (
    <div className="org-analytics">
      <h3>Organization Analytics</h3>
      <div className="analytics-grid">
        <div className="stat-card">
          <div className="stat-value">{data.total_downloads.toLocaleString()}</div>
          <div className="stat-label">Total Downloads</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{data.total_version_checks.toLocaleString()}</div>
          <div className="stat-label">Version Checks</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{data.total_unique_users.toLocaleString()}</div>
          <div className="stat-label">Unique Users</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{data.addon_count}</div>
          <div className="stat-label">Addons</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{data.member_count}</div>
          <div className="stat-label">Members</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{formatBytes(data.storage_used_bytes)}</div>
          <div className="stat-label">Storage Used</div>
        </div>
      </div>

      {data.top_addons.length > 0 && (
        <div className="top-addons">
          <h4>Top Addons</h4>
          <div className="top-addons-list">
            {data.top_addons.map((addon, i) => (
              <div key={addon.id} className="top-addon-row">
                <span className="top-addon-rank">#{i + 1}</span>
                <span className="top-addon-name">{addon.name}</span>
                <span className="top-addon-downloads">{addon.downloads.toLocaleString()} downloads</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
