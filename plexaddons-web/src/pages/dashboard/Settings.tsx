import { useState, FormEvent, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import { toast } from 'sonner';
import { UserProfileUpdate, WebhookConfig } from '../../types';
import ApiKeysManager from '../../components/ApiKeysManager';
import './Settings.css';

export default function Settings() {
  const { user, setUser, logout } = useAuth();
  const [email, setEmail] = useState(user?.email || '');
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Profile state
  const [profileData, setProfileData] = useState<UserProfileUpdate>({
    bio: user?.bio || '',
    website: user?.website || '',
    github_username: user?.github_username || '',
    twitter_username: user?.twitter_username || '',
    profile_slug: user?.profile_slug || '',
    profile_public: user?.profile_public ?? true,
    show_addons: user?.show_addons ?? true,
    accent_color: user?.accent_color || '#5865f2',
    banner_url: user?.banner_url || '',
  });
  const [savingProfile, setSavingProfile] = useState(false);
  
  // Webhook state
  const [webhookConfig, setWebhookConfig] = useState<WebhookConfig | null>(null);
  const [webhookUrl, setWebhookUrl] = useState('');
  const [webhookEnabled, setWebhookEnabled] = useState(false);
  const [newWebhookSecret, setNewWebhookSecret] = useState<string | null>(null);
  const [savingWebhook, setSavingWebhook] = useState(false);
  const [testingWebhook, setTestingWebhook] = useState(false);
  const [regeneratingSecret, setRegeneratingSecret] = useState(false);
  
  // Delete account state
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState('');
  const [deleting, setDeleting] = useState(false);

  // Fetch webhook config on mount (for premium users)
  useEffect(() => {
    if (user?.subscription_tier === 'premium') {
      // Fetch webhook config
      api.getMyWebhook().then((config) => {
        setWebhookConfig(config);
        setWebhookUrl(config.webhook_url || '');
        setWebhookEnabled(config.webhook_enabled);
      }).catch(() => {});
    }
  }, [user?.subscription_tier]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);
    setSaving(true);

    try {
      const updatedUser = await api.updateMe({ email: email || undefined });
      setUser(updatedUser);
      setSuccess(true);
    } catch (err: any) {
      setError(err.message || 'Failed to update settings');
    } finally {
      setSaving(false);
    }
  };

  const handleProfileSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSavingProfile(true);
    
    try {
      const updatedUser = await api.updateMyProfile({
        ...profileData,
        bio: profileData.bio || null,
        website: profileData.website || null,
        github_username: profileData.github_username || null,
        twitter_username: profileData.twitter_username || null,
        profile_slug: profileData.profile_slug || null,
        banner_url: profileData.banner_url || null,
      });
      setUser(updatedUser);
      toast.success('Profile updated successfully!');
    } catch (err: any) {
      toast.error(err.message || 'Failed to update profile');
    } finally {
      setSavingProfile(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (deleteConfirmText !== 'DELETE') return;
    
    setDeleting(true);
    try {
      await api.deleteMyAccount();
      toast.success('Account deleted successfully. Goodbye!');
      // Wait a moment for the user to see the message
      setTimeout(() => {
        logout();
      }, 1500);
    } catch (err: any) {
      toast.error(err.message || 'Failed to delete account');
      setDeleting(false);
    }
  };

  const profileUrl = user?.profile_slug || user?.discord_id;
  const isPro = user?.subscription_tier === 'pro' || user?.subscription_tier === 'premium';
  const isPremium = user?.subscription_tier === 'premium';

  const handleSaveWebhook = async (e: FormEvent) => {
    e.preventDefault();
    setSavingWebhook(true);
    try {
      const config = await api.updateMyWebhook({
        webhook_url: webhookUrl || null,
        webhook_enabled: webhookEnabled,
      });
      setWebhookConfig(config);
      toast.success('Webhook settings saved!');
    } catch (err: any) {
      toast.error(err.message || 'Failed to save webhook settings');
    } finally {
      setSavingWebhook(false);
    }
  };

  const handleTestWebhook = async () => {
    setTestingWebhook(true);
    try {
      const result = await api.testMyWebhook();
      if (result.success) {
        toast.success(`Webhook test successful! Status: ${result.status_code}`);
      } else {
        toast.error(`Webhook test failed: ${result.error}`);
      }
    } catch (err: any) {
      toast.error(err.message || 'Failed to test webhook');
    } finally {
      setTestingWebhook(false);
    }
  };

  const handleRegenerateSecret = async () => {
    if (!confirm('Are you sure you want to regenerate your webhook secret? You\'ll need to update it in your receiving server.')) {
      return;
    }
    setRegeneratingSecret(true);
    try {
      const result = await api.regenerateWebhookSecret();
      setNewWebhookSecret(result.secret);
      setWebhookConfig(prev => prev ? { ...prev, has_secret: true } : null);
      toast.success('Webhook secret regenerated! Make sure to copy it.');
    } catch (err: any) {
      toast.error(err.message || 'Failed to regenerate webhook secret');
    } finally {
      setRegeneratingSecret(false);
    }
  };

  const handleDeleteWebhook = async () => {
    if (!confirm('Are you sure you want to delete your webhook configuration?')) {
      return;
    }
    try {
      await api.deleteMyWebhook();
      setWebhookConfig({ webhook_url: null, webhook_enabled: false, has_secret: false });
      setWebhookUrl('');
      setWebhookEnabled(false);
      setNewWebhookSecret(null);
      toast.success('Webhook deleted');
    } catch (err: any) {
      toast.error(err.message || 'Failed to delete webhook');
    }
  };

  const copyWebhookSecret = () => {
    if (newWebhookSecret) {
      navigator.clipboard.writeText(newWebhookSecret);
      toast.success('Webhook secret copied to clipboard');
    }
  };

  return (
    <div className="settings-page">
      <h1>Settings</h1>

      <div className="settings-card">
        <h2>Account Information</h2>
        <div className="account-info">
          <div className="info-item">
            <label>Discord Username</label>
            <span>{user?.discord_username}</span>
          </div>
          <div className="info-item">
            <label>Discord ID</label>
            <span className="mono">{user?.discord_id}</span>
          </div>
          <div className="info-item">
            <label>Account Created</label>
            <span>{user?.created_at ? new Date(user.created_at).toLocaleDateString() : '-'}</span>
          </div>
          <div className="info-item">
            <label>Subscription Tier</label>
            <span className="tier-badge">{user?.subscription_tier?.toUpperCase()}</span>
          </div>
        </div>
      </div>

      <div className="settings-card">
        <h2>Email Settings</h2>
        
        {success && (
          <div className="success-message">
            Settings saved successfully!
          </div>
        )}

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="email">Email Address</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
            />
            <small>Used for important account notifications</small>
          </div>

          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </form>
      </div>

      <div className="settings-card">
        <h2>Public Profile</h2>
        <p className="section-description">
          Customize how others see you. 
          <Link to={`/u/${profileUrl}`} className="profile-link">View your profile →</Link>
        </p>
        
        <form onSubmit={handleProfileSubmit}>
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="bio">Bio</label>
              <textarea
                id="bio"
                value={profileData.bio || ''}
                onChange={(e) => setProfileData({ ...profileData, bio: e.target.value })}
                placeholder="Tell others about yourself..."
                maxLength={500}
                rows={3}
              />
              <small>{(profileData.bio || '').length}/500 characters</small>
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="website">Website</label>
              <input
                type="url"
                id="website"
                value={profileData.website || ''}
                onChange={(e) => setProfileData({ ...profileData, website: e.target.value })}
                placeholder="https://yoursite.com"
              />
            </div>
            <div className="form-group">
              <label htmlFor="profile_slug">
                Custom URL
                {!isPro && <span className="pro-badge">Pro</span>}
              </label>
              <div className="input-with-prefix">
                <span className="input-prefix">/u/</span>
                <input
                  type="text"
                  id="profile_slug"
                  value={profileData.profile_slug || ''}
                  onChange={(e) => setProfileData({ ...profileData, profile_slug: e.target.value })}
                  placeholder={user?.discord_id}
                  disabled={!isPro}
                  pattern="^[a-zA-Z0-9_-]+$"
                />
              </div>
              {!isPro && <small>Upgrade to Pro to use a custom profile URL</small>}
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="github">GitHub Username</label>
              <div className="input-with-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                </svg>
                <input
                  type="text"
                  id="github"
                  value={profileData.github_username || ''}
                  onChange={(e) => setProfileData({ ...profileData, github_username: e.target.value })}
                  placeholder="username"
                />
              </div>
            </div>
            <div className="form-group">
              <label htmlFor="twitter">X/Twitter Username</label>
              <div className="input-with-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                </svg>
                <input
                  type="text"
                  id="twitter"
                  value={profileData.twitter_username || ''}
                  onChange={(e) => setProfileData({ ...profileData, twitter_username: e.target.value })}
                  placeholder="username"
                />
              </div>
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="accent_color">
                Accent Color
                {!isPro && <span className="pro-badge">Pro</span>}
              </label>
              <div className="color-picker-row">
                <input
                  type="color"
                  id="accent_color"
                  value={profileData.accent_color || '#5865f2'}
                  onChange={(e) => setProfileData({ ...profileData, accent_color: e.target.value })}
                  disabled={!isPro}
                />
                <input
                  type="text"
                  value={profileData.accent_color || '#5865f2'}
                  onChange={(e) => setProfileData({ ...profileData, accent_color: e.target.value })}
                  placeholder="#5865f2"
                  pattern="^#[0-9A-Fa-f]{6}$"
                  disabled={!isPro}
                />
              </div>
              {!isPro && <small>Upgrade to Pro to customize your accent color</small>}
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="banner_url">
                Profile Banner
                {!isPro && <span className="pro-badge">Pro</span>}
              </label>
              <input
                type="url"
                id="banner_url"
                value={profileData.banner_url || ''}
                onChange={(e) => setProfileData({ ...profileData, banner_url: e.target.value })}
                placeholder="https://example.com/your-banner.jpg"
                disabled={!isPro}
              />
              {!isPro ? (
                <small>Upgrade to Pro to set a custom profile banner</small>
              ) : (
                <small>Enter an image URL (recommended: 1200x300px). Leave empty for default gradient.</small>
              )}
              {isPro && profileData.banner_url && (
                <div className="banner-preview">
                  <img 
                    src={profileData.banner_url} 
                    alt="Banner preview" 
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = 'none';
                    }}
                    onLoad={(e) => {
                      (e.target as HTMLImageElement).style.display = 'block';
                    }}
                  />
                </div>
              )}
            </div>
          </div>

          <div className="form-row toggles">
            <label className="toggle-item">
              <input
                type="checkbox"
                checked={profileData.profile_public ?? true}
                onChange={(e) => setProfileData({ ...profileData, profile_public: e.target.checked })}
              />
              <span className="toggle-label">
                <strong>Public Profile</strong>
                <small>Allow others to view your profile</small>
              </span>
            </label>
            <label className="toggle-item">
              <input
                type="checkbox"
                checked={profileData.show_addons ?? true}
                onChange={(e) => setProfileData({ ...profileData, show_addons: e.target.checked })}
              />
              <span className="toggle-label">
                <strong>Show Addons</strong>
                <small>Display your addons on your profile</small>
              </span>
            </label>
          </div>

          <button type="submit" className="btn btn-primary" disabled={savingProfile}>
            {savingProfile ? 'Saving...' : 'Save Profile'}
          </button>
        </form>
      </div>

      {/* API Keys Section - Pro+ */}
      <div className="settings-card">
        <h2>
          API Keys
          {!isPro && <span className="pro-badge">Pro</span>}
        </h2>
        
        {isPro ? (
          <ApiKeysManager />
        ) : (
          <div className="upgrade-prompt-inline">
            <p>API keys are available for Pro and Premium subscribers.</p>
            <Link to="/dashboard/subscription" className="btn btn-primary">
              Upgrade to Pro
            </Link>
          </div>
        )}
      </div>

      {/* Webhook Section - Premium only */}
      <div className="settings-card">
        <h2>
          Webhook Notifications
          {!isPremium && <span className="premium-badge">Premium</span>}
        </h2>
        
        {isPremium ? (
          <>
            <p className="section-description">
              Receive real-time notifications when new versions of addons you follow are released.
              Configure your webhook endpoint below.
            </p>
            
            {newWebhookSecret && (
              <div className="api-key-reveal">
                <p className="warning-text">⚠️ Copy this secret now - it won't be shown again!</p>
                <div className="key-display">
                  <code>{newWebhookSecret}</code>
                  <button className="btn btn-secondary btn-sm" onClick={copyWebhookSecret}>
                    Copy
                  </button>
                </div>
              </div>
            )}
            
            <form onSubmit={handleSaveWebhook}>
              <div className="form-group">
                <label htmlFor="webhook_url">Webhook URL</label>
                <input
                  type="url"
                  id="webhook_url"
                  value={webhookUrl}
                  onChange={(e) => setWebhookUrl(e.target.value)}
                  placeholder="https://your-server.com/webhook"
                />
                <small>We'll POST JSON payloads to this URL when events occur</small>
              </div>
              
              <div className="form-row toggles">
                <label className="toggle-item">
                  <input
                    type="checkbox"
                    checked={webhookEnabled}
                    onChange={(e) => setWebhookEnabled(e.target.checked)}
                    disabled={!webhookUrl}
                  />
                  <span className="toggle-label">
                    <strong>Enable Webhook</strong>
                    <small>Start receiving notifications</small>
                  </span>
                </label>
              </div>
              
              <div className="button-row">
                <button type="submit" className="btn btn-primary" disabled={savingWebhook}>
                  {savingWebhook ? 'Saving...' : 'Save Webhook'}
                </button>
                
                {webhookConfig?.webhook_url && (
                  <>
                    <button 
                      type="button"
                      className="btn btn-secondary" 
                      onClick={handleTestWebhook}
                      disabled={testingWebhook || !webhookEnabled}
                    >
                      {testingWebhook ? 'Testing...' : 'Test Webhook'}
                    </button>
                    <button 
                      type="button"
                      className="btn btn-secondary" 
                      onClick={handleRegenerateSecret}
                      disabled={regeneratingSecret}
                    >
                      {regeneratingSecret ? 'Regenerating...' : webhookConfig?.has_secret ? 'Regenerate Secret' : 'Generate Secret'}
                    </button>
                    <button 
                      type="button"
                      className="btn btn-danger" 
                      onClick={handleDeleteWebhook}
                    >
                      Delete
                    </button>
                  </>
                )}
              </div>
            </form>
            
            {webhookConfig?.has_secret && (
              <div className="webhook-info">
                <h4>Verifying Webhooks</h4>
                <p>
                  Each webhook request includes an <code>X-Webhook-Signature</code> header with an HMAC-SHA256 
                  signature. Verify this using your secret to ensure the request came from PlexAddons.
                </p>
              </div>
            )}
          </>
        ) : (
          <div className="upgrade-prompt-inline">
            <p>Webhook notifications are available for Premium subscribers.</p>
            <Link to="/dashboard/subscription" className="btn btn-primary">
              Upgrade to Premium
            </Link>
          </div>
        )}
      </div>

      <div className="settings-card danger-zone">
        <h2>Danger Zone</h2>
        <p>These actions are irreversible. Please be careful.</p>
        
        {!showDeleteConfirm ? (
          <button 
            className="btn btn-danger" 
            onClick={() => setShowDeleteConfirm(true)}
          >
            Delete Account
          </button>
        ) : (
          <div className="delete-confirm-container">
            <p className="delete-warning">
              ⚠️ This will permanently delete your account, all your addons, versions, 
              tickets, and cancel any active subscriptions. This action cannot be undone.
            </p>
            <div className="delete-confirm-input">
              <label>Type <strong>DELETE</strong> to confirm:</label>
              <input
                type="text"
                value={deleteConfirmText}
                onChange={(e) => setDeleteConfirmText(e.target.value)}
                placeholder="DELETE"
                disabled={deleting}
              />
            </div>
            <div className="delete-actions">
              <button
                className="btn btn-secondary"
                onClick={() => {
                  setShowDeleteConfirm(false);
                  setDeleteConfirmText('');
                }}
                disabled={deleting}
              >
                Cancel
              </button>
              <button
                className="btn btn-danger"
                onClick={handleDeleteAccount}
                disabled={deleteConfirmText !== 'DELETE' || deleting}
              >
                {deleting ? 'Deleting...' : 'Delete My Account'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
