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

  const handleSubscribe = async (tier: 'pro' | 'premium') => {
    if (!isAuthenticated) {
      window.location.href = '/login';
      return;
    }

    try {
      const { checkout_url } = await api.createStripeCheckout(tier);
      window.location.href = checkout_url;
    } catch (err) {
      console.error('Failed to create checkout:', err);
      alert('Failed to start checkout. Please try again.');
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
                    onClick={() => handleSubscribe(plan.tier as 'pro' | 'premium')}
                    className="btn btn-primary btn-full"
                  >
                    {isAuthenticated ? 'Subscribe' : 'Sign Up & Subscribe'}
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
    </div>
  );
}
