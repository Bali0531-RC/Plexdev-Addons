import { useState, useEffect, FormEvent } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { toast } from 'sonner';
import { api } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import type { Version, VersionCreate, VersionUpdate } from '../../types';
import './VersionEditor.css';

export default function VersionEditor() {
  const { slug, version: versionParam } = useParams<{ slug: string; version: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const isNew = !versionParam || versionParam === 'new';

  const [existingVersion, setExistingVersion] = useState<Version | null>(null);
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [version, setVersion] = useState('');
  const [downloadUrl, setDownloadUrl] = useState('');
  const [description, setDescription] = useState('');
  const [changelogUrl, setChangelogUrl] = useState('');
  const [changelogContent, setChangelogContent] = useState('');
  const [breaking, setBreaking] = useState(false);
  const [urgent, setUrgent] = useState(false);
  const [releaseDate, setReleaseDate] = useState('');
  const [scheduledReleaseAt, setScheduledReleaseAt] = useState('');
  const [rolloutPercentage, setRolloutPercentage] = useState<number | ''>('');

  // Tier checks
  const effectiveTier = user?.effective_tier || user?.subscription_tier || 'free';
  const canSchedule = effectiveTier === 'pro' || effectiveTier === 'premium';
  const canRollout = effectiveTier === 'premium';

  useEffect(() => {
    if (!isNew && slug && versionParam) {
      loadVersion();
    }
  }, [slug, versionParam, isNew]);

  const loadVersion = async () => {
    try {
      setLoading(true);
      const data = await api.getVersion(slug!, versionParam!);
      setExistingVersion(data);
      
      // Populate form
      setVersion(data.version);
      setDownloadUrl(data.download_url);
      setDescription(data.description || '');
      setChangelogUrl(data.changelog_url || '');
      setChangelogContent(data.changelog_content || '');
      setBreaking(data.breaking);
      setUrgent(data.urgent);
      setReleaseDate(data.release_date.split('T')[0]);
      if (data.scheduled_release_at) {
        setScheduledReleaseAt(data.scheduled_release_at.slice(0, 16)); // format: YYYY-MM-DDTHH:MM
      }
      if (data.rollout_percentage !== null) {
        setRolloutPercentage(data.rollout_percentage);
      }
    } catch (err) {
      setError('Failed to load version');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSaving(true);

    try {
      if (isNew) {
        const data: VersionCreate = {
          version,
          download_url: downloadUrl,
          description: description || undefined,
          changelog_url: changelogUrl || undefined,
          changelog_content: changelogContent || undefined,
          breaking,
          urgent,
          release_date: releaseDate || undefined,
          scheduled_release_at: canSchedule && scheduledReleaseAt ? scheduledReleaseAt : undefined,
          rollout_percentage: canRollout && rolloutPercentage !== '' ? rolloutPercentage : undefined,
        };
        await api.createVersion(slug!, data);
      } else {
        const data: VersionUpdate = {
          download_url: downloadUrl,
          description: description || undefined,
          changelog_url: changelogUrl || undefined,
          changelog_content: changelogContent || undefined,
          breaking,
          urgent,
          scheduled_release_at: canSchedule ? (scheduledReleaseAt || undefined) : undefined,
          rollout_percentage: canRollout ? (rolloutPercentage !== '' ? rolloutPercentage : undefined) : undefined,
        };
        await api.updateVersion(slug!, versionParam!, data);
      }
      navigate(`/dashboard/addons/${slug}`);
    } catch (err: any) {
      setError(err.message || 'Failed to save version');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this version? This action cannot be undone.')) return;
    toast.promise(
      api.deleteVersion(slug!, versionParam!).then(() => navigate(`/dashboard/addons/${slug}`)),
      {
        loading: 'Deleting version...',
        success: 'Version deleted',
        error: (err: any) => err.message || 'Failed to delete version',
      }
    );
  };

  if (loading) {
    return (
      <div className="loading-page">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className="version-editor">
      <div className="editor-header">
        <div>
          <Link to={`/dashboard/addons/${slug}`} className="back-link">
            ← Back to addon
          </Link>
          <h1>{isNew ? 'Add Version' : `Edit v${existingVersion?.version}`}</h1>
        </div>
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="editor-form">
        <div className="form-section">
          <h2>Version Information</h2>
          
          <div className="form-group">
            <label htmlFor="version">Version Number *</label>
            <input
              type="text"
              id="version"
              value={version}
              onChange={(e) => setVersion(e.target.value)}
              required
              disabled={!isNew}
              placeholder="1.0.0"
            />
            <small>Use semantic versioning (e.g., 1.0.0, 2.1.3)</small>
          </div>

          <div className="form-group">
            <label htmlFor="downloadUrl">Download URL *</label>
            <input
              type="url"
              id="downloadUrl"
              value={downloadUrl}
              onChange={(e) => setDownloadUrl(e.target.value)}
              required
              placeholder="https://github.com/user/repo/releases/download/v1.0.0/addon.zip"
            />
          </div>

          <div className="form-group">
            <label htmlFor="releaseDate">Release Date</label>
            <input
              type="date"
              id="releaseDate"
              value={releaseDate}
              onChange={(e) => setReleaseDate(e.target.value)}
              disabled={!isNew}
            />
          </div>

          <div className="form-group">
            <label htmlFor="description">Description</label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief description of this version"
              rows={2}
            />
          </div>
        </div>

        <div className="form-section">
          <h2>Changelog</h2>
          
          <div className="form-group">
            <label htmlFor="changelogUrl">Changelog URL</label>
            <input
              type="url"
              id="changelogUrl"
              value={changelogUrl}
              onChange={(e) => setChangelogUrl(e.target.value)}
              placeholder="https://github.com/user/repo/blob/main/CHANGELOG.md"
            />
          </div>

          <div className="form-group">
            <label htmlFor="changelogContent">Changelog Content</label>
            <textarea
              id="changelogContent"
              value={changelogContent}
              onChange={(e) => setChangelogContent(e.target.value)}
              placeholder="- Added new feature&#10;- Fixed bug&#10;- Improved performance"
              rows={6}
            />
          </div>
        </div>

        <div className="form-section">
          <h2>
            Release Scheduling
            {!canSchedule && <span className="tier-badge pro">Pro+</span>}
          </h2>
          
          <div className="form-group">
            <label htmlFor="scheduledReleaseAt">Scheduled Release</label>
            <input
              type="datetime-local"
              id="scheduledReleaseAt"
              value={scheduledReleaseAt}
              onChange={(e) => setScheduledReleaseAt(e.target.value)}
              disabled={!canSchedule}
              min={new Date().toISOString().slice(0, 16)}
            />
            <small>
              {canSchedule 
                ? 'Leave empty to publish immediately. Set a future date to schedule the release.'
                : 'Upgrade to Pro or Premium to schedule releases.'}
            </small>
          </div>

          <div className="form-group">
            <label htmlFor="rolloutPercentage">
              Gradual Rollout
              {!canRollout && <span className="tier-badge premium">Premium</span>}
            </label>
            <input
              type="number"
              id="rolloutPercentage"
              value={rolloutPercentage}
              onChange={(e) => setRolloutPercentage(e.target.value ? parseInt(e.target.value) : '')}
              disabled={!canRollout}
              min={1}
              max={100}
              placeholder="100"
            />
            <small>
              {canRollout 
                ? 'Percentage of users who will receive this update (1-100). Leave empty for 100%.'
                : 'Upgrade to Premium for A/B testing and gradual rollouts.'}
            </small>
          </div>

          {existingVersion && (
            <div className="version-status">
              <span className={`status-indicator ${existingVersion.is_published ? 'published' : 'scheduled'}`}>
                {existingVersion.is_published ? '● Published' : '◐ Scheduled'}
              </span>
              {existingVersion.rollout_percentage !== null && existingVersion.rollout_percentage < 100 && (
                <span className="rollout-indicator">
                  {existingVersion.rollout_percentage}% rollout
                </span>
              )}
            </div>
          )}
        </div>

        <div className="form-section">
          <h2>Flags</h2>
          
          <div className="form-group checkbox-group">
            <label>
              <input
                type="checkbox"
                checked={breaking}
                onChange={(e) => setBreaking(e.target.checked)}
              />
              <span>Breaking change</span>
            </label>
            <small>This version contains changes that may break existing setups</small>
          </div>

          <div className="form-group checkbox-group">
            <label>
              <input
                type="checkbox"
                checked={urgent}
                onChange={(e) => setUrgent(e.target.checked)}
              />
              <span>Urgent update</span>
            </label>
            <small>This update should be installed as soon as possible</small>
          </div>
        </div>

        <div className="form-actions">
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? 'Saving...' : isNew ? 'Create Version' : 'Save Changes'}
          </button>
          <Link to={`/dashboard/addons/${slug}`} className="btn btn-secondary">
            Cancel
          </Link>
          {!isNew && (
            <button type="button" onClick={handleDelete} className="btn btn-danger">
              Delete Version
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
