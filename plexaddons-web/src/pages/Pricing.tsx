import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import type { PaymentPlan } from '../types';
import './Pricing.css';

export default function Pricing() {
  const { isAuthenticated, user } = useAuth();
  const [plans, setPlans] = useState<PaymentPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);
  const [selectedTier, setSelectedTier] = useState<'pro' | 'premium' | null>(null);

  useEffect(() => {
    loadPlans();
  }, []);

  const loadPlans = async () => {
    try {
      const response = await api.getPlans();
      setPlans(response.plans);
    } catch (err) {
      console.error('Failed to load plans:', err);
      // Use default plans if API fails
      setPlans([
        {
          tier: 'free',
          name: 'Free',
          price_monthly: 0,
          storage_quota_bytes: 50 * 1024 * 1024,
          version_history_limit: 5,
          rate_limit: 30,
          features: ['50MB storage', '5 version history', '30 requests/min'],
        },
        {
          tier: 'pro',
          name: 'Pro',
          price_monthly: 1,
          storage_quota_bytes: 500 * 1024 * 1024,
          version_history_limit: 10,
          rate_limit: 60,
          features: ['500MB storage', '10 version history', '60 requests/min', 'Priority support'],
        },
        {
          tier: 'premium',
          name: 'Premium',
          price_monthly: 5,
          storage_quota_bytes: 5 * 1024 * 1024 * 1024,
          version_history_limit: -1,
          rate_limit: 120,
          features: ['5GB storage', 'Unlimited version history', '120 requests/min', 'Priority support', 'Early access features'],
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes >= 1024 * 1024 * 1024) {
      return `${(bytes / (1024 * 1024 * 1024)).toFixed(0)}GB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(0)}MB`;
  };

  const handleSubscribe = async (tier: 'pro' | 'premium', provider: 'stripe' | 'paypal') => {
    if (!isAuthenticated) {
      window.location.href = '/login';
      return;
    }

    setCheckoutLoading(`${tier}-${provider}`);

    try {
      if (provider === 'stripe') {
        const { checkout_url } = await api.createStripeCheckout(tier);
        window.location.href = checkout_url;
      } else {
        // PayPal - get subscription details and redirect
        const { plan_id, custom_id } = await api.getPayPalSubscriptionDetails(tier);
        // Open PayPal subscription page
        const paypalUrl = `https://www.paypal.com/webapps/billing/plans/subscribe?plan_id=${plan_id}&custom_id=${custom_id}`;
        window.location.href = paypalUrl;
      }
    } catch (err) {
      console.error('Failed to create checkout:', err);
      alert('Failed to start checkout. Please try again.');
      setCheckoutLoading(null);
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
    <div className="pricing-page">
      <div className="pricing-header">
        <h1>Choose Your Plan</h1>
        <p>Start free and upgrade as you grow</p>
      </div>

      <div className="pricing-grid">
        {plans.map((plan) => {
          const isCurrentPlan = user?.subscription_tier === plan.tier;
          const isFreePlan = plan.tier === 'free';
          
          return (
            <div 
              key={plan.tier} 
              className={`pricing-card ${plan.tier === 'pro' ? 'pricing-featured' : ''}`}
            >
              {plan.tier === 'pro' && (
                <span className="pricing-popular">Most Popular</span>
              )}
              <h2>{plan.name}</h2>
              <div className="pricing-price">
                <span className="price-amount">
                  ${plan.price_monthly}
                </span>
                <span className="price-period">/month</span>
              </div>
              <ul className="pricing-features">
                <li>
                  <span className="feature-icon">✓</span>
                  {formatBytes(plan.storage_quota_bytes)} storage
                </li>
                <li>
                  <span className="feature-icon">✓</span>
                  {plan.version_history_limit === -1 
                    ? 'Unlimited version history' 
                    : `${plan.version_history_limit} version history`}
                </li>
                <li>
                  <span className="feature-icon">✓</span>
                  {plan.rate_limit} requests/min
                </li>
                {plan.tier !== 'free' && (
                  <li>
                    <span className="feature-icon">✓</span>
                    Priority support
                  </li>
                )}
                {plan.tier === 'premium' && (
                  <li>
                    <span className="feature-icon">✓</span>
                    Early access features
                  </li>
                )}
              </ul>
              <div className="pricing-action">
                {isCurrentPlan ? (
                  <span className="current-plan">Current Plan</span>
                ) : isFreePlan ? (
                  isAuthenticated ? (
                    <Link to="/dashboard" className="btn btn-secondary btn-full">
                      Go to Dashboard
                    </Link>
                  ) : (
                    <Link to="/login" className="btn btn-secondary btn-full">
                      Get Started Free
                    </Link>
                  )
                ) : (
                  <button 
                    onClick={() => setSelectedTier(plan.tier as 'pro' | 'premium')}
                    className="btn btn-primary btn-full"
                  >
                    Subscribe
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="pricing-faq">
        <h2>Frequently Asked Questions</h2>
        <div className="faq-grid">
          <div className="faq-item">
            <h3>Can I cancel anytime?</h3>
            <p>Yes! You can cancel your subscription at any time. You'll continue to have access until the end of your billing period.</p>
          </div>
          <div className="faq-item">
            <h3>What payment methods do you accept?</h3>
            <p>We accept credit cards through Stripe and PayPal.</p>
          </div>
          <div className="faq-item">
            <h3>What happens if I exceed my storage?</h3>
            <p>You won't be able to create new versions until you free up space or upgrade your plan.</p>
          </div>
          <div className="faq-item">
            <h3>Can I downgrade my plan?</h3>
            <p>Yes, you can downgrade at any time. The change will take effect at the start of your next billing cycle.</p>
          </div>
        </div>
      </div>

      {/* Payment Method Modal */}
      {selectedTier && (
        <div className="payment-modal-overlay" onClick={() => !checkoutLoading && setSelectedTier(null)}>
          <div className="payment-modal" onClick={(e) => e.stopPropagation()}>
            <button 
              className="payment-modal-close" 
              onClick={() => !checkoutLoading && setSelectedTier(null)}
              disabled={checkoutLoading !== null}
            >
              ×
            </button>
            <h3>Choose Payment Method</h3>
            <p>Select how you'd like to pay for {selectedTier === 'pro' ? 'Pro' : 'Premium'}</p>
            <div className="payment-modal-buttons">
              <button 
                onClick={() => handleSubscribe(selectedTier, 'stripe')}
                className="btn btn-stripe btn-full"
                disabled={checkoutLoading !== null}
              >
                {checkoutLoading === `${selectedTier}-stripe` ? (
                  'Processing...'
                ) : (
                  <>
                    <svg className="payment-icon" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M4 4h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zm0 4v2h16V8H4zm0 6v2h4v-2H4zm6 0v2h2v-2h-2z"/>
                    </svg>
                    Pay with Card
                  </>
                )}
              </button>
              <button 
                onClick={() => handleSubscribe(selectedTier, 'paypal')}
                className="btn btn-paypal btn-full"
                disabled={checkoutLoading !== null}
              >
                {checkoutLoading === `${selectedTier}-paypal` ? (
                  'Processing...'
                ) : (
                  <>
                    <svg className="payment-icon paypal-logo" viewBox="0 0 24 24">
                      <path fill="#003087" d="M7.076 21.337H2.47a.641.641 0 0 1-.633-.74L4.944 3.72a.773.773 0 0 1 .763-.642h6.645c2.212 0 3.759.462 4.6 1.373.393.426.652.903.775 1.421.127.532.127 1.168 0 1.89l-.012.07v.618l.481.275c.406.224.731.487.976.79.257.318.436.689.532 1.101.1.424.119.917.056 1.467-.074.634-.227 1.19-.457 1.655-.235.475-.55.883-.936 1.215-.393.338-.862.598-1.394.775-.519.173-1.112.26-1.764.26H13.84a.94.94 0 0 0-.63.24.95.95 0 0 0-.305.594l-.04.22-.673 4.262-.03.157a.228.228 0 0 1-.062.122.172.172 0 0 1-.11.039H7.076z"/>
                      <path fill="#0070E0" d="M19.584 8.236c-.01.064-.023.13-.036.195-.523 2.682-2.312 3.607-4.6 3.607h-1.163a.564.564 0 0 0-.558.478l-.596 3.776-.169 1.07a.296.296 0 0 0 .293.344h2.059c.244 0 .451-.177.49-.418l.02-.104.389-2.467.025-.136a.5.5 0 0 1 .493-.42h.31c2.009 0 3.581-.816 4.042-3.177.192-.987.093-1.813-.417-2.392a1.995 1.995 0 0 0-.582-.356z"/>
                      <path fill="#003087" d="M18.548 7.794a4.023 4.023 0 0 0-.496-.109 6.304 6.304 0 0 0-1-.078h-3.028a.494.494 0 0 0-.49.42l-.645 4.09-.019.12a.564.564 0 0 1 .558-.478h1.163c2.288 0 4.077-.925 4.6-3.607.016-.08.029-.156.04-.228a2.674 2.674 0 0 0-.683-.13z"/>
                    </svg>
                    Pay with PayPal
                  </>
                )}
              </button>
            </div>
            <p className="payment-modal-note">Secure payment processing</p>
          </div>
        </div>
      )}
    </div>
  );
}
