import './Docs.css';

export default function Docs() {
  return (
    <div className="docs-page">
      <div className="docs-header">
        <h1>Developer Documentation</h1>
        <p>Learn how to integrate PlexDev Addons version checking into your projects using <code>pavc</code></p>
      </div>

      <div className="docs-content">
        <aside className="docs-sidebar">
          <nav>
            <h3>Getting Started</h3>
            <ul>
              <li><a href="#introduction">Introduction</a></li>
              <li><a href="#installation">Installation</a></li>
              <li><a href="#quick-start">Quick Start</a></li>
            </ul>
            <h3>API Reference</h3>
            <ul>
              <li><a href="#version-checker">VersionChecker</a></li>
              <li><a href="#methods">Methods</a></li>
              <li><a href="#output-formatting">Output Formatting</a></li>
            </ul>
            <h3>Publishing</h3>
            <ul>
              <li><a href="#creating-addon">Creating an Addon</a></li>
              <li><a href="#releasing-versions">Releasing Versions</a></li>
              <li><a href="#analytics">Analytics</a></li>
              <li><a href="#best-practices">Best Practices</a></li>
            </ul>
            <h3>CI/CD Automation</h3>
            <ul>
              <li><a href="#automation-api">Automation API</a></li>
              <li><a href="#github-actions">GitHub Actions</a></li>
            </ul>
            <h3>API Endpoints</h3>
            <ul>
              <li><a href="#api-endpoints">Public API</a></li>
            </ul>
          </nav>
        </aside>

        <main className="docs-main">
          <section id="introduction">
            <h2>Introduction</h2>
            <p>
              PlexDev Addons provides a centralized platform for distributing and updating 
              addons for PlexDevelopment products. Use our official <code>pavc</code> (PlexAddons Version Checker) 
              npm package to easily integrate update notifications into your projects.
            </p>
            <div className="docs-info-box">
              <strong>📦 pavc</strong> - The official version checker for PlexAddons
              <br />
              <a href="https://www.npmjs.com/package/pavc" target="_blank" rel="noopener noreferrer">
                View on npm →
              </a>
            </div>
          </section>

          <section id="installation">
            <h2>Installation</h2>
            <p>Install the <code>pavc</code> package from npm:</p>
            <pre><code>{`npm install pavc`}</code></pre>
            <p>Or using yarn:</p>
            <pre><code>{`yarn add pavc`}</code></pre>
            <p>Or using pnpm:</p>
            <pre><code>{`pnpm add pavc`}</code></pre>
          </section>

          <section id="quick-start">
            <h2>Quick Start</h2>
            <p>Basic usage example:</p>
            <pre><code>{`const VersionChecker = require('pavc');

// Initialize with your addon name (or slug) and current version
const checker = new VersionChecker('MyAddon', '1.0.0');

// Check for updates
const result = await checker.checkForUpdates();

// Log formatted message to console
console.log(checker.formatVersionMessage(result));

// Or use the convenience method
await checker.checkAndLog();`}</code></pre>

            <h3>Using Slug Instead of Name</h3>
            <p>You can use either your addon's name or its URL-friendly slug:</p>
            <pre><code>{`// Using addon name (display name)
const checker = new VersionChecker('My Cool Addon', '1.0.0');

// Using slug (URL-friendly)
const checker = new VersionChecker('my-cool-addon', '1.0.0');

// Both will work - the API supports both!`}</code></pre>

            <h3>Discord Bot Integration</h3>
            <pre><code>{`const VersionChecker = require('pavc');
const Discord = require('discord.js');

const client = new Discord.Client({ intents: [...] });
const checker = new VersionChecker('MyBot', '2.0.0');

client.once('ready', async () => {
    console.log(\`Logged in as \${client.user.tag}\`);
    
    // Check for updates on startup
    const result = await checker.checkForUpdates();
    console.log(checker.formatVersionMessage(result));
    
    if (result.isOutdated) {
        console.log(checker.getUpdateDetails(result));
    }
});

client.login(process.env.DISCORD_TOKEN);`}</code></pre>
          </section>

          <section id="version-checker">
            <h2>VersionChecker Class</h2>
            <p>The main class for checking addon versions.</p>
            
            <h3>Constructor</h3>
            <pre><code>{`new VersionChecker(addonName, currentVersion, options)`}</code></pre>
            
            <h3>Parameters</h3>
            <div className="docs-table">
              <table>
                <thead>
                  <tr>
                    <th>Parameter</th>
                    <th>Type</th>
                    <th>Description</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td><code>addonName</code></td>
                    <td>string</td>
                    <td>Your addon's name or slug (must match what's registered)</td>
                  </tr>
                  <tr>
                    <td><code>currentVersion</code></td>
                    <td>string</td>
                    <td>Your addon's current version (e.g., "1.0.0")</td>
                  </tr>
                  <tr>
                    <td><code>options</code></td>
                    <td>object</td>
                    <td>Optional configuration (see below)</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <h3>Options</h3>
            <div className="docs-table">
              <table>
                <thead>
                  <tr>
                    <th>Option</th>
                    <th>Type</th>
                    <th>Default</th>
                    <th>Description</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td><code>apiUrl</code></td>
                    <td>string</td>
                    <td>https://addons.plexdev.live</td>
                    <td>Base API URL</td>
                  </tr>
                  <tr>
                    <td><code>timeout</code></td>
                    <td>number</td>
                    <td>10000</td>
                    <td>Request timeout in milliseconds</td>
                  </tr>
                  <tr>
                    <td><code>retries</code></td>
                    <td>number</td>
                    <td>2</td>
                    <td>Number of retry attempts on failure</td>
                  </tr>
                  <tr>
                    <td><code>trackAnalytics</code></td>
                    <td>boolean</td>
                    <td>true</td>
                    <td>Send current version for analytics tracking</td>
                  </tr>
                  <tr>
                    <td><code>useLegacyApi</code></td>
                    <td>boolean</td>
                    <td>false</td>
                    <td>Force use of legacy versions.json endpoint</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section id="methods">
            <h2>Methods</h2>
            
            <h3><code>checkForUpdates()</code></h3>
            <p>Check for updates and return detailed information.</p>
            <pre><code>{`const result = await checker.checkForUpdates();

// Result object:
{
  success: true,
  isOutdated: true,      // true if update available
  isCurrent: false,       // true if on latest version
  isNewer: false,         // true if running dev/pre-release
  current: "1.0.0",       // your version
  latest: "1.2.0",        // latest available version
  releaseDate: "2025-01-15",
  downloadUrl: "https://...",
  description: "What's new...",
  changelog: "- Added feature X\\n- Fixed bug Y",
  urgent: false,          // true if urgent update
  breaking: false,        // true if breaking changes
  author: "bali0531",
  homepage: "https://..."
}`}</code></pre>

            <h3><code>checkAndLog()</code></h3>
            <p>Convenience method to check and log results to console with formatting.</p>
            <pre><code>{`// Automatically logs formatted output
await checker.checkAndLog();

// Output examples:
// ✓ [OK] Version Check: Up to date (v1.0.0)
// ⚠ [UPDATE] Version Check: Outdated (v1.0.0 → v1.2.0)`}</code></pre>

            <h3><code>formatVersionMessage(result)</code></h3>
            <p>Generate a colored console message for the version status.</p>
            <pre><code>{`const result = await checker.checkForUpdates();
console.log(checker.formatVersionMessage(result));`}</code></pre>

            <h3><code>getUpdateDetails(result)</code></h3>
            <p>Get detailed update information formatted as a box.</p>
            <pre><code>{`const result = await checker.checkForUpdates();
if (result.isOutdated) {
    console.log(checker.getUpdateDetails(result));
}`}</code></pre>

            <h3><code>getPlainSummary(result)</code></h3>
            <p>Get a plain text summary without ANSI colors (useful for logs/files).</p>
            <pre><code>{`const result = await checker.checkForUpdates();
const summary = checker.getPlainSummary(result);
// "Update Available: v1.0.0 → v1.2.0 [URGENT]"`}</code></pre>

            <h3><code>getAllVersions(limit)</code></h3>
            <p>Get all available versions (returns latest version for public API).</p>
            <pre><code>{`const versions = await checker.getAllVersions(10);
console.log(versions.versions);`}</code></pre>
          </section>

          <section id="output-formatting">
            <h2>Output Formatting</h2>
            <p>The version checker provides colored console output:</p>
            
            <div className="docs-code-block">
              <div className="console-output">
                <span className="console-green">[OK]</span> Version Check: <span className="console-green">Up to date</span> (v1.0.0)
              </div>
              <div className="console-output">
                <span className="console-red">[UPDATE]</span> Version Check: <span className="console-red">Outdated</span> (v1.0.0 → v1.2.0)
              </div>
              <div className="console-output">
                <span className="console-cyan">[DEV]</span> Version Check: <span className="console-cyan">Development version</span> (v1.3.0 &gt; v1.2.0)
              </div>
              <div className="console-output">
                <span className="console-yellow">[WARN]</span> Version Check: <span className="console-yellow">Failed (timeout)</span>
              </div>
            </div>

            <p>Update details include changelog, author, and download links:</p>
            <pre><code>{`📦 Update Available for MyAddon
   Current: v1.0.0
   Latest:  v1.2.0 (Jan 15, 2025)
   Author:  bali0531
   Changes: Added new feature, fixed bugs
   Download: https://...`}</code></pre>
          </section>

          <section id="creating-addon">
            <h2>Creating an Addon</h2>
            <ol>
              <li>Sign in with Discord at <a href="/login">addons.plexdev.live</a></li>
              <li>Go to your <a href="/dashboard/addons">Dashboard → My Addons</a></li>
              <li>Click "Create Addon"</li>
              <li>Fill in the addon details:
                <ul>
                  <li><strong>Name:</strong> Display name for your addon</li>
                  <li><strong>Description:</strong> What your addon does</li>
                  <li><strong>Homepage:</strong> GitHub or website URL (optional)</li>
                  <li><strong>Tags:</strong> Categories to help users find your addon</li>
                </ul>
              </li>
              <li>The <strong>slug</strong> is auto-generated from your addon name (e.g., "My Addon" → "my-addon")</li>
            </ol>
            <div className="docs-info-box">
              <strong>💡 Tip:</strong> You can use either the addon name or slug when initializing VersionChecker. The API supports both!
            </div>
          </section>

          <section id="releasing-versions">
            <h2>Releasing Versions</h2>
            <ol>
              <li>Navigate to your addon in the dashboard</li>
              <li>Click "New Version"</li>
              <li>Enter version number (semver format: 1.0.0)</li>
              <li>Add changelog notes (supports Markdown)</li>
              <li>Optionally add a download URL</li>
              <li>Mark as <strong>urgent</strong> for critical updates</li>
              <li>Mark as <strong>breaking</strong> if incompatible changes</li>
              <li>Publish the version</li>
            </ol>
            <p>
              Once published, users running <code>pavc</code> will automatically be notified
              of the new version.
            </p>
          </section>

          <section id="analytics">
            <h2>Analytics</h2>
            <p>
              When <code>trackAnalytics</code> is enabled (default), the version checker sends your addon's 
              current version to our API. This allows you to:
            </p>
            <ul>
              <li>See how many users are running your addon</li>
              <li>Track version distribution (who's on which version)</li>
              <li>Monitor update adoption rates</li>
              <li>View daily/weekly/monthly usage trends</li>
            </ul>
            <p>
              View your analytics in the <a href="/dashboard/analytics">Dashboard → Analytics</a> (requires Pro or Premium).
            </p>
            <div className="docs-info-box">
              <strong>🔒 Privacy:</strong> Only version information and a hashed IP are collected. 
              No personal data is stored.
            </div>
          </section>

          <section id="best-practices">
            <h2>Best Practices</h2>
            <ul>
              <li>
                <strong>Use semantic versioning:</strong> Follow <code>MAJOR.MINOR.PATCH</code> format
              </li>
              <li>
                <strong>Write clear changelogs:</strong> Help users understand what changed
              </li>
              <li>
                <strong>Check on startup:</strong> Check once when your addon starts, not continuously
              </li>
              <li>
                <strong>Handle errors gracefully:</strong> Version check failures shouldn't break your addon
                <pre><code>{`const result = await checker.checkForUpdates();
if (!result.success) {
    console.log('Version check unavailable, continuing...');
}
// Your addon continues normally`}</code></pre>
              </li>
              <li>
                <strong>Use urgent/breaking flags:</strong> Alert users to critical updates
              </li>
              <li>
                <strong>Notify users non-intrusively:</strong> Log to console or show a subtle notification
              </li>
            </ul>
          </section>

          <section id="api-endpoints">
            <h2>Public API Endpoints</h2>
            <p>These endpoints are available without authentication:</p>
            
            <h3>Get Latest Version for Addon (by name or slug)</h3>
            <pre><code>{`GET https://addons.plexdev.live/api/addons/{name-or-slug}/latest

# Examples:
GET /api/addons/MyAddon/latest      # by name
GET /api/addons/my-addon/latest     # by slug

# Optional header for analytics:
X-Current-Version: 1.0.0

Response:
{
  "name": "MyAddon",
  "slug": "my-addon",
  "version": "1.2.0",
  "release_date": "2025-01-15",
  "download_url": "https://...",
  "description": "Added new features...",
  "changelog": "- Feature A\\n- Bug fix B",
  "author": "bali0531",
  "urgent": false,
  "breaking": false,
  "external": false
}`}</code></pre>

            <h3>Get All Addon Versions (Legacy)</h3>
            <pre><code>{`GET https://addons.plexdev.live/versions.json

Response:
{
  "addons": {
    "MyAddon": {
      "version": "1.2.0",
      "releaseDate": "2025-01-15",
      "downloadUrl": "https://...",
      "description": "Added new features...",
      "changelog": "..."
    }
  },
  "lastUpdated": "2025-01-15T12:00:00Z",
  "repository": "https://github.com/..."
}`}</code></pre>

            <h3>List All Public Addons</h3>
            <pre><code>{`GET https://addons.plexdev.live/api/addons

Response:
{
  "addons": [...],
  "count": 42
}`}</code></pre>
          </section>

          <section id="automation-api">
            <h2>CI/CD Automation API</h2>
            <p>
              Pro and Premium users can automate version management using the Automation API.
              Create API keys with specific permissions to safely automate your workflows.
            </p>
            <div className="docs-info-box">
              <strong>🔑 API Keys:</strong> Available for Pro (read-only) and Premium (full access) subscribers.
              <br />
              <a href="/dashboard/settings">Manage your API keys →</a>
            </div>

            <h3>API Key Permissions (Scopes)</h3>
            <table className="docs-table">
              <thead>
                <tr>
                  <th>Scope</th>
                  <th>Description</th>
                  <th>Tier</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><code>addons:read</code></td>
                  <td>View addon information</td>
                  <td>Pro+</td>
                </tr>
                <tr>
                  <td><code>versions:read</code></td>
                  <td>View version details</td>
                  <td>Pro+</td>
                </tr>
                <tr>
                  <td><code>analytics:read</code></td>
                  <td>Access download analytics</td>
                  <td>Pro+</td>
                </tr>
                <tr>
                  <td><code>versions:write</code></td>
                  <td>Publish new versions</td>
                  <td>Premium</td>
                </tr>
                <tr>
                  <td><code>addons:write</code></td>
                  <td>Create/update addons</td>
                  <td>Premium</td>
                </tr>
                <tr>
                  <td><code>webhooks:manage</code></td>
                  <td>Manage webhooks</td>
                  <td>Premium</td>
                </tr>
                <tr>
                  <td><code>full:access</code></td>
                  <td>All permissions</td>
                  <td>Premium</td>
                </tr>
              </tbody>
            </table>

            <h3>Authentication</h3>
            <p>All automation endpoints require an API key passed in the <code>X-API-Key</code> header:</p>
            <pre><code>{`curl -H "X-API-Key: pa_your_api_key_here" \\
  https://addons.plexdev.live/api/v1/automation/addons`}</code></pre>

            <h3>Publish a New Version</h3>
            <p><strong>Required scope:</strong> <code>versions:write</code> (Premium)</p>
            <pre><code>{`POST /api/v1/automation/addons/{slug}/publish

Headers:
  X-API-Key: pa_your_api_key
  Content-Type: application/json

Body:
{
  "version": "1.2.0",
  "download_url": "https://github.com/.../releases/download/v1.2.0/addon.zip",
  "description": "New features and bug fixes",
  "changelog": "- Added feature X\\n- Fixed bug Y",
  "breaking": false,
  "urgent": false
}

Response:
{
  "success": true,
  "message": "Version 1.2.0 published successfully",
  "addon_slug": "my-addon",
  "addon_name": "My Addon",
  "version": { ... }
}`}</code></pre>

            <h3>Get Latest Version</h3>
            <p><strong>Required scope:</strong> <code>versions:read</code> (Pro+)</p>
            <pre><code>{`GET /api/v1/automation/addons/{slug}/latest

Headers:
  X-API-Key: pa_your_api_key

Response:
{
  "addon_slug": "my-addon",
  "addon_name": "My Addon",
  "latest_version": "1.2.0",
  "release_date": "2025-01-15",
  "download_url": "https://..."
}`}</code></pre>

            <h3>List Your Addons</h3>
            <p><strong>Required scope:</strong> <code>addons:read</code> (Pro+)</p>
            <pre><code>{`GET /api/v1/automation/addons

Headers:
  X-API-Key: pa_your_api_key

Response:
{
  "addons": [
    { "id": 1, "name": "My Addon", "slug": "my-addon", "is_public": true }
  ],
  "count": 1
}`}</code></pre>
          </section>

          <section id="github-actions">
            <h2>GitHub Actions Integration</h2>
            <p>
              Automatically publish new versions to PlexAddons whenever you create a GitHub release.
              Add this workflow to your repository:
            </p>

            <h3>Setup</h3>
            <ol>
              <li>Go to your repository → Settings → Secrets and variables → Actions</li>
              <li>Add a new secret named <code>PLEXADDONS_API_KEY</code> with your API key</li>
              <li>Create <code>.github/workflows/plexaddons-publish.yml</code> with the content below</li>
            </ol>

            <h3>Workflow File</h3>
            <pre><code>{`# .github/workflows/plexaddons-publish.yml
name: Publish to PlexAddons

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - name: Publish to PlexAddons
        run: |
          # Extract version from tag (removes 'v' prefix if present)
          VERSION=\${{ github.event.release.tag_name }}
          VERSION=\${VERSION#v}
          
          curl -X POST "https://addons.plexdev.live/api/v1/automation/addons/\${{ github.event.repository.name }}/publish" \\
            -H "X-API-Key: \${{ secrets.PLEXADDONS_API_KEY }}" \\
            -H "Content-Type: application/json" \\
            -d "{
              \\"version\\": \\"\${VERSION}\\",
              \\"download_url\\": \\"\${{ github.event.release.zipball_url }}\\",
              \\"description\\": \\"\${{ github.event.release.name }}\\",
              \\"changelog\\": $(echo '\${{ github.event.release.body }}' | jq -Rs .)
            }"
`}</code></pre>

            <h3>Alternative: Simple Workflow</h3>
            <p>If you prefer a simpler approach without changelog:</p>
            <pre><code>{`# .github/workflows/plexaddons-publish.yml
name: Publish to PlexAddons

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - name: Publish to PlexAddons
        env:
          PLEXADDONS_API_KEY: \${{ secrets.PLEXADDONS_API_KEY }}
        run: |
          VERSION="\${{ github.event.release.tag_name }}"
          VERSION="\${VERSION#v}"
          
          curl -X POST "https://addons.plexdev.live/api/v1/automation/addons/YOUR-ADDON-SLUG/publish" \\
            -H "X-API-Key: \$PLEXADDONS_API_KEY" \\
            -H "Content-Type: application/json" \\
            -d '{
              "version": "'\$VERSION'",
              "download_url": "\${{ github.event.release.zipball_url }}",
              "description": "\${{ github.event.release.name }}"
            }'
`}</code></pre>

            <div className="docs-info-box">
              <strong>💡 Tip:</strong> Make sure your addon slug matches your GitHub repository name, 
              or replace <code>YOUR-ADDON-SLUG</code> with your actual addon slug.
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}
