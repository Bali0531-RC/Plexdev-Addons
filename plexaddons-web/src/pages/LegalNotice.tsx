import MarkdownRenderer from '../components/MarkdownRenderer';
import './Legal.css';

const CONTENT = `# Legal Notice (Impressum)

_Last updated: 2025-12-16_

This page provides operator information for PlexAddons (https://addons.plexdev.xyz).

## Operator

- Country: **Hungary**
- Name / entity: **Turi Balázs ("Bali0531")**
- Address: Not publicly listed.
- Email: **contact@plexdev.xyz**

## Legal correspondence

If you need to send formal legal correspondence, contact us at **contact@plexdev.xyz** and we will provide an address or alternative delivery method where appropriate.

---

_This page is provided for general informational purposes and is not legal advice._
`;

export default function LegalNotice() {
  return (
    <div className="legal-page">
      <div className="legal-header">
        <h1>Legal Notice</h1>
        <p>Operator information for PlexAddons</p>
      </div>

      <div className="legal-card">
        <div className="legal-meta">Last updated: 2025-12-16</div>
        <MarkdownRenderer content={CONTENT} />
      </div>
    </div>
  );
}
