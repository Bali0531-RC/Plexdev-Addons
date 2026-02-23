import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { api } from '../services/api';
import type { AddonLicense, StripeConnectStatus, RevenueStats } from '../types';
import './MarketplaceManager.css';

interface Props {
  addonId: number;
  isPaid: boolean;
  priceCents: number | null;
  revenueSplitPercent: number;
  sponsorUrl: string | null;
}

type Tab = 'pricing' | 'licenses' | 'revenue' | 'connect' | 'sponsor';

export default function MarketplaceManager({ addonId, isPaid, priceCents, revenueSplitPercent, sponsorUrl: initialSponsorUrl }: Props) {
  const [tab, setTab] = useState<Tab>('pricing');

  return (
    <div className="marketplace-manager">
      <h2>Marketplace &amp; Sponsorship</h2>
      <div className="marketplace-tabs">
        {(['pricing', 'licenses', 'revenue', 'connect', 'sponsor'] as Tab[]).map(t => (
          <button key={t} className={tab === t ? 'active' : ''} onClick={() => setTab(t)}>
            {t === 'pricing' ? 'Pricing' : t === 'licenses' ? 'Licenses' : t === 'revenue' ? 'Revenue' : t === 'connect' ? 'Stripe Connect' : 'Sponsor'}
          </button>
        ))}
      </div>

      <div className="marketplace-panel">
        {tab === 'pricing' && <PricingPanel addonId={addonId} isPaid={isPaid} priceCents={priceCents} revenueSplitPercent={revenueSplitPercent} />}
        {tab === 'licenses' && <LicensesPanel addonId={addonId} />}
        {tab === 'revenue' && <RevenuePanel addonId={addonId} />}
        {tab === 'connect' && <ConnectPanel />}
        {tab === 'sponsor' && <SponsorPanel addonId={addonId} sponsorUrl={initialSponsorUrl} />}
      </div>
    </div>
  );
}

// ─── Pricing Panel ───

function PricingPanel({ addonId, isPaid: initPaid, priceCents: initPrice, revenueSplitPercent: initSplit }: {
  addonId: number; isPaid: boolean; priceCents: number | null; revenueSplitPercent: number;
}) {
  const [paid, setPaid] = useState(initPaid);
  const [price, setPrice] = useState(initPrice ? (initPrice / 100).toFixed(2) : '');
  const [split, setSplit] = useState(String(initSplit));
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      const cents = Math.round(parseFloat(price || '0') * 100);
      if (paid && cents < 100) {
        toast.error('Minimum price is $1.00');
        return;
      }
      await api.updateAddonPricing(addonId, {
        is_paid: paid,
        price_cents: paid ? cents : undefined,
        revenue_split_percent: parseInt(split) || 90,
      });
      toast.success('Pricing updated');
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to update pricing');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="pricing-form">
      <div className="pricing-toggle">
        <input type="checkbox" id="is-paid" checked={paid} onChange={e => setPaid(e.target.checked)} />
        <label htmlFor="is-paid">Enable paid licensing for this addon</label>
      </div>

      {paid && (
        <>
          <div className="form-group">
            <label>Price (USD)</label>
            <input type="number" min="1" step="0.01" value={price} onChange={e => setPrice(e.target.value)} placeholder="9.99" />
            <span className="hint">Minimum $1.00</span>
          </div>

          <div className="form-group">
            <label>Revenue Split (your share %)</label>
            <input type="number" min="50" max="100" value={split} onChange={e => setSplit(e.target.value)} />
            <span className="hint">Platform takes the remainder</span>
          </div>
        </>
      )}

      <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
        {saving ? 'Saving...' : 'Save Pricing'}
      </button>
    </div>
  );
}

// ─── Licenses Panel ───

function LicensesPanel({ addonId }: { addonId: number }) {
  const [licenses, setLicenses] = useState<AddonLicense[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadLicenses();
  }, [addonId]);

  const loadLicenses = async () => {
    try {
      const resp = await api.listAddonLicenses(addonId);
      setLicenses(resp.licenses);
      setTotal(resp.total);
    } catch {
      toast.error('Failed to load licenses');
    } finally {
      setLoading(false);
    }
  };

  const handleRevoke = async (licenseId: number) => {
    try {
      await api.revokeLicense(licenseId);
      toast.success('License revoked');
      loadLicenses();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to revoke');
    }
  };

  if (loading) return <div className="empty-state">Loading licenses...</div>;
  if (total === 0) return <div className="empty-state">No licenses issued yet</div>;

  return (
    <div>
      <p style={{ marginBottom: '1rem', color: 'var(--text-secondary)' }}>{total} license(s) issued</p>
      <table className="license-table">
        <thead>
          <tr>
            <th>License Key</th>
            <th>Status</th>
            <th>Server ID</th>
            <th>Amount</th>
            <th>Created</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {licenses.map(lic => (
            <tr key={lic.id}>
              <td><span className="license-key">{lic.license_key.slice(0, 16)}...</span></td>
              <td><span className={`license-status ${lic.status}`}>{lic.status}</span></td>
              <td>{lic.server_id || '—'}</td>
              <td>${(lic.amount_cents / 100).toFixed(2)}</td>
              <td>{new Date(lic.created_at).toLocaleDateString()}</td>
              <td>
                {lic.status === 'active' && (
                  <button className="btn btn-sm btn-danger" onClick={() => handleRevoke(lic.id)}>Revoke</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── Revenue Panel ───

function RevenuePanel({ addonId }: { addonId: number }) {
  const [stats, setStats] = useState<RevenueStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getRevenueStats(addonId)
      .then(setStats)
      .catch(() => toast.error('Failed to load revenue'))
      .finally(() => setLoading(false));
  }, [addonId]);

  if (loading) return <div className="empty-state">Loading revenue...</div>;
  if (!stats) return <div className="empty-state">No revenue data</div>;

  const fmt = (cents: number) => `$${(cents / 100).toFixed(2)}`;

  return (
    <div className="revenue-grid">
      <div className="revenue-card">
        <div className="value">{stats.total_sales}</div>
        <div className="label">Total Sales</div>
      </div>
      <div className="revenue-card">
        <div className="value">{fmt(stats.total_revenue_cents)}</div>
        <div className="label">Total Revenue</div>
      </div>
      <div className="revenue-card">
        <div className="value">{fmt(stats.total_earnings_cents)}</div>
        <div className="label">Your Earnings</div>
      </div>
      <div className="revenue-card">
        <div className="value">{fmt(stats.total_fees_cents)}</div>
        <div className="label">Platform Fees</div>
      </div>
      <div className="revenue-card">
        <div className="value">{stats.active_licenses}</div>
        <div className="label">Active Licenses</div>
      </div>
    </div>
  );
}

// ─── Stripe Connect Panel ───

function ConnectPanel() {
  const [status, setStatus] = useState<StripeConnectStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getStripeConnectStatus()
      .then(setStatus)
      .catch(() => toast.error('Failed to load Connect status'))
      .finally(() => setLoading(false));
  }, []);

  const handleOnboard = async () => {
    try {
      const currentUrl = window.location.href;
      const resp = await api.startStripeConnectOnboarding(currentUrl, currentUrl);
      if (resp.onboarding_url) {
        window.location.href = resp.onboarding_url;
      } else {
        toast.success('Connect account created');
        const updated = await api.getStripeConnectStatus();
        setStatus(updated);
      }
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to start onboarding');
    }
  };

  if (loading) return <div className="empty-state">Loading...</div>;

  return (
    <div>
      <div className="connect-status">
        <span className={`connect-badge ${status?.has_connect_account ? 'connected' : 'not-connected'}`}>
          {status?.has_connect_account ? 'Connected' : 'Not Connected'}
        </span>
        {status?.has_connect_account ? (
          <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Account: {status.account_id} &middot; Payouts: {status.payouts_enabled ? 'Enabled' : 'Disabled'}
          </span>
        ) : (
          <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Connect your Stripe account to receive payouts for paid addons
          </span>
        )}
        {!status?.has_connect_account && (
          <div className="connect-action">
            <button className="btn btn-primary" onClick={handleOnboard}>Set Up Stripe Connect</button>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Sponsor Panel ───

function SponsorPanel({ addonId, sponsorUrl: initial }: { addonId: number; sponsorUrl: string | null }) {
  const [url, setUrl] = useState(initial || '');
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.updateSponsorUrl(addonId, url || null);
      toast.success('Sponsor URL updated');
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to update');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="sponsor-form">
      <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
        Add a sponsor/donate link that will be displayed on your addon's page.
      </p>
      <div className="form-group">
        <label>Sponsor URL</label>
        <input
          type="url"
          value={url}
          onChange={e => setUrl(e.target.value)}
          placeholder="https://github.com/sponsors/you"
        />
      </div>
      {url && (
        <div className="sponsor-preview">
          ❤️ <a href={url} target="_blank" rel="noopener noreferrer">Sponsor this addon</a>
        </div>
      )}
      <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
        {saving ? 'Saving...' : 'Save Sponsor URL'}
      </button>
    </div>
  );
}
