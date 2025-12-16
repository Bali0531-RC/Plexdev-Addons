import MarkdownRenderer from '../components/MarkdownRenderer';
import './Legal.css';

const CONTENT = `# Acceptable Use Policy

_Last updated: 2025-12-16_

This Acceptable Use Policy (\"AUP\") describes what is and is not allowed on PlexAddons (the \"Service\"), available at https://addons.plexdev.live.

This AUP applies to all users and all content you submit (including addon listings, descriptions, tags, changelogs, and external download links).

## 1. You Must Not

You must not use the Service to:

- upload, link to, or distribute malware, spyware, phishing content, or other harmful code;
- publish or link to content that infringes intellectual property rights;
- publish or link to pirated software or keys/cracks;
- abuse, harass, threaten, or discriminate against others;
- attempt unauthorized access to systems or accounts;
- interfere with or disrupt the Service (including bypassing rate limits);
- scrape the Service in a way that imposes an unreasonable load;
- use the Service for unlawful activities.

## 2. External Links

Addons may include external links (for example to downloads, documentation, or repositories). You are responsible for ensuring links you publish are safe, lawful, and kept reasonably up to date.

We may remove or disable links or listings that we believe create risk, violate policies, or violate law.

## 3. Enforcement

We may take action if we believe you violated this AUP, including:

- removing or hiding content;
- temporarily limiting features;
- suspending or terminating accounts; and/or
- reporting activity where required by law.

We may enforce this AUP at our discretion, including to protect users and the Service.

## 4. Reporting Abuse

To report abuse or suspicious content, email **contact@plexdev.live** and include:

- the listing URL (or addon slug)
- what you observed
- any supporting details (screenshots, logs, etc.)

---

_This page is provided for general informational purposes and is not legal advice._
`;

export default function AcceptableUsePolicy() {
  return (
    <div className="legal-page">
      <div className="legal-header">
        <h1>Acceptable Use</h1>
        <p>Rules to keep PlexAddons safe for everyone</p>
      </div>

      <div className="legal-card">
        <div className="legal-meta">Last updated: 2025-12-16</div>
        <MarkdownRenderer content={CONTENT} />
      </div>
    </div>
  );
}
