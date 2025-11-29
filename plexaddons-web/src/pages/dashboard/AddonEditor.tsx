import { useState, useEffect, FormEvent } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { api } from '../../services/api';
import type { Addon, Version, AddonCreate, AddonUpdate } from '../../types';
import './AddonEditor.css';

export default function AddonEditor() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const isNew = !slug || slug === 'new';

  const [addon, setAddon] = useState<Addon | null>(null);
  const [versions, setVersions] = useState<Version[]>([]);
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [homepage, setHomepage] = useState('');
  const [external, setExternal] = useState(false);
  const [isActive, setIsActive] = useState(true);
  const [isPublic, setIsPublic] = useState(true);

  useEffect(() => {
    if (!isNew && slug) {
      loadAddon();
    }
  }, [slug, isNew]);

  const loadAddon = async () => {
    try {
      setLoading(true);
      const [addonData, versionsData] = await Promise.all([
        api.getAddon(slug!),
        api.listVersions(slug!),
      ]);
      setAddon(addonData);
      setVersions(versionsData.versions);
      
      // Populate form
      setName(addonData.name);
      setDescription(addonData.description || '');
      setHomepage(addonData.homepage || '');
      setExternal(addonData.external);
      setIsActive(addonData.is_active);
      setIsPublic(addonData.is_public);
    } catch (err) {
      setError('Failed to load addon');
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
        const data: AddonCreate = {
          name,
          description: description || undefined,
          homepage: homepage || undefined,
          external,
        };
        const newAddon = await api.createAddon(data);
        navigate(`/dashboard/addons/${newAddon.slug}`, { replace: true });
      } else {
        const data: AddonUpdate = {
          name,
          description: description || undefined,
          homepage: homepage || undefined,
          external,
          is_active: isActive,
          is_public: isPublic,
        };
        await api.updateAddon(slug!, data);
        navigate('/dashboard/addons');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to save addon');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this addon? This action cannot be undone.')) {
      return;
    }

    try {
      await api.deleteAddon(slug!);
      navigate('/dashboard/addons');
    } catch (err: any) {
      setError(err.message || 'Failed to delete addon');
    }
  };

  if (loading) {
    return (
      <div className="loading-page">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className="addon-editor">
      <div className="editor-header">
        <h1>{isNew ? 'Create Addon' : `Edit ${addon?.name}`}</h1>
        {!isNew && (
          <Link to={`/addons/${slug}`} className="btn btn-secondary" target="_blank">
            View Public Page
          </Link>
        )}
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="editor-form">
        <div className="form-section">
          <h2>Basic Information</h2>
          
          <div className="form-group">
            <label htmlFor="name">Name *</label>
            <input
              type="text"
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              placeholder="My Awesome Addon"
            />
          </div>

          <div className="form-group">
            <label htmlFor="description">Description</label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="A brief description of your addon"
              rows={3}
            />
          </div>

          <div className="form-group">
            <label htmlFor="homepage">Homepage URL</label>
            <input
              type="url"
              id="homepage"
              value={homepage}
              onChange={(e) => setHomepage(e.target.value)}
              placeholder="https://github.com/username/addon"
            />
          </div>
        </div>

        <div className="form-section">
          <h2>Settings</h2>
          
          <div className="form-group checkbox-group">
            <label>
              <input
                type="checkbox"
                checked={external}
                onChange={(e) => setExternal(e.target.checked)}
              />
              <span>External addon (hosted elsewhere)</span>
            </label>
          </div>

          {!isNew && (
            <>
              <div className="form-group checkbox-group">
                <label>
                  <input
                    type="checkbox"
                    checked={isActive}
                    onChange={(e) => setIsActive(e.target.checked)}
                  />
                  <span>Active</span>
                </label>
              </div>

              <div className="form-group checkbox-group">
                <label>
                  <input
                    type="checkbox"
                    checked={isPublic}
                    onChange={(e) => setIsPublic(e.target.checked)}
                  />
                  <span>Public (visible in addon list)</span>
                </label>
              </div>
            </>
          )}
        </div>

        <div className="form-actions">
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? 'Saving...' : isNew ? 'Create Addon' : 'Save Changes'}
          </button>
          <Link to="/dashboard/addons" className="btn btn-secondary">
            Cancel
          </Link>
          {!isNew && (
            <button type="button" onClick={handleDelete} className="btn btn-danger">
              Delete Addon
            </button>
          )}
        </div>
      </form>

      {!isNew && (
        <div className="versions-section">
          <div className="versions-header">
            <h2>Versions ({versions.length})</h2>
            <Link to={`/dashboard/addons/${slug}/versions/new`} className="btn btn-primary">
              + Add Version
            </Link>
          </div>

          {versions.length === 0 ? (
            <p className="no-versions">No versions yet</p>
          ) : (
            <div className="versions-list">
              {versions.map((version, index) => (
                <div key={version.id} className="version-row">
                  <div className="version-info">
                    <span className="version-number">v{version.version}</span>
                    {index === 0 && <span className="badge badge-latest">Latest</span>}
                    {version.breaking && <span className="badge badge-breaking">Breaking</span>}
                  </div>
                  <span className="version-date">
                    {new Date(version.release_date).toLocaleDateString()}
                  </span>
                  <Link 
                    to={`/dashboard/addons/${slug}/versions/${version.version}`}
                    className="btn btn-sm btn-secondary"
                  >
                    Edit
                  </Link>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
