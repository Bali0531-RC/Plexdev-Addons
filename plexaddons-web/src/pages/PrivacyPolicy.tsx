import MarkdownRenderer from '../components/MarkdownRenderer';
import './Legal.css';

const CONTENT = `# Privacy Policy

_Last updated: 2025-12-16_

This Privacy Policy explains how PlexAddons (the \"Service\"), available at https://addons.plexdev.live, collects, uses, and shares information.

If you are located in the European Economic Area (EEA), the United Kingdom, or Switzerland, this Policy is intended to help you understand our processing under the GDPR/UK GDPR.

## 0. Who We Are (Data Controller)

The data controller for personal data processed via the Service is the operator of PlexAddons.

- Contact email: **contact@plexdev.live**

## 1. Information We Collect

### Account and profile information
When you sign in with Discord, we may receive and store:

- Discord user ID
- username / display name
- avatar
- email address (if provided by Discord and you authorize it)

We may also store information you provide in your profile on the Service (such as a custom profile URL, banner settings, or other profile metadata if enabled).

### Addon and publishing data
If you publish or manage addons, we may store:

- addon names, slugs, descriptions, tags
- version information (version numbers, release notes/changelogs)
- download links or file references you provide

### Usage and technical data
We may collect technical information necessary to operate and secure the Service, such as:

- IP address (for abuse prevention and rate-limiting)
- request timestamps and basic request metadata
- device/browser information (where available)
- error logs

### Payments
If you purchase a subscription, payments are processed by third-party payment providers (such as Stripe and/or PayPal). We do not store full payment card details.

We may store subscription-related metadata (e.g., tier, renewal status, provider identifiers) so we can deliver paid features.

## 2. Legal Bases (EEA/UK)

Where GDPR/UK GDPR applies, we rely on the following legal bases depending on the context:

- **Contract**: to provide the Service you request (account, publishing, subscriptions).
- **Legitimate interests**: to secure, maintain, and improve the Service (e.g., abuse prevention, rate-limiting, debugging).
- **Consent**: if we ever introduce optional cookies or similar tracking technologies beyond what is strictly necessary.

## 3. How We Use Information

We use collected information to:

- provide and maintain the Service
- authenticate users and prevent abuse
- enable publishing and version distribution
- process and manage subscriptions
- provide customer support
- monitor performance and improve features

## 4. How We Share Information

We may share information:

- **Publicly**: Addon listings, versions, and certain profile details may be public by design.
- **With service providers**: Hosting providers, payment processors, and other vendors that help operate the Service.
- **For legal reasons**: If required to comply with law, enforce our terms, or protect safety and security.

## 5. International Data Transfers

Some of our service providers (for example Discord and payment providers) may process data outside of your country.

Where required, we use appropriate safeguards for international transfers (such as standard contractual clauses) and take steps intended to ensure an adequate level of protection.

## 6. Cookies and Local Storage

We may use cookies and/or local storage to:

- keep you signed in
- remember preferences
- protect against fraud and abuse

## 5. Data Retention

We retain information as long as needed to operate the Service, comply with legal obligations, resolve disputes, and enforce agreements.

You may request deletion of your account data where feasible, subject to legal and operational requirements.

## 7. Security

We take reasonable measures to protect information, but no method of transmission or storage is completely secure.

## 8. Your Rights

Depending on your location, you may have rights including:

- access to your personal data
- correction of inaccurate data
- deletion (\"right to be forgotten\")
- restriction of processing
- data portability
- objection to processing based on legitimate interests
- withdrawal of consent (where processing is based on consent)

You also have the right to lodge a complaint with your local data protection authority.

To make a request, contact us using the email below.

## 9. Changes to This Policy

We may update this Privacy Policy from time to time. Continued use of the Service after changes become effective means you accept the updated Policy.

## 10. Contact

For privacy questions or requests, contact: **contact@plexdev.live**.

---

_This page is provided for general informational purposes and is not legal advice._
`;

export default function PrivacyPolicy() {
  return (
    <div className="legal-page">
      <div className="legal-header">
        <h1>Privacy Policy</h1>
        <p>How PlexAddons collects and uses information</p>
      </div>

      <div className="legal-card">
        <div className="legal-meta">Last updated: 2025-12-16</div>
        <MarkdownRenderer content={CONTENT} />
      </div>
    </div>
  );
}
