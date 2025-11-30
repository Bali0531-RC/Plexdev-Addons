import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../services/api';
import type { Addon, Version } from '../types';
import MarkdownRenderer from '../components/MarkdownRenderer';
import './AddonDetail.css';

export default function AddonDetail() {
  const { slug } = useParams<{ slug: string }>();
  const [addon, setAddon] = useState<Addon | null>(null);
  const [versions, setVersions] = useState<Version[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (slug) {
      loadAddon();
    }
  }, [slug]);

  const loadAddon = async () => {
    try {
      setLoading(true);
      const [addonData, versionsData] = await Promise.all([
        api.getAddon(slug!),
        api.listVersions(slug!),
      ]);
      setAddon(addonData);
      setVersions(versionsData.versions);
    } catch (err) {
      setError('Addon not found');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  if (loading) {
    return (
      <div className="loading-page">
        <div className="spinner" />
      </div>
    );
  }

  if (error || !addon) {
    return (
      <div className="error-page">
        <h2>Addon Not Found</h2>
        <p>{error || 'The addon you are looking for does not exist.'}</p>
        <Link to="/addons" className="btn btn-primary">
          Back to Addons
        </Link>
      </div>
    );
  }

  return (
    <div className="addon-detail">
      <div className="addon-detail-header">
        <div className="addon-detail-title">
          <h1>
            {addon.name}
            {addon.verified && (
              <span className="verified-badge-large" title="Verified by PlexDevelopment">✓</span>
            )}
          </h1>
          {addon.external && <span className="badge badge-external">External</span>}
        </div>
        {addon.latest_version && (
          <span className="addon-latest-version">v{addon.latest_version}</span>
        )}
      </div>

      {addon.description && (
        <p className="addon-detail-description">{addon.description}</p>
      )}

      <div className="addon-detail-meta">
        <span 
          className="addon-author-link"
          onClick={() => addon.owner_discord_id && (window.location.href = `/u/${addon.owner_discord_id}`)}
          style={{ cursor: addon.owner_discord_id ? 'pointer' : 'default' }}
        >
          by {addon.owner_username || 'Unknown'}
        </span>
        {addon.homepage && (
          <>
            <span className="meta-separator">•</span>
            <a href={addon.homepage} target="_blank" rel="noopener noreferrer">
              Homepage
            </a>
          </>
        )}
        <span className="meta-separator">•</span>
        <span>{versions.length} version{versions.length !== 1 ? 's' : ''}</span>
      </div>

      <section className="versions-section">
        <h2>Versions</h2>
        {versions.length === 0 ? (
          <p className="no-versions">No versions available yet.</p>
        ) : (
          <div className="versions-list">
            {versions.map((version, index) => (
              <div 
                key={version.id} 
                className={`version-item ${index === 0 ? 'version-latest' : ''}`}
              >
                <div className="version-header">
                  <div className="version-info">
                    <span className="version-number">v{version.version}</span>
                    {index === 0 && <span className="badge badge-latest">Latest</span>}
                    {version.breaking && <span className="badge badge-breaking">Breaking</span>}
                    {version.urgent && <span className="badge badge-urgent">Urgent</span>}
                  </div>
                  <span className="version-date">{formatDate(version.release_date)}</span>
                </div>
                
                {version.description && (
                  <p className="version-description">{version.description}</p>
                )}

                {version.changelog_content && (
                  <div className="version-changelog">
                    <h4>Changelog</h4>
                    <MarkdownRenderer content={version.changelog_content} />
                  </div>
                )}

                <div className="version-actions">
                  <a 
                    href={version.download_url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="btn btn-sm btn-primary"
                  >
                    Download
                  </a>
                  {version.changelog_url && (
                    <a 
                      href={version.changelog_url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="btn btn-sm btn-secondary"
                    >
                      View Changelog
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
