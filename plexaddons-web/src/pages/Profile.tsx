import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../services/api'
import { UserPublicProfile, Addon } from '../types'
import './Profile.css'

const TIER_BADGES: Record<string, { label: string; color: string }> = {
  free: { label: 'Free', color: '#666' },
  pro: { label: 'Pro', color: '#f59e0b' },
  premium: { label: 'Premium', color: '#8b5cf6' },
}

export default function Profile() {
  const { identifier } = useParams<{ identifier: string }>()
  const [profile, setProfile] = useState<UserPublicProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchProfile = async () => {
      if (!identifier) return
      
      try {
        setLoading(true)
        setError(null)
        const data = await api.getPublicProfile(identifier)
        setProfile(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load profile')
      } finally {
        setLoading(false)
      }
    }

    fetchProfile()
  }, [identifier])

  if (loading) {
    return (
      <div className="profile-page">
        <div className="profile-loading">
          <div className="loading-spinner" />
          <p>Loading profile...</p>
        </div>
      </div>
    )
  }

  if (error || !profile) {
    return (
      <div className="profile-page">
        <div className="profile-error">
          <h2>Profile Not Found</h2>
          <p>{error || 'This profile does not exist or is private.'}</p>
          <Link to="/" className="back-link">← Back to Home</Link>
        </div>
      </div>
    )
  }

  const tierBadge = TIER_BADGES[profile.subscription_tier]
  const avatarUrl = profile.discord_avatar
    ? `https://cdn.discordapp.com/avatars/${profile.discord_id}/${profile.discord_avatar}.png?size=256`
    : `https://cdn.discordapp.com/embed/avatars/${parseInt(profile.discord_id) % 5}.png`

  return (
    <div className="profile-page">
      {/* Banner */}
      <div 
        className="profile-banner"
        style={{
          background: profile.banner_url 
            ? `url(${profile.banner_url}) center/cover` 
            : profile.accent_color 
              ? `linear-gradient(135deg, ${profile.accent_color}, ${profile.accent_color}88)`
              : 'linear-gradient(135deg, #5865f2, #7289da)',
        }}
      />

      {/* Profile Header */}
      <div className="profile-container">
        <div className="profile-header">
          <img 
            src={avatarUrl} 
            alt={profile.discord_username}
            className="profile-avatar"
          />
          <div className="profile-info">
            <div className="profile-name-row">
              <h1 className="profile-name">{profile.discord_username}</h1>
              <span 
                className="profile-tier-badge"
                style={{ backgroundColor: tierBadge.color }}
              >
                {tierBadge.label}
              </span>
            </div>
            
            {profile.badges && profile.badges.length > 0 && (
              <div className="profile-badges">
                {profile.badges.map((badge, i) => (
                  <span key={i} className="badge">{badge}</span>
                ))}
              </div>
            )}

            {profile.bio && (
              <p className="profile-bio">{profile.bio}</p>
            )}

            <div className="profile-links">
              {profile.website && (
                <a 
                  href={profile.website} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="profile-link"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10"/>
                    <path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
                  </svg>
                  Website
                </a>
              )}
              {profile.github_username && (
                <a 
                  href={`https://github.com/${profile.github_username}`} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="profile-link"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                  </svg>
                  {profile.github_username}
                </a>
              )}
              {profile.twitter_username && (
                <a 
                  href={`https://twitter.com/${profile.twitter_username}`} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="profile-link"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                  </svg>
                  @{profile.twitter_username}
                </a>
              )}
            </div>

            <p className="profile-joined">
              Member since {new Date(profile.created_at).toLocaleDateString('en-US', { 
                month: 'long', 
                year: 'numeric' 
              })}
            </p>
          </div>
        </div>

        {/* Addons Section */}
        {profile.addons && profile.addons.length > 0 && (
          <div className="profile-addons">
            <h2 className="section-title">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
                <polyline points="7.5 4.21 12 6.81 16.5 4.21"/>
                <polyline points="7.5 19.79 7.5 14.6 3 12"/>
                <polyline points="21 12 16.5 14.6 16.5 19.79"/>
                <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
                <line x1="12" y1="22.08" x2="12" y2="12"/>
              </svg>
              Addons ({profile.addons.length})
            </h2>
            <div className="addons-grid">
              {profile.addons.map((addon: Addon) => (
                <Link 
                  key={addon.id} 
                  to={`/addons/${addon.slug}`}
                  className="addon-card"
                >
                  <h3 className="addon-name">{addon.name}</h3>
                  {addon.description && (
                    <p className="addon-description">{addon.description}</p>
                  )}
                  <div className="addon-meta">
                    {addon.latest_version && (
                      <span className="addon-version">v{addon.latest_version}</span>
                    )}
                    <span className="addon-versions">
                      {addon.version_count} version{addon.version_count !== 1 ? 's' : ''}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        )}

        {profile.addons && profile.addons.length === 0 && (
          <div className="profile-no-addons">
            <p>This user hasn't published any addons yet.</p>
          </div>
        )}
      </div>
    </div>
  )
}
