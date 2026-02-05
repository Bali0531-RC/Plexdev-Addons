import MarkdownRenderer from '../components/MarkdownRenderer';
import './Legal.css';

const CONTENT = `# Terms of Service

_Last updated: 2025-12-16_

These Terms of Service (\"Terms\") govern your access to and use of PlexAddons (the \"Service\"), available at https://addons.plexdev.xyz.

By accessing or using the Service, you agree to these Terms. If you do not agree, do not use the Service.

## 1. The Service

PlexAddons provides a platform for publishing, distributing, and managing addons and related metadata (including version history, changelogs, and download links).

We may modify, suspend, or discontinue all or part of the Service at any time.

## 2. Eligibility and Accounts

- You may need to sign in via Discord to use certain features.
- You are responsible for maintaining the security of your account and for all activity under your account.
- You must provide accurate information and keep it up to date.

## 3. User Content

\"User Content\" includes addon listings, descriptions, tags, changelogs, files/links you provide, and any other content you submit.

You:

- retain ownership of your User Content; and
- grant us a non-exclusive, worldwide, royalty-free license to host, store, reproduce, display, and distribute your User Content as necessary to operate and improve the Service.

You are responsible for ensuring you have the rights to submit your User Content and that it does not infringe others’ rights.

## 4. Acceptable Use

You agree not to:

- use the Service for unlawful, harmful, or abusive purposes;
- attempt to gain unauthorized access to the Service or related systems;
- upload or distribute malware, exploits, or other harmful code;
- interfere with or disrupt the Service (including rate-limit evasion);
- scrape or harvest data in a way that unreasonably burdens the Service.

We may investigate and take action (including suspension) if we believe you violated these Terms.

## 5. Addons, Downloads, and Risk

Addons may be created and published by third parties. We do not guarantee that any addon is safe, error-free, or suitable for your needs.

You are responsible for reviewing and using addons at your own risk.

## 6. Paid Plans, Billing, and Refunds

Some features may require a paid subscription.

- Payments may be processed by third-party providers (e.g., Stripe and/or PayPal).
- Pricing and plan features may change over time.
- Refund handling (if any) depends on the plan terms and applicable payment provider policies.

## 7. Intellectual Property

The Service, including its software and design is owned by Turi Balázs (\"Bali0531\") and/or its licensors and is protected by applicable laws.

## 8. Termination

We may suspend or terminate your access to the Service at any time if:

- you violate these Terms;
- your use presents risk or legal exposure to the Service; or
- we must do so to comply with law.

You may stop using the Service at any time.

## 9. Disclaimer of Warranties

THE SERVICE IS PROVIDED \"AS IS\" AND \"AS AVAILABLE\" WITHOUT WARRANTIES OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.

## 10. Limitation of Liability

TO THE MAXIMUM EXTENT PERMITTED BY LAW, PLEXADDONS AND ITS OPERATORS WILL NOT BE LIABLE FOR INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, OR ANY LOSS OF DATA, PROFITS, OR REVENUE, ARISING FROM YOUR USE OF THE SERVICE.

## 11. Changes to These Terms

We may update these Terms from time to time. Continued use of the Service after changes become effective means you accept the updated Terms.

## 12. Contact

If you have questions about these Terms, contact: **contact@plexdev.xyz**.

---

_This page is provided for general informational purposes and is not legal advice._
`;

export default function TermsOfService() {
  return (
    <div className="legal-page">
      <div className="legal-header">
        <h1>Terms of Service</h1>
        <p>Rules and conditions for using PlexAddons</p>
      </div>

      <div className="legal-card">
        <div className="legal-meta">Last updated: 2025-12-16</div>
        <MarkdownRenderer content={CONTENT} />
      </div>
    </div>
  );
}
