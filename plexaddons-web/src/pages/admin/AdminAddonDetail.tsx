import { useState, useEffect, FormEvent } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { api } from '../../services/api';
import type { Addon, Version, AddonUpdate, VersionUpdate } from '../../types';
import './AdminAddonDetail.css';

export default function AdminAddonDetail() {
  const { addonId } = useParams<{ addonId: string }>();
  const navigate = useNavigate();
  
  const [addon, setAddon] = useState<Addon | null>(null);
  const [versions, setVersions] = useState<Version[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  
  // Form state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [homepage, setHomepage] = useState('');
  const [external, setExternal] = useState(false);
  const [isActive, setIsActive] = useState(true);
  const [isPublic, setIsPublic] = useState(true);
  
  // Version editing
  const [editingVersion, setEditingVersion] = useState<Version | null>(null);
  const [versionForm, setVersionForm] = useState({
    download_url: '',
    description: '',
    changelog_url: '',
    changelog_content: '',
    breaking: false,
    urgent: false,
  });

  useEffect(() => {
    if (addonId) {
      loadAddon();
    }
  }, [addonId]);

  const loadAddon = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.adminGetAddon(parseInt(addonId!));
      setAddon(data.addon);
      setVersions(data.versions || []);
      
      // Populate form
      setName(data.addon.name);
      setDescription(data.addon.description || '');
      setHomepage(data.addon.homepage || '');
      setExternal(data.addon.external);
      setIsActive(data.addon.is_active);
      setIsPublic(data.addon.is_public);
    } catch (err: any) {
      setError(err.message || 'Failed to load addon');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!addon) return;
    
    setSaving(true);
    setError(null);
    setSuccessMessage(null);
    
    try {
      const data: AddonUpdate = {
        name,
        description: description || undefined,
        homepage: homepage || undefined,
        external,
        is_active: isActive,
        is_public: isPublic,
      };
      
      await api.adminUpdateAddon(addon.id, data);
      setSuccessMessage('Addon updated successfully');
      loadAddon();
    } catch (err: any) {
      setError(err.message || 'Failed to update addon');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!addon) return;
    if (!confirm(`Are you sure you want to delete "${addon.name}"? This will also delete all versions. This action cannot be undone.`)) {
      return;
    }
    
    try {
      await api.adminDeleteAddon(addon.id);
      navigate('/admin/addons');
    } catch (err: any) {
      setError(err.message || 'Failed to delete addon');
    }
  };

  const handleEditVersion = (version: Version) => {
    setEditingVersion(version);
    setVersionForm({
      download_url: version.download_url,
      description: version.description || '',
      changelog_url: version.changelog_url || '',
      changelog_content: version.changelog_content || '',
      breaking: version.breaking,
      urgent: version.urgent,
    });
  };

  const handleSaveVersion = async () => {
    if (!addon || !editingVersion) return;
    
    setSaving(true);
    setError(null);
    
    try {
      const data: VersionUpdate = {
        download_url: versionForm.download_url,
        description: versionForm.description || undefined,
        changelog_url: versionForm.changelog_url || undefined,
        changelog_content: versionForm.changelog_content || undefined,
        breaking: versionForm.breaking,
        urgent: versionForm.urgent,
      };
      
      await api.adminUpdateVersion(addon.id, editingVersion.id, data);
      setEditingVersion(null);
      setSuccessMessage('Version updated successfully');
      loadAddon();
    } catch (err: any) {
      setError(err.message || 'Failed to update version');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteVersion = async (version: Version) => {
    if (!addon) return;
    if (!confirm(`Are you sure you want to delete version ${version.version}? This action cannot be undone.`)) {
      return;
    }
    
    try {
      await api.adminDeleteVersion(addon.id, version.id);
      setSuccessMessage('Version deleted successfully');
      loadAddon();
    } catch (err: any) {
      setError(err.message || 'Failed to delete version');
    }
  };

  if (loading) {
    return (
      <div className="loading-page">
        <div className="spinner" />
      </div>
    );
  }

  if (!addon) {
    return (
      <div className="admin-addon-detail">
        <div className="error-message">Addon not found</div>
        <Link to="/admin/addons" className="btn btn-secondary">Back to Addons</Link>
      </div>
    );
  }

  return (
    <div className="admin-addon-detail">
      <div className="detail-header">
        <div>
          <Link to="/admin/addons" className="back-link">← Back to Addons</Link>
          <h1>Edit Addon: {addon.name}</h1>
          <p className="addon-meta">
            Owned by <strong>{addon.owner_username || 'Unknown'}</strong> • 
            ID: {addon.id} • 
            Slug: <code>{addon.slug}</code>
          </p>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}
      {successMessage && <div className="success-message">{successMessage}</div>}

      <div className="detail-content">
        <div className="detail-section">
          <h2>Addon Details</h2>
          <form onSubmit={handleSubmit} className="addon-form">
            <div className="form-group">
              <label htmlFor="name">Name *</label>
              <input
                id="name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="description">Description</label>
              <textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
              />
            </div>

            <div className="form-group">
              <label htmlFor="homepage">Homepage URL</label>
              <input
                id="homepage"
                type="url"
                value={homepage}
                onChange={(e) => setHomepage(e.target.value)}
                placeholder="https://..."
              />
            </div>

            <div className="form-row">
              <div className="checkbox-group">
                <label>
                  <input
                    type="checkbox"
                    checked={external}
                    onChange={(e) => setExternal(e.target.checked)}
                  />
                  <span>External (free addon)</span>
                </label>
              </div>

              <div className="checkbox-group">
                <label>
                  <input
                    type="checkbox"
                    checked={isActive}
                    onChange={(e) => setIsActive(e.target.checked)}
                  />
                  <span>Active</span>
                </label>
              </div>

              <div className="checkbox-group">
                <label>
                  <input
                    type="checkbox"
                    checked={isPublic}
                    onChange={(e) => setIsPublic(e.target.checked)}
                  />
                  <span>Public</span>
                </label>
              </div>
            </div>

            <div className="form-actions">
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
              <button type="button" onClick={handleDelete} className="btn btn-danger">
                Delete Addon
              </button>
            </div>
          </form>
        </div>

        <div className="detail-section">
          <div className="versions-header">
            <h2>Versions ({versions.length})</h2>
          </div>

          {versions.length === 0 ? (
            <p className="no-versions">No versions yet</p>
          ) : (
            <div className="versions-list">
              {versions.map((version, index) => (
                <div key={version.id} className="version-row">
                  {editingVersion?.id === version.id ? (
                    <div className="version-edit-form">
                      <div className="version-edit-header">
                        <h3>Editing v{version.version}</h3>
                        <button 
                          type="button" 
                          className="btn btn-sm btn-secondary"
                          onClick={() => setEditingVersion(null)}
                        >
                          Cancel
                        </button>
                      </div>
                      
                      <div className="form-group">
                        <label>Download URL *</label>
                        <input
                          type="url"
                          value={versionForm.download_url}
                          onChange={(e) => setVersionForm({...versionForm, download_url: e.target.value})}
                          required
                        />
                      </div>
                      
                      <div className="form-group">
                        <label>Description</label>
                        <input
                          type="text"
                          value={versionForm.description}
                          onChange={(e) => setVersionForm({...versionForm, description: e.target.value})}
                        />
                      </div>
                      
                      <div className="form-group">
                        <label>Changelog URL</label>
                        <input
                          type="url"
                          value={versionForm.changelog_url}
                          onChange={(e) => setVersionForm({...versionForm, changelog_url: e.target.value})}
                        />
                      </div>
                      
                      <div className="form-group">
                        <label>Changelog Content</label>
                        <textarea
                          value={versionForm.changelog_content}
                          onChange={(e) => setVersionForm({...versionForm, changelog_content: e.target.value})}
                          rows={4}
                        />
                      </div>
                      
                      <div className="form-row">
                        <label className="checkbox-inline">
                          <input
                            type="checkbox"
                            checked={versionForm.breaking}
                            onChange={(e) => setVersionForm({...versionForm, breaking: e.target.checked})}
                          />
                          Breaking
                        </label>
                        <label className="checkbox-inline">
                          <input
                            type="checkbox"
                            checked={versionForm.urgent}
                            onChange={(e) => setVersionForm({...versionForm, urgent: e.target.checked})}
                          />
                          Urgent
                        </label>
                      </div>
                      
                      <div className="form-actions">
                        <button 
                          type="button" 
                          className="btn btn-primary"
                          onClick={handleSaveVersion}
                          disabled={saving}
                        >
                          {saving ? 'Saving...' : 'Save Version'}
                        </button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <div className="version-info">
                        <span className="version-number">v{version.version}</span>
                        {index === 0 && <span className="badge badge-latest">Latest</span>}
                        {version.urgent && <span className="badge badge-urgent">Urgent</span>}
                        {version.breaking && <span className="badge badge-breaking">Breaking</span>}
                      </div>
                      <span className="version-date">
                        {new Date(version.release_date).toLocaleDateString()}
                      </span>
                      <span className="version-desc">
                        {version.description || '-'}
                      </span>
                      <div className="version-actions">
                        <button
                          className="btn btn-sm btn-secondary"
                          onClick={() => handleEditVersion(version)}
                        >
                          Edit
                        </button>
                        <button
                          className="btn btn-sm btn-danger"
                          onClick={() => handleDeleteVersion(version)}
                        >
                          Delete
                        </button>
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
