import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { api } from '../services/api';
import type {
  SelfHostedConfig, SelfHostedConfigCreate,
  AnalyticsAlert, AnalyticsAlertCreate,
  CohortAnalysisResponse,
  PredictiveEstimate,
  RealtimeStats, RecentCheck, HourlyBreakdown,
} from '../types';
import './PremiumAnalytics.css';

interface Props {
  addonId: number;
  versions: { version: string }[];
}

type Tab = 'realtime' | 'alerts' | 'cohorts' | 'predictive' | 'selfhosted';

export default function PremiumAnalytics({ addonId, versions }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>('realtime');

  const tabs: { key: Tab; label: string }[] = [
    { key: 'realtime', label: 'Real-Time' },
    { key: 'alerts', label: 'Alerts' },
    { key: 'cohorts', label: 'Cohorts' },
    { key: 'predictive', label: 'Predictions' },
    { key: 'selfhosted', label: 'Self-Hosted' },
  ];

  return (
    <div className="premium-analytics">
      <h3>Premium Analytics</h3>
      <div className="pa-tabs">
        {tabs.map(t => (
          <button
            key={t.key}
            className={`pa-tab ${activeTab === t.key ? 'active' : ''}`}
            onClick={() => setActiveTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="pa-content">
        {activeTab === 'realtime' && <RealtimePanel addonId={addonId} />}
        {activeTab === 'alerts' && <AlertsPanel addonId={addonId} />}
        {activeTab === 'cohorts' && <CohortsPanel addonId={addonId} />}
        {activeTab === 'predictive' && <PredictivePanel addonId={addonId} versions={versions} />}
        {activeTab === 'selfhosted' && <SelfHostedPanel addonId={addonId} />}
      </div>
    </div>
  );
}

// ============== Real-Time Panel ==============

function RealtimePanel({ addonId }: { addonId: number }) {
  const [stats, setStats] = useState<RealtimeStats | null>(null);
  const [recentChecks, setRecentChecks] = useState<RecentCheck[]>([]);
  const [hourly, setHourly] = useState<HourlyBreakdown[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    try {
      const [statsData, recentData, hourlyData] = await Promise.all([
        api.getRealtimeStats(addonId),
        api.getRecentChecks(addonId, 20),
        api.getHourlyBreakdown(addonId, 24),
      ]);
      setStats(statsData);
      setRecentChecks(recentData.checks || []);
      setHourly(hourlyData.hourly || []);
    } catch {
      toast.error('Failed to load real-time analytics');
    } finally {
      setLoading(false);
    }
  }, [addonId]);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, [loadData]);

  if (loading) return <div className="pa-loading">Loading real-time data...</div>;

  return (
    <div className="realtime-panel">
      {stats && (
        <div className="realtime-stats-grid">
          <div className="stat-card">
            <div className="stat-value">{stats.checks_last_hour}</div>
            <div className="stat-label">Checks (1h)</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.checks_last_24h}</div>
            <div className="stat-label">Checks (24h)</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.unique_users_last_hour}</div>
            <div className="stat-label">Unique Users (1h)</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.active_versions}</div>
            <div className="stat-label">Active Versions</div>
          </div>
          {stats.top_version && (
            <div className="stat-card">
              <div className="stat-value">{stats.top_version}</div>
              <div className="stat-label">Top Version</div>
            </div>
          )}
        </div>
      )}

      {hourly.length > 0 && (
        <div className="hourly-chart">
          <h4>Hourly Breakdown (24h)</h4>
          <div className="hourly-bars">
            {hourly.map((h, i) => {
              const maxChecks = Math.max(...hourly.map(x => x.checks), 1);
              const height = (h.checks / maxChecks) * 100;
              return (
                <div key={i} className="hourly-bar-container" title={`${new Date(h.hour).toLocaleTimeString()}: ${h.checks} checks`}>
                  <div className="hourly-bar" style={{ height: `${height}%` }} />
                  <div className="hourly-label">{new Date(h.hour).getHours()}h</div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="recent-checks">
        <h4>Recent Checks</h4>
        {recentChecks.length === 0 ? (
          <p className="pa-empty">No recent version checks.</p>
        ) : (
          <table className="pa-table">
            <thead>
              <tr>
                <th>Version</th>
                <th>Resolved</th>
                <th>Time</th>
                <th>Client</th>
              </tr>
            </thead>
            <tbody>
              {recentChecks.map(c => (
                <tr key={c.id}>
                  <td>{c.checked_version}</td>
                  <td>{c.resolved_version || '-'}</td>
                  <td>{c.timestamp ? new Date(c.timestamp).toLocaleTimeString() : '-'}</td>
                  <td className="hash-prefix">{c.client_hash_prefix || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// ============== Alerts Panel ==============

function AlertsPanel({ addonId }: { addonId: number }) {
  const [alerts, setAlerts] = useState<AnalyticsAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState<AnalyticsAlertCreate>({
    name: '',
    metric: 'daily_checks',
    comparison: 'below',
    threshold: 100,
    notification_channel: 'webhook',
    cooldown_minutes: 60,
  });

  const loadAlerts = useCallback(async () => {
    try {
      const data = await api.listAlerts(addonId);
      setAlerts(data.alerts || []);
    } catch {
      toast.error('Failed to load alerts');
    } finally {
      setLoading(false);
    }
  }, [addonId]);

  useEffect(() => { loadAlerts(); }, [loadAlerts]);

  const handleCreate = async () => {
    try {
      await api.createAlert(addonId, form as unknown as Record<string, unknown>);
      toast.success('Alert created');
      setShowCreate(false);
      setForm({ name: '', metric: 'daily_checks', comparison: 'below', threshold: 100, notification_channel: 'webhook', cooldown_minutes: 60 });
      loadAlerts();
    } catch {
      toast.error('Failed to create alert');
    }
  };

  const handleDelete = async (alertId: number) => {
    if (!confirm('Delete this alert?')) return;
    try {
      await api.deleteAlert(addonId, alertId);
      toast.success('Alert deleted');
      loadAlerts();
    } catch {
      toast.error('Failed to delete alert');
    }
  };

  const handleTest = async (alertId: number) => {
    try {
      await api.testAlert(addonId, alertId);
      toast.success('Test notification sent');
    } catch {
      toast.error('Failed to send test');
    }
  };

  const handleToggle = async (alert: AnalyticsAlert) => {
    try {
      await api.updateAlert(addonId, alert.id, { is_active: !alert.is_active });
      toast.success(alert.is_active ? 'Alert paused' : 'Alert activated');
      loadAlerts();
    } catch {
      toast.error('Failed to update alert');
    }
  };

  if (loading) return <div className="pa-loading">Loading alerts...</div>;

  return (
    <div className="alerts-panel">
      <div className="pa-header">
        <span>{alerts.length} alert{alerts.length !== 1 ? 's' : ''}</span>
        <button className="btn btn-sm btn-primary" onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? 'Cancel' : '+ New Alert'}
        </button>
      </div>

      {showCreate && (
        <div className="alert-create-form">
          <div className="form-row">
            <label>Name</label>
            <input type="text" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="Low traffic alert" />
          </div>
          <div className="form-row">
            <label>Metric</label>
            <select value={form.metric} onChange={e => setForm({ ...form, metric: e.target.value })}>
              <option value="daily_checks">Daily Checks</option>
              <option value="unique_users">Unique Users</option>
              <option value="error_rate">Error Rate</option>
            </select>
          </div>
          <div className="form-row">
            <label>Condition</label>
            <div className="condition-row">
              <select value={form.comparison} onChange={e => setForm({ ...form, comparison: e.target.value as 'below' | 'above' })}>
                <option value="below">Drops below</option>
                <option value="above">Exceeds</option>
              </select>
              <input type="number" value={form.threshold} onChange={e => setForm({ ...form, threshold: parseInt(e.target.value) || 0 })} min={0} />
            </div>
          </div>
          <div className="form-row">
            <label>Channel</label>
            <select value={form.notification_channel} onChange={e => setForm({ ...form, notification_channel: e.target.value as 'webhook' | 'email' | 'discord' })}>
              <option value="webhook">Webhook</option>
              <option value="email">Email</option>
              <option value="discord">Discord</option>
            </select>
          </div>
          {form.notification_channel === 'webhook' && (
            <div className="form-row">
              <label>Webhook URL</label>
              <input type="url" value={form.webhook_url || ''} onChange={e => setForm({ ...form, webhook_url: e.target.value })} placeholder="https://..." />
            </div>
          )}
          {form.notification_channel === 'email' && (
            <div className="form-row">
              <label>Email</label>
              <input type="email" value={form.email || ''} onChange={e => setForm({ ...form, email: e.target.value })} placeholder="you@example.com" />
            </div>
          )}
          {form.notification_channel === 'discord' && (
            <div className="form-row">
              <label>Discord Webhook URL</label>
              <input type="url" value={form.discord_webhook_url || ''} onChange={e => setForm({ ...form, discord_webhook_url: e.target.value })} placeholder="https://discord.com/api/webhooks/..." />
            </div>
          )}
          <div className="form-row">
            <label>Cooldown (minutes)</label>
            <input type="number" value={form.cooldown_minutes} onChange={e => setForm({ ...form, cooldown_minutes: parseInt(e.target.value) || 60 })} min={5} max={1440} />
          </div>
          <button className="btn btn-primary" onClick={handleCreate} disabled={!form.name}>Create Alert</button>
        </div>
      )}

      <div className="alerts-list">
        {alerts.map(alert => (
          <div key={alert.id} className={`alert-card ${alert.is_active ? '' : 'inactive'}`}>
            <div className="alert-info">
              <strong>{alert.name}</strong>
              <span className="alert-condition">
                {alert.metric} {alert.comparison} {alert.threshold}
              </span>
              <span className="alert-channel">{alert.notification_channel}</span>
              {alert.last_triggered_at && (
                <span className="alert-last-triggered">Last: {new Date(alert.last_triggered_at).toLocaleString()}</span>
              )}
              <span className="alert-trigger-count">Triggered {alert.trigger_count}x</span>
            </div>
            <div className="alert-actions">
              <button className="btn btn-sm" onClick={() => handleToggle(alert)}>
                {alert.is_active ? 'Pause' : 'Activate'}
              </button>
              <button className="btn btn-sm" onClick={() => handleTest(alert.id)}>Test</button>
              <button className="btn btn-sm btn-danger" onClick={() => handleDelete(alert.id)}>Delete</button>
            </div>
          </div>
        ))}
        {alerts.length === 0 && <p className="pa-empty">No alerts configured. Create one to get notified about analytics changes.</p>}
      </div>
    </div>
  );
}

// ============== Cohorts Panel ==============

function CohortsPanel({ addonId }: { addonId: number }) {
  const [cohortData, setCohortData] = useState<CohortAnalysisResponse | null>(null);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);

  const loadCohorts = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getCohortAnalysis(addonId, days);
      setCohortData(data);
    } catch {
      toast.error('Failed to load cohort data');
    } finally {
      setLoading(false);
    }
  }, [addonId, days]);

  useEffect(() => { loadCohorts(); }, [loadCohorts]);

  if (loading) return <div className="pa-loading">Loading cohort data...</div>;

  return (
    <div className="cohorts-panel">
      <div className="pa-header">
        <span>Version Upgrade Paths</span>
        <select value={days} onChange={e => setDays(Number(e.target.value))}>
          <option value={7}>Last 7 days</option>
          <option value={14}>Last 14 days</option>
          <option value={30}>Last 30 days</option>
          <option value={60}>Last 60 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      {cohortData && cohortData.cohorts.length > 0 ? (
        <>
          <div className="cohort-summary">
            <strong>{cohortData.total_transitions}</strong> total transitions in the last {cohortData.period_days} days
          </div>
          <table className="pa-table">
            <thead>
              <tr>
                <th>From Version</th>
                <th>To Version</th>
                <th>Users</th>
                <th>First</th>
                <th>Last</th>
              </tr>
            </thead>
            <tbody>
              {cohortData.cohorts.map((c, i) => (
                <tr key={i}>
                  <td><span className="version-badge from">{c.from_version}</span></td>
                  <td><span className="version-badge to">{c.to_version}</span></td>
                  <td>{c.user_count}</td>
                  <td>{new Date(c.first_transition).toLocaleDateString()}</td>
                  <td>{new Date(c.last_transition).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      ) : (
        <p className="pa-empty">No version transitions detected yet. Cohort data is recorded when users upgrade between versions.</p>
      )}
    </div>
  );
}

// ============== Predictive Panel ==============

function PredictivePanel({ addonId, versions }: { addonId: number; versions: { version: string }[] }) {
  const [estimate, setEstimate] = useState<PredictiveEstimate | null>(null);
  const [selectedVersion, setSelectedVersion] = useState(versions[0]?.version || '');
  const [predDays, setPredDays] = useState(14);
  const [loading, setLoading] = useState(false);

  const loadPrediction = useCallback(async () => {
    if (!selectedVersion) return;
    setLoading(true);
    try {
      const data = await api.getPredictiveAnalytics(addonId, selectedVersion, predDays);
      setEstimate(data);
    } catch {
      toast.error('Failed to load predictions');
    } finally {
      setLoading(false);
    }
  }, [addonId, selectedVersion, predDays]);

  useEffect(() => { loadPrediction(); }, [loadPrediction]);

  return (
    <div className="predictive-panel">
      <div className="pa-header">
        <div className="pred-controls">
          <label>Version:</label>
          <select value={selectedVersion} onChange={e => setSelectedVersion(e.target.value)}>
            {versions.map(v => (
              <option key={v.version} value={v.version}>{v.version}</option>
            ))}
          </select>
          <label>Based on:</label>
          <select value={predDays} onChange={e => setPredDays(Number(e.target.value))}>
            <option value={7}>7 days</option>
            <option value={14}>14 days</option>
            <option value={30}>30 days</option>
          </select>
        </div>
      </div>

      {loading && <div className="pa-loading">Calculating predictions...</div>}

      {!loading && estimate && (
        <div className="prediction-results">
          <div className="pred-stat-grid">
            <div className="stat-card">
              <div className="stat-value">{estimate.current_adoption_percent}%</div>
              <div className="stat-label">Current Adoption</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{estimate.daily_adoption_rate}%</div>
              <div className="stat-label">Daily Rate</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{estimate.adopted_users} / {estimate.total_users}</div>
              <div className="stat-label">Users Adopted</div>
            </div>
          </div>

          <div className="milestones">
            <h4>Estimated Milestones</h4>
            <div className="milestone-list">
              <div className="milestone">
                <span className="milestone-target">50% adoption</span>
                <span className="milestone-estimate">
                  {estimate.estimated_days_to_50 === null ? 'N/A' : estimate.estimated_days_to_50 === 0 ? 'Reached' : `~${estimate.estimated_days_to_50} days`}
                </span>
              </div>
              <div className="milestone">
                <span className="milestone-target">90% adoption</span>
                <span className="milestone-estimate">
                  {estimate.estimated_days_to_90 === null ? 'N/A' : estimate.estimated_days_to_90 === 0 ? 'Reached' : `~${estimate.estimated_days_to_90} days`}
                </span>
              </div>
              <div className="milestone">
                <span className="milestone-target">100% adoption</span>
                <span className="milestone-estimate">
                  {estimate.estimated_days_to_100 === null ? 'N/A' : estimate.estimated_days_to_100 === 0 ? 'Reached' : `~${estimate.estimated_days_to_100} days`}
                </span>
              </div>
            </div>
          </div>

          {estimate.daily_adoption_rate === 0 && (
            <p className="pa-warning">No adoption trend detected. Predictions require at least a few days of version check data.</p>
          )}
        </div>
      )}

      {!loading && !estimate && selectedVersion && (
        <p className="pa-empty">Select a version to see adoption predictions.</p>
      )}
    </div>
  );
}

// ============== Self-Hosted Panel ==============

function SelfHostedPanel({ addonId }: { addonId: number }) {
  const [config, setConfig] = useState<SelfHostedConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [exists, setExists] = useState(false);
  const [form, setForm] = useState<SelfHostedConfigCreate>({
    private_endpoint_enabled: true,
    api_key_required: true,
    rate_limit_per_minute: 60,
  });

  const loadConfig = useCallback(async () => {
    try {
      const data = await api.getSelfHostedConfig(addonId);
      setConfig(data);
      setExists(true);
      setForm({
        custom_domain: data.custom_domain,
        private_endpoint_enabled: data.private_endpoint_enabled,
        api_key_required: data.api_key_required,
        rate_limit_per_minute: data.rate_limit_per_minute,
      });
    } catch {
      setExists(false);
    } finally {
      setLoading(false);
    }
  }, [addonId]);

  useEffect(() => { loadConfig(); }, [loadConfig]);

  const handleSave = async () => {
    try {
      if (exists) {
        await api.updateSelfHostedConfig(addonId, form as unknown as Record<string, unknown>);
        toast.success('Config updated');
      } else {
        await api.createSelfHostedConfig(addonId, form as unknown as Record<string, unknown>);
        toast.success('Config created');
      }
      loadConfig();
    } catch {
      toast.error('Failed to save config');
    }
  };

  const handleDelete = async () => {
    if (!confirm('Delete self-hosted configuration?')) return;
    try {
      await api.deleteSelfHostedConfig(addonId);
      toast.success('Config deleted');
      setConfig(null);
      setExists(false);
      setForm({ private_endpoint_enabled: true, api_key_required: true, rate_limit_per_minute: 60 });
    } catch {
      toast.error('Failed to delete config');
    }
  };

  const handleVerifyDomain = async () => {
    try {
      const result = await api.verifySelfHostedDomain(addonId);
      if (result.verified) {
        toast.success('Domain verified!');
      } else {
        toast.info(result.instructions);
      }
      loadConfig();
    } catch {
      toast.error('Failed to verify domain');
    }
  };

  if (loading) return <div className="pa-loading">Loading self-hosted config...</div>;

  return (
    <div className="selfhosted-panel">
      <p className="pa-description">
        Configure a private versions.json endpoint for your addon. Optionally use a custom domain.
      </p>

      <div className="form-row">
        <label>Custom Domain (optional)</label>
        <input
          type="text"
          value={form.custom_domain || ''}
          onChange={e => setForm({ ...form, custom_domain: e.target.value || undefined })}
          placeholder="updates.yourdomain.com"
        />
        {config?.custom_domain && !config.domain_verified && (
          <button className="btn btn-sm" onClick={handleVerifyDomain}>Verify Domain</button>
        )}
        {config?.domain_verified && <span className="verified-badge">Verified</span>}
      </div>

      <div className="form-row">
        <label>
          <input
            type="checkbox"
            checked={form.private_endpoint_enabled ?? true}
            onChange={e => setForm({ ...form, private_endpoint_enabled: e.target.checked })}
          />
          Enable private versions.json endpoint
        </label>
      </div>

      <div className="form-row">
        <label>
          <input
            type="checkbox"
            checked={form.api_key_required ?? true}
            onChange={e => setForm({ ...form, api_key_required: e.target.checked })}
          />
          Require API key for access
        </label>
      </div>

      <div className="form-row">
        <label>Rate Limit (per minute)</label>
        <input
          type="number"
          value={form.rate_limit_per_minute ?? 60}
          onChange={e => setForm({ ...form, rate_limit_per_minute: parseInt(e.target.value) || 60 })}
          min={1}
          max={600}
        />
      </div>

      {config?.verification_token && !config.domain_verified && config.custom_domain && (
        <div className="verification-info">
          <h4>Domain Verification</h4>
          <p>Add a TXT record to your domain:</p>
          <code>_plexdev-verify={config.verification_token}</code>
        </div>
      )}

      <div className="selfhosted-actions">
        <button className="btn btn-primary" onClick={handleSave}>
          {exists ? 'Update Config' : 'Create Config'}
        </button>
        {exists && (
          <button className="btn btn-danger" onClick={handleDelete}>Delete Config</button>
        )}
      </div>
    </div>
  );
}
