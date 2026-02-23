import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../services/api';
import type { Addon, Version } from '../types';
import { useAuth } from '../context/AuthContext';
import MarkdownRenderer from '../components/MarkdownRenderer';
import ScreenshotGallery from '../components/ScreenshotGallery';
import StarButton from '../components/StarButton';
import ReviewsSection from '../components/ReviewsSection';
import './AddonDetail.css';

export default function AddonDetail() {
  const { slug } = useParams<{ slug: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const [addon, setAddon] = useState<Addon | null>(null);
  const [versions, setVersions] = useState<Version[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [purchasing, setPurchasing] = useState(false);
  const [purchased, setPurchased] = useState(false);
  const [purchaseMessage, setPurchaseMessage] = useState<string | null>(null);
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuth();

  // Handle purchase success/cancel redirect from Stripe
  useEffect(() => {
    const purchaseStatus = searchParams.get('purchase');
    if (purchaseStatus === 'success') {
      setPurchased(true);
      setPurchaseMessage('Payment successful! Your license is now active.');
      setSearchParams({}, { replace: true });
    } else if (purchaseStatus === 'cancelled') {
      setPurchaseMessage('Payment was cancelled.');
      setSearchParams({}, { replace: true });
    }
  }, [searchParams, setSearchParams]);

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
      // Check if current user already has a license for this paid addon
      if (addonData.is_paid && isAuthenticated) {
        try {
          const licenses = await api.listMyLicenses(0, 200);
          if (licenses.licenses.some(l => l.addon_id === addonData.id)) {
            setPurchased(true);
          }
        } catch {
          // Ignore — license check is best-effort
        }
      }
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
    <div
      className="addon-detail"
      style={addon.theme_accent_color ? { '--addon-accent': addon.theme_accent_color } as React.CSSProperties : undefined}
    >
      {addon.theme_header_url && (
        <div className="addon-theme-header">
          <img src={addon.theme_header_url} alt="" className="addon-theme-header-img" />
        </div>
      )}
      <div className="addon-detail-header">
        <div className="addon-detail-title">
          {addon.icon_url && (
            <img src={addon.icon_url} alt={addon.name} className="addon-detail-icon" />
          )}
          <h1>
            {addon.name}
            {addon.verified && (
              <span className="verified-badge-large" title="Verified by PlexDevelopment">✓</span>
            )}
          </h1>
          {addon.external && <span className="badge badge-external">External</span>}
          {addon.is_paid && (
            <span className="badge badge-paid">
              {addon.price_cents ? `$${(addon.price_cents / 100).toFixed(2)}` : 'Paid'}
            </span>
          )}
          <StarButton slug={addon.slug} />
        </div>
        {addon.latest_version && (
          <span className="addon-latest-version">v{addon.latest_version}</span>
        )}
      </div>

      {addon.description && (
        <p className="addon-detail-description">{addon.description}</p>
      )}

      {purchaseMessage && (
        <div className={`addon-purchase-message ${purchased ? 'success' : 'info'}`}>
          {purchaseMessage}
        </div>
      )}

      {addon.is_paid && (
        <div className="addon-purchase-section">
          <div className="addon-price-display">
            {addon.price_cents ? `$${(addon.price_cents / 100).toFixed(2)}` : 'Paid'}
          </div>
          {purchased ? (
            <span className="btn btn-secondary addon-purchased-btn" aria-disabled>✓ Purchased</span>
          ) : isAuthenticated && addon.owner_id !== user?.id ? (
            <button
              className="btn btn-primary addon-purchase-btn"
              disabled={purchasing}
              onClick={async () => {
                setPurchasing(true);
                try {
                  const resp = await api.purchaseAddon(addon.id);
                  if (resp.checkout_url) {
                    window.location.href = resp.checkout_url;
                  }
                } catch (err: any) {
                  const msg = err?.message || 'Purchase failed. Please try again.';
                  console.error('Purchase failed:', err);
                  alert(msg);
                  setPurchasing(false);
                }
              }}
            >
              {purchasing ? 'Redirecting to payment…' : 'Purchase'}
            </button>
          ) : !isAuthenticated ? (
            <Link to="/login" className="btn btn-primary addon-purchase-btn">Log in to Purchase</Link>
          ) : null}
        </div>
      )}

      <ScreenshotGallery
        screenshots={addon.screenshots || []}
        bannerUrl={addon.banner_url}
      />

      <div className="addon-detail-meta">
        <span 
          className="addon-author-link"
          onClick={() => addon.owner_discord_id && navigate(`/u/${addon.owner_discord_id}`)}
          style={{ cursor: addon.owner_discord_id ? 'pointer' : 'default' }}
        >
          by {addon.owner_username || 'Unknown'}
          {addon.owner_verified_developer && (
            <span className="verified-dev-badge" title="Verified Developer">✓</span>
          )}
        </span>
        {addon.homepage && (
          <>
            <span className="meta-separator">•</span>
            <a href={addon.homepage} target="_blank" rel="noopener noreferrer">
              Homepage
            </a>
          </>
        )}
        {addon.sponsor_url && (
          <>
            <span className="meta-separator">•</span>
            <a href={addon.sponsor_url} target="_blank" rel="noopener noreferrer" className="donate-link">
              ❤️ Support
            </a>
          </>
        )}
        <span className="meta-separator">•</span>
        <span>{versions.length} version{versions.length !== 1 ? 's' : ''}</span>
        {addon.download_count > 0 && (
          <>
            <span className="meta-separator">•</span>
            <span>⬇ {addon.download_count.toLocaleString()} download{addon.download_count !== 1 ? 's' : ''}</span>
          </>
        )}
      </div>

      {addon.readme && (
        <section className="addon-readme-section">
          <h2>About</h2>
          <div className="addon-readme">
            <MarkdownRenderer content={addon.readme} />
          </div>
        </section>
      )}

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
                    {version.channel && version.channel !== 'stable' && (
                      <span className={`badge badge-channel-${version.channel}`}>{version.channel}</span>
                    )}
                    {version.is_deprecated && <span className="badge badge-deprecated">Deprecated</span>}
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

      <ReviewsSection slug={addon.slug} addonOwnerId={addon.owner_id} />
    </div>
  );
}
