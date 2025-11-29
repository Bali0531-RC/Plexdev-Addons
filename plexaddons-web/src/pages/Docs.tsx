import './Docs.css';

export default function Docs() {
  return (
    <div className="docs-page">
      <div className="docs-header">
        <h1>Developer Documentation</h1>
        <p>Learn how to integrate PlexDev Addons version checking into your projects</p>
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
              <li><a href="#events">Events</a></li>
            </ul>
            <h3>Publishing</h3>
            <ul>
              <li><a href="#creating-addon">Creating an Addon</a></li>
              <li><a href="#releasing-versions">Releasing Versions</a></li>
              <li><a href="#best-practices">Best Practices</a></li>
            </ul>
          </nav>
        </aside>

        <main className="docs-main">
          <section id="introduction">
            <h2>Introduction</h2>
            <p>
              PlexDev Addons provides a centralized platform for distributing and updating 
              addons for PlexDevelopment products. Use our VersionChecker library to easily 
              integrate update notifications into your projects.
            </p>
          </section>

          <section id="installation">
            <h2>Installation</h2>
            <p>Copy the VersionChecker.js file to your project:</p>
            <pre><code>{`// Download from GitHub
const VersionChecker = require('./version-checker/VersionChecker');

// Or import as ES module
import VersionChecker from './version-checker/VersionChecker.mjs';`}</code></pre>
          </section>

          <section id="quick-start">
            <h2>Quick Start</h2>
            <p>Basic usage example:</p>
            <pre><code>{`const VersionChecker = require('./version-checker/VersionChecker');

const checker = new VersionChecker({
  // Use the addons.plexdev.live API
  versionsUrl: 'https://addons.plexdev.live/api/v1/public/addons/{slug}/versions',
  currentVersion: '1.0.0',
  addonSlug: 'my-addon',
  checkInterval: 3600000, // 1 hour
});

// Listen for updates
checker.on('updateAvailable', (info) => {
  console.log(\`Update available: v\${info.latestVersion}\`);
  console.log(\`Changelog: \${info.changelog}\`);
});

// Start checking
checker.startAutoCheck();`}</code></pre>
          </section>

          <section id="version-checker">
            <h2>VersionChecker Class</h2>
            <p>The main class for checking addon versions.</p>
            
            <h3>Constructor Options</h3>
            <div className="docs-table">
              <table>
                <thead>
                  <tr>
                    <th>Option</th>
                    <th>Type</th>
                    <th>Description</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td><code>versionsUrl</code></td>
                    <td>string</td>
                    <td>URL to fetch version info from. Use <code>{'{slug}'}</code> as placeholder.</td>
                  </tr>
                  <tr>
                    <td><code>currentVersion</code></td>
                    <td>string</td>
                    <td>Current version of your addon (semver format)</td>
                  </tr>
                  <tr>
                    <td><code>addonSlug</code></td>
                    <td>string</td>
                    <td>Your addon's unique slug on PlexDev Addons</td>
                  </tr>
                  <tr>
                    <td><code>checkInterval</code></td>
                    <td>number</td>
                    <td>Interval between checks in milliseconds (default: 1 hour)</td>
                  </tr>
                  <tr>
                    <td><code>autoCheck</code></td>
                    <td>boolean</td>
                    <td>Start checking automatically (default: false)</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section id="methods">
            <h2>Methods</h2>
            
            <h3><code>checkForUpdates()</code></h3>
            <p>Manually check for updates. Returns a Promise with update info.</p>
            <pre><code>{`const info = await checker.checkForUpdates();
if (info.updateAvailable) {
  console.log('New version:', info.latestVersion);
}`}</code></pre>

            <h3><code>startAutoCheck()</code></h3>
            <p>Start automatic periodic checking.</p>

            <h3><code>stopAutoCheck()</code></h3>
            <p>Stop automatic checking.</p>

            <h3><code>setCurrentVersion(version)</code></h3>
            <p>Update the current version (useful after applying an update).</p>
          </section>

          <section id="events">
            <h2>Events</h2>
            <p>VersionChecker emits events you can listen to:</p>
            
            <div className="docs-table">
              <table>
                <thead>
                  <tr>
                    <th>Event</th>
                    <th>Data</th>
                    <th>Description</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td><code>updateAvailable</code></td>
                    <td><code>{`{ latestVersion, changelog, downloadUrl }`}</code></td>
                    <td>Fired when a newer version is available</td>
                  </tr>
                  <tr>
                    <td><code>upToDate</code></td>
                    <td><code>{`{ currentVersion }`}</code></td>
                    <td>Fired when already on latest version</td>
                  </tr>
                  <tr>
                    <td><code>error</code></td>
                    <td><code>{`{ error }`}</code></td>
                    <td>Fired when version check fails</td>
                  </tr>
                  <tr>
                    <td><code>checking</code></td>
                    <td>-</td>
                    <td>Fired when starting a version check</td>
                  </tr>
                </tbody>
              </table>
            </div>
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
                  <li><strong>Slug:</strong> Unique URL-friendly identifier</li>
                  <li><strong>Description:</strong> What your addon does</li>
                  <li><strong>Repository:</strong> GitHub or other repo URL (optional)</li>
                </ul>
              </li>
            </ol>
          </section>

          <section id="releasing-versions">
            <h2>Releasing Versions</h2>
            <ol>
              <li>Navigate to your addon in the dashboard</li>
              <li>Click "New Version"</li>
              <li>Enter version number (semver format: 1.0.0)</li>
              <li>Add changelog notes (supports Markdown)</li>
              <li>Optionally add a download URL</li>
              <li>Publish the version</li>
            </ol>
            <p>
              Once published, users running VersionChecker will automatically be notified
              of the new version.
            </p>
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
                <strong>Set reasonable check intervals:</strong> Don't check too frequently (1 hour minimum recommended)
              </li>
              <li>
                <strong>Handle errors gracefully:</strong> Version check failures shouldn't break your addon
              </li>
              <li>
                <strong>Notify users non-intrusively:</strong> Log to console or show a subtle notification
              </li>
            </ul>
          </section>

          <section id="api-endpoints">
            <h2>Public API Endpoints</h2>
            <p>These endpoints are available without authentication:</p>
            
            <h3>Get Addon Versions</h3>
            <pre><code>{`GET https://addons.plexdev.live/api/v1/public/addons/{slug}/versions

Response:
{
  "addon": {
    "name": "My Addon",
    "slug": "my-addon",
    "description": "..."
  },
  "versions": [
    {
      "version": "1.2.0",
      "changelog": "Added new features...",
      "download_url": "https://...",
      "published_at": "2025-01-15T..."
    }
  ],
  "latest": "1.2.0"
}`}</code></pre>

            <h3>List All Addons</h3>
            <pre><code>{`GET https://addons.plexdev.live/api/v1/public/addons

Response:
{
  "addons": [...],
  "total": 42,
  "page": 1,
  "per_page": 20
}`}</code></pre>
          </section>
        </main>
      </div>
    </div>
  );
}
