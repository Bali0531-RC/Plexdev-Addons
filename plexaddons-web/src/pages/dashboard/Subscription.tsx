import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { useAuth } from '../../context/AuthContext';
import { api, safeRedirect } from '../../services/api';
import type { Subscription } from '../../types';
import './Subscription.css';

export default function Subscription() {
  const { user } = useAuth();
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [loading, setLoading] = useState(true);
  const [managing, setManaging] = useState(false);

  useEffect(() => {
    loadSubscription();
  }, []);

  const loadSubscription = async () => {
    try {
      const data = await api.getMySubscription();
      setSubscription(data);
    } catch (err) {
      console.error('Failed to load subscription:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleManageSubscription = async () => {
    if (subscription?.provider !== 'stripe') {
      toast.info('Please manage your PayPal subscription through PayPal.com');
      return;
    }

    try {
      setManaging(true);
      const { portal_url } = await api.createStripePortal();
      safeRedirect(portal_url);
    } catch (err) {
      console.error('Failed to create portal:', err);
      toast.error('Failed to open billing portal. Please try again.');
    } finally {
      setManaging(false);
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
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

  return (
    <div className="subscription-page">
      <h1>Subscription</h1>

      <div className="subscription-card">
        <div className="subscription-header">
          <div className="subscription-tier">
            <span className="tier-label">Current Plan</span>
            <span className={`tier-name ${user?.is_admin ? 'tier-admin' : `tier-${user?.subscription_tier}`}`}>
              {user?.is_admin ? 'ADMIN' : user?.subscription_tier?.toUpperCase()}
            </span>
          </div>
          {subscription && (
            <span className={`status-badge status-${subscription.status}`}>
              {subscription.status}
            </span>
          )}
        </div>

        {user?.is_admin ? (
          <p className="no-subscription">
            As an admin, you have unlimited storage and no restrictions.
          </p>
        ) : subscription ? (
          <div className="subscription-details">
            <div className="detail-item">
              <label>Provider</label>
              <span>{subscription.provider === 'stripe' ? 'Credit Card (Stripe)' : 'PayPal'}</span>
            </div>
            <div className="detail-item">
              <label>Current Period Ends</label>
              <span>{formatDate(subscription.current_period_end)}</span>
            </div>
            {subscription.canceled_at && (
              <div className="detail-item">
                <label>Canceled At</label>
                <span>{formatDate(subscription.canceled_at)}</span>
              </div>
            )}
          </div>
        ) : user?.subscription_tier === 'free' ? (
          <p className="no-subscription">
            You're on the free plan. Upgrade to unlock more features!
          </p>
        ) : (
          <p className="no-subscription">
            Your subscription is managed by an administrator.
          </p>
        )}

        <div className="subscription-actions">
          {user?.subscription_tier === 'free' ? (
            <Link to="/pricing" className="btn btn-primary">
              Upgrade Now
            </Link>
          ) : subscription ? (
            <button
              onClick={handleManageSubscription}
              className="btn btn-secondary"
              disabled={managing}
            >
              {managing ? 'Loading...' : 'Manage Subscription'}
            </button>
          ) : null}
        </div>
      </div>

      <div className="plan-comparison">
        <h2>Plan Comparison</h2>
        <table>
          <thead>
            <tr>
              <th>Feature</th>
              <th>Free</th>
              <th>Pro ($1/mo)</th>
              <th>Premium ($5/mo)</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Storage</td>
              <td>5 MB</td>
              <td>100 MB</td>
              <td>1 GB</td>
            </tr>
            <tr>
              <td>Version History</td>
              <td>3 versions</td>
              <td>10 versions</td>
              <td>Unlimited</td>
            </tr>
            <tr>
              <td>API Rate Limit</td>
              <td>100/min</td>
              <td>300/min</td>
              <td>1000/min</td>
            </tr>
            <tr>
              <td>Custom Profile URL</td>
              <td className="feature-no">✗</td>
              <td className="feature-yes">✓</td>
              <td className="feature-yes">✓</td>
            </tr>
            <tr>
              <td>Profile Banner</td>
              <td className="feature-no">✗</td>
              <td className="feature-yes">✓</td>
              <td className="feature-yes">✓</td>
            </tr>
            <tr>
              <td>Private Addons</td>
              <td className="feature-no">✗</td>
              <td className="feature-yes">✓</td>
              <td className="feature-yes">✓</td>
            </tr>
            <tr>
              <td>Usage Analytics</td>
              <td className="feature-no">✗</td>
              <td>30 days</td>
              <td>90 days</td>
            </tr>
            <tr>
              <td>Scheduled Releases</td>
              <td className="feature-no">✗</td>
              <td className="feature-yes">✓</td>
              <td className="feature-yes">✓</td>
            </tr>
            <tr>
              <td>Gradual Rollouts (A/B)</td>
              <td className="feature-no">✗</td>
              <td className="feature-no">✗</td>
              <td className="feature-yes">✓</td>
            </tr>
            <tr>
              <td>Team Organizations</td>
              <td className="feature-no">✗</td>
              <td className="feature-no">✗</td>
              <td className="feature-yes">✓</td>
            </tr>
            <tr>
              <td>API Key Access</td>
              <td className="feature-no">✗</td>
              <td className="feature-yes">✓</td>
              <td className="feature-yes">✓</td>
            </tr>
            <tr>
              <td>Webhook Notifications</td>
              <td className="feature-no">✗</td>
              <td className="feature-no">✗</td>
              <td className="feature-yes">✓</td>
            </tr>
            <tr>
              <td>Priority Support</td>
              <td className="feature-no">✗</td>
              <td className="feature-yes">✓</td>
              <td className="feature-yes">✓</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
