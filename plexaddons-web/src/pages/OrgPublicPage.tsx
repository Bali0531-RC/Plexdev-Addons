import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../services/api';
import type { OrgPublicPage as OrgPublicPageType } from '../types';
import { PackageIcon } from '../components/Icons';
import './OrgPublicPage.css';

export default function OrgPublicPage() {
  const { orgSlug } = useParams<{ orgSlug: string }>();
  const [org, setOrg] = useState<OrgPublicPageType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!orgSlug) return;
    loadOrg();
  }, [orgSlug]);

  const loadOrg = async () => {
    try {
      setLoading(true);
      const data = await api.getPublicOrgPage(orgSlug!);
      setOrg(data);
    } catch {
      setError('Organization not found');
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="loading-page"><div className="spinner" /></div>;
  if (error || !org) return <div className="error-page"><h2>{error || 'Not Found'}</h2></div>;

  return (
    <div className="org-public-page">
      {org.banner_url && (
        <div className="org-banner" style={{ backgroundImage: `url(${org.banner_url})` }} />
      )}
      <div className="org-public-header">
        <div className="org-avatar-large">
          {org.avatar_url ? (
            <img src={org.avatar_url} alt={org.name} />
          ) : (
            <span>{org.name.charAt(0).toUpperCase()}</span>
          )}
        </div>
        <div className="org-header-info">
          <h1>{org.name}</h1>
          {org.description && <p className="org-description">{org.description}</p>}
          <div className="org-meta">
            <span>{org.member_count} members</span>
            <span>{org.addon_count} addons</span>
            {org.owner_username && <span>Owner: {org.owner_username}</span>}
          </div>
        </div>
      </div>

      <div className="org-addons-section">
        <h2>Addons ({org.addons.length})</h2>
        {org.addons.length === 0 ? (
          <p className="no-data">No public addons yet.</p>
        ) : (
          <div className="org-addons-grid">
            {org.addons.map(addon => (
              <Link key={addon.id} to={`/addons/${addon.slug}`} className="addon-card">
                <div className="addon-card-icon">
                  {addon.icon_url ? (
                    <img src={addon.icon_url} alt={addon.name} />
                  ) : (
                    <PackageIcon size={24} />
                  )}
                </div>
                <div className="addon-card-info">
                  <h3>{addon.name}</h3>
                  {addon.description && (
                    <p className="addon-card-desc">
                      {addon.description.length > 100
                        ? addon.description.substring(0, 100) + '...'
                        : addon.description}
                    </p>
                  )}
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
