import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../services/api'
import { useAuth } from '../../context/AuthContext'
import { AnalyticsSummary, AddonAnalytics } from '../../types'
import './Analytics.css'

export default function Analytics() {
  const { user } = useAuth()
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null)
  const [selectedAddon, setSelectedAddon] = useState<AddonAnalytics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        setLoading(true)
        setError(null)
        const data = await api.getAnalyticsSummary()
        setAnalytics(data)
        if (data.addons.length > 0) {
          setSelectedAddon(data.addons[0])
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load analytics')
      } finally {
        setLoading(false)
      }
    }

    fetchAnalytics()
  }, [])

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
          <button onClick={() => window.location.reload()} className="btn btn-primary">
            Retry
          </button>
        </div>
      </div>
    )
  }

  const periodDays = user?.subscription_tier === 'premium' ? 90 : 30

  return (
    <div className="analytics-page">
      <div className="analytics-header">
        <h1>Analytics</h1>
        <span className="period-badge">Last {periodDays} days</span>
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

      {analytics?.addons && analytics.addons.length > 0 ? (
        <>
          {/* Addon Selector */}
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

              {/* Daily Chart - Simple bar representation */}
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
    </div>
  )
}
