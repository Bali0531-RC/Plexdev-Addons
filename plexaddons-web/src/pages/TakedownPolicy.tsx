import MarkdownRenderer from '../components/MarkdownRenderer';
import './Legal.css';

const CONTENT = `# Copyright & Takedown Policy

_Last updated: 2025-12-16_

PlexAddons (the \"Service\"), available at https://addons.plexdev.live, allows users to publish addon listings and related metadata, including external links.

We respect intellectual property rights and expect users to do the same.

## 1. What This Policy Covers

This Policy covers requests to remove or disable access to content on PlexAddons that you believe infringes your copyright or other intellectual property rights.

## 2. How to Submit a Takedown Request

Email **contact@plexdev.live** with the subject line \"Takedown Request\" and include:

- your full name and contact details
- identification of the work you believe is infringed
- the exact URL(s) on PlexAddons you want reviewed (or addon slug)
- an explanation of why you believe the content infringes your rights
- a statement that you have a good-faith belief the use is not authorized
- a statement, under penalty of perjury (where applicable), that the information in your notice is accurate and that you are the rights owner or authorized to act for them
- your physical or electronic signature (typing your name is acceptable)

## 3. What Happens Next

We may:

- remove or disable access to the content/listing; and/or
- contact the uploader/publisher for more information.

We may also request additional details before acting.

## 4. Counter-Notice

If your content was removed and you believe it was removed in error, contact **contact@plexdev.live** with the subject line \"Counter Notice\" and include:

- the URL(s) involved
- why you believe the content was removed in error
- any supporting documentation

We will review and respond as appropriate.

## 5. Repeat Infringers

We may suspend or terminate accounts that repeatedly infringe intellectual property rights.

---

_This page is provided for general informational purposes and is not legal advice._
`;

export default function TakedownPolicy() {
  return (
    <div className="legal-page">
      <div className="legal-header">
        <h1>Copyright & Takedown</h1>
        <p>How to report suspected IP infringement</p>
      </div>

      <div className="legal-card">
        <div className="legal-meta">Last updated: 2025-12-16</div>
        <MarkdownRenderer content={CONTENT} />
      </div>
    </div>
  );
}
