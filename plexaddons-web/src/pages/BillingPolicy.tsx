import MarkdownRenderer from '../components/MarkdownRenderer';
import './Legal.css';

const CONTENT = `# Billing & Subscriptions Policy

_Last updated: 2025-12-16_

This Billing & Subscriptions Policy explains how paid plans, renewals, cancellations, and billing issues work for PlexAddons (the \"Service\"), available at https://addons.plexdev.live.

## 1. Paid Plans

Some features require a paid subscription plan. Plan features and pricing are shown on the Pricing page and may change over time.

## 2. Payment Processors

Payments are processed by third-party payment providers (such as Stripe and/or PayPal). Depending on the provider you choose, billing flows, invoices/receipts, and some account management may be handled by that provider.

We do not store full payment card details.

## 3. Renewals

Unless stated otherwise:

- subscriptions renew automatically at the end of each billing period; and
- you are responsible for keeping your payment method current.

If a payment fails, we may retry payment and/or suspend paid features until payment succeeds.

## 4. Cancellation

You can cancel your subscription through your PlexAddons dashboard (when available) and/or through the payment provider used for the subscription.

After cancellation, your subscription may remain active until the end of the current billing period. Access to paid features may change at the end of that period.

## 5. Refunds

Refunds are not guaranteed and may be granted at our discretion or as required by applicable law.

If you believe you were charged in error, contact us with:

- the email/account used
- approximate charge date
- payment provider (Stripe/PayPal)
- any receipt/invoice identifiers

## 6. Chargebacks and Disputes

If you initiate a chargeback or payment dispute, we may suspend your account or paid features while the dispute is resolved.

## 7. Changes

We may update this Policy from time to time. Continued use of the Service after changes become effective means you accept the updated Policy.

## 8. Contact

Billing questions: **contact@plexdev.live**

---

_This page is provided for general informational purposes and is not legal advice._
`;

export default function BillingPolicy() {
  return (
    <div className="legal-page">
      <div className="legal-header">
        <h1>Billing & Subscriptions</h1>
        <p>How renewals, cancellations, and billing issues work</p>
      </div>

      <div className="legal-card">
        <div className="legal-meta">Last updated: 2025-12-16</div>
        <MarkdownRenderer content={CONTENT} />
      </div>
    </div>
  );
}
