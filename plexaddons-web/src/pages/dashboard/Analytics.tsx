import { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../services/api'
import { useAuth } from '../../context/AuthContext'
import { AnalyticsSummary, AddonAnalytics, ApiUsageAnalytics } from '../../types'
import './Analytics.css'

const DATE_RANGE_OPTIONS = [7, 14, 30, 90] as const;

export default function Analytics() {
  const { user } = useAuth()
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null)
  const [selectedAddon, setSelectedAddon] = useState<AddonAnalytics | null>(null)
  const [apiUsage, setApiUsage] = useState<ApiUsageAnalytics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [days, setDays] = useState<number>(30)
  const [activeTab, setActiveTab] = useState<'addons' | 'api-usage'>('addons')
  const [exporting, setExporting] = useState(false)

  const maxDays = user?.subscription_tier === 'premium' ? 90 : 30

  const fetchAnalytics = useCallback(async (rangeDays: number) => {
    try {
      setLoading(true)
      setError(null)
      const data = await api.getAnalyticsSummary(rangeDays)
      setAnalytics(data)
      if (data.addons.length > 0) {
        setSelectedAddon(data.addons[0])
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load analytics')
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchApiUsage = useCallback(async () => {
    try {
      const data = await api.getApiUsageAnalytics(Math.min(days, 30))
      setApiUsage(data)
    } catch {
      // API usage is supplementary, don't block the page
    }
  }, [days])

  useEffect(() => {
    if (user?.subscription_tier !== 'free') {
      fetchAnalytics(days)
    }
  }, [days, fetchAnalytics, user?.subscription_tier])

  useEffect(() => {
    if (activeTab === 'api-usage' && user?.subscription_tier !== 'free') {
      fetchApiUsage()
    }
  }, [activeTab, fetchApiUsage, user?.subscription_tier])

  const handleExport = async (format: 'csv' | 'json') => {
    if (!selectedAddon) return
    try {
      setExporting(true)
      const blob = await api.exportAddonAnalytics(selectedAddon.addon_id, format, days)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${selectedAddon.addon_slug}-analytics.${format}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch {
      // silently fail
    } finally {
      setExporting(false)
    }
  }

  if (user?.subscription_tier === 'free') {
    return (
      <div className="analytics-page">
        <div className="analytics-header">
          <h1>Analytics</h1>
        </div>
        <div className="upgrade-prompt">
          <div className="upgrade-icon">📊</div>
          <h2>Unlock Analytics</h2>
          <p>Upgrade to Pro or Premium to see detailed usage statistics for your addons.</p>
          <ul className="features-list">
            <li>See how many users are using your addons</li>
            <li>Track version distribution across users</li>
            <li>View daily usage trends</li>
            <li>Export analytics data (CSV/JSON)</li>
            <li>API key usage analytics</li>
            <li>Pro: 30 days of data</li>
            <li>Premium: 90 days of data</li>
          </ul>
          <Link to="/dashboard/subscription" className="btn btn-primary">
            Upgrade Now
          </Link>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="analytics-page">
        <div className="analytics-header">
          <h1>Analytics</h1>
        </div>
        <div className="loading-state">
          <div className="loading-spinner" />
          <p>Loading analytics...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="analytics-page">
        <div className="analytics-header">
          <h1>Analytics</h1>
        </div>
        <div className="error-state">
          <p>{error}</p>
          <button onClick={() => fetchAnalytics(days)} className="btn btn-primary">
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="analytics-page">
      <div className="analytics-header">
        <h1>Analytics</h1>
        <div className="date-range-picker">
          {DATE_RANGE_OPTIONS.filter(d => d <= maxDays).map(d => (
            <button
              key={d}
              className={`range-btn ${days === d ? 'active' : ''}`}
              onClick={() => setDays(d)}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="summary-cards">
        <div className="summary-card">
          <span className="summary-label">Total Addons</span>
          <span className="summary-value">{analytics?.total_addons || 0}</span>
        </div>
        <div className="summary-card">
          <span className="summary-label">Total Version Checks</span>
          <span className="summary-value">{analytics?.total_checks.toLocaleString() || 0}</span>
        </div>
        <div className="summary-card">
          <span className="summary-label">Unique Users</span>
          <span className="summary-value">{analytics?.total_unique_users.toLocaleString() || 0}</span>
        </div>
      </div>

      {/* Tab Switcher */}
      <div className="analytics-tabs">
        <button
          className={`tab-btn ${activeTab === 'addons' ? 'active' : ''}`}
          onClick={() => setActiveTab('addons')}
        >
          Addon Analytics
        </button>
        <button
          className={`tab-btn ${activeTab === 'api-usage' ? 'active' : ''}`}
          onClick={() => setActiveTab('api-usage')}
        >
          API Usage
        </button>
      </div>

      {activeTab === 'addons' && (
        <>
          {analytics?.addons && analytics.addons.length > 0 ? (
            <>
              {/* Addon Selector + Export */}
              <div className="addon-selector">
                <label>Select Addon:</label>
                <select
                  value={selectedAddon?.addon_id || ''}
                  onChange={(e) => {
                    const addon = analytics.addons.find(a => a.addon_id === parseInt(e.target.value))
                    setSelectedAddon(addon || null)
                  }}
                >
                  {analytics.addons.map(addon => (
                    <option key={addon.addon_id} value={addon.addon_id}>
                      {addon.addon_name}
                    </option>
                  ))}
                </select>
                <div className="export-buttons">
                  <button
                    className="btn btn-sm btn-secondary"
                    onClick={() => handleExport('csv')}
                    disabled={exporting || !selectedAddon}
                  >
                    Export CSV
                  </button>
                  <button
                    className="btn btn-sm btn-secondary"
                    onClick={() => handleExport('json')}
                    disabled={exporting || !selectedAddon}
                  >
                    Export JSON
                  </button>
                </div>
              </div>

              {selectedAddon && (
                <div className="addon-analytics">
                  <div className="analytics-section">
                    <h2>Usage Overview</h2>
                    <div className="metrics-row">
                      <div className="metric">
                        <span className="metric-value">{selectedAddon.total_checks.toLocaleString()}</span>
                        <span className="metric-label">Version Checks</span>
                      </div>
                      <div className="metric">
                        <span className="metric-value">{selectedAddon.total_unique_users.toLocaleString()}</span>
                        <span className="metric-label">Unique Users</span>
                      </div>
                      <div className="metric">
                        <span className="metric-value">
                          {selectedAddon.daily_stats.length > 0
                            ? Math.round(selectedAddon.total_checks / selectedAddon.daily_stats.length)
                            : 0}
                        </span>
                        <span className="metric-label">Avg. Daily Checks</span>
                      </div>
                    </div>
                  </div>

                  {/* Version Distribution */}
                  <div className="analytics-section">
                    <h2>Version Distribution</h2>
                    {selectedAddon.version_distribution.length > 0 ? (
                      <div className="version-distribution">
                        {selectedAddon.version_distribution.map((v, i) => (
                          <div key={i} className="version-row">
                            <div className="version-info">
                              <span className="version-name">{v.version}</span>
                              <span className="version-stats">
                                {v.check_count.toLocaleString()} checks • {v.unique_users.toLocaleString()} users
                              </span>
                            </div>
                            <div className="version-bar-container">
                              <div
                                className="version-bar"
                                style={{ width: `${v.percentage}%` }}
                              />
                              <span className="version-percentage">{v.percentage.toFixed(1)}%</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="no-data">No version data yet</p>
                    )}
                  </div>

                  {/* Daily Chart */}
                  <div className="analytics-section">
                    <h2>Daily Activity</h2>
                    {selectedAddon.daily_stats.length > 0 ? (
                      <div className="daily-chart">
                        <div className="chart-bars">
                          {selectedAddon.daily_stats.slice(-14).map((day, i) => {
                            const maxChecks = Math.max(...selectedAddon.daily_stats.map(d => d.check_count))
                            const height = maxChecks > 0 ? (day.check_count / maxChecks) * 100 : 0
                            return (
                              <div key={i} className="chart-bar-wrapper" title={`${day.date}: ${day.check_count} checks`}>
                                <div className="chart-bar" style={{ height: `${height}%` }} />
                                <span className="chart-label">
                                  {new Date(day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                                </span>
                              </div>
                            )
                          })}
                        </div>
                      </div>
                    ) : (
                      <p className="no-data">No daily data yet</p>
                    )}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="no-addons-state">
              <p>No addons with analytics data yet.</p>
              <p>Version checks will appear here once users start checking for updates.</p>
            </div>
          )}
        </>
      )}

      {activeTab === 'api-usage' && (
        <div className="api-usage-section">
          {apiUsage ? (
            <>
              {/* API Keys Summary */}
              <div className="analytics-section">
                <h2>API Keys</h2>
                {apiUsage.keys.length > 0 ? (
                  <div className="api-keys-table">
                    <div className="table-header">
                      <span>Name</span>
                      <span>Key Prefix</span>
                      <span>Usage Count</span>
                      <span>Last Used</span>
                      <span>Status</span>
                    </div>
                    {apiUsage.keys.map((key, i) => (
                      <div key={i} className="table-row">
                        <span>{key.name}</span>
                        <span className="mono">{key.key_prefix}...</span>
                        <span>{key.usage_count.toLocaleString()}</span>
                        <span>{key.last_used_at ? new Date(key.last_used_at).toLocaleDateString() : 'Never'}</span>
                        <span className={`status-badge ${key.is_active ? 'active' : 'inactive'}`}>
                          {key.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="no-data">No API keys created yet. <Link to="/dashboard/api-keys">Create one</Link></p>
                )}
              </div>

              {/* Top Endpoints */}
              <div className="analytics-section">
                <h2>Top Endpoints (last {apiUsage.period_days} days)</h2>
                {apiUsage.top_endpoints.length > 0 ? (
                  <div className="endpoint-list">
                    {apiUsage.top_endpoints.map((ep, i) => {
                      const maxCount = apiUsage.top_endpoints[0]?.count || 1
                      return (
                        <div key={i} className="endpoint-row">
                          <div className="endpoint-info">
                            <span className={`method-badge method-${ep.method.toLowerCase()}`}>{ep.method}</span>
                            <span className="endpoint-path mono">{ep.endpoint}</span>
                          </div>
                          <div className="endpoint-bar-container">
                            <div className="endpoint-bar" style={{ width: `${(ep.count / maxCount) * 100}%` }} />
                            <span className="endpoint-count">{ep.count.toLocaleString()}</span>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <p className="no-data">No API requests recorded yet</p>
                )}
              </div>

              {/* Daily API Requests Chart */}
              <div className="analytics-section">
                <h2>Daily API Requests</h2>
                {apiUsage.daily_requests.length > 0 ? (
                  <div className="daily-chart">
                    <div className="chart-bars">
                      {apiUsage.daily_requests.map((day, i) => {
                        const maxCount = Math.max(...apiUsage.daily_requests.map(d => d.count))
                        const height = maxCount > 0 ? (day.count / maxCount) * 100 : 0
                        return (
                          <div key={i} className="chart-bar-wrapper" title={`${day.date}: ${day.count} requests`}>
                            <div className="chart-bar api-bar" style={{ height: `${height}%` }} />
                            <span className="chart-label">
                              {new Date(day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                            </span>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                ) : (
                  <p className="no-data">No daily request data yet</p>
                )}
              </div>
            </>
          ) : (
            <div className="loading-state">
              <div className="loading-spinner" />
              <p>Loading API usage data...</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
