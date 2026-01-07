# PlexAddons Version Checker

A version checker library for addons registered on [addons.plexdev.live](https://addons.plexdev.live).

## Installation

Copy `VersionChecker.js` directly into your project.

## Quick Start

```javascript
const VersionChecker = require('./VersionChecker.js');

// Basic usage - automatically tracks analytics
const checker = new VersionChecker('MyAddon', '1.0.0');

// Check for updates
const result = await checker.checkForUpdates();
console.log(checker.formatVersionMessage(result));

// Or use the convenience method that logs automatically
await checker.checkAndLog();
```

## Features

- 🔄 Automatic update checking with formatted console output
- 📊 Analytics tracking (helps addon owners see version distribution)
- 🔑 API key support for addon owners (Premium feature)
- 📝 TypeScript support with included type definitions
- 🌐 Works with both API and legacy versions.json endpoints
- ⚡ Lightweight with automatic retries and timeout handling
- 🎯 Semantic version comparison

## Basic Usage

```javascript
const VersionChecker = require('./VersionChecker.js');

const checker = new VersionChecker('MyAddon', '1.0.0');

// Check for updates
const result = await checker.checkForUpdates();

if (result.isOutdated) {
  console.log(`Update available: v${result.current} → v${result.latest}`);
  console.log(checker.getUpdateDetails(result));
}
```

## Constructor Options

```javascript
const checker = new VersionChecker('AddonName', '1.0.0', {
  // Base URL for the PlexAddons API
  apiUrl: 'https://addons.plexdev.live',
  
  // Legacy versions.json URL (fallback)
  repositoryUrl: 'https://addons.plexdev.live/versions.json',
  
  // Request timeout in milliseconds
  timeout: 10000,
  
  // Number of retry attempts
  retries: 2,
  
  // Force use of legacy versions.json API
  useLegacyApi: false,
  
  // Send current version to API for analytics (default: true)
  // This helps addon owners see which versions users are running
  trackAnalytics: true
});
```

## Methods

### Version Checking

#### `checkForUpdates(): Promise<VersionCheckResult>`
Check for updates and return detailed result.

```javascript
const result = await checker.checkForUpdates();
// result.isOutdated, result.latest, result.urgent, etc.
```

#### `checkAndLog(): Promise<VersionCheckResult>`
Check for updates and log formatted message to console.

```javascript
await checker.checkAndLog();
// Outputs: [OK] Version Check: Up to date (v1.0.0)
// Or: [UPDATE] Version Check: Outdated (v1.0.0 → v1.1.0)
```

#### `formatVersionMessage(result): string`
Get formatted console message with ANSI colors.

#### `getUpdateDetails(result): string`
Get detailed update information box.

#### `getPlainSummary(result): string`
Get plain text summary without colors.

## VersionCheckResult

```typescript
interface VersionCheckResult {
  success: boolean;        // Whether the check succeeded
  error?: string;          // Error message if failed
  isOutdated: boolean;     // Current version < latest
  isCurrent: boolean;      // Current version = latest
  isNewer: boolean;        // Current version > latest (dev build)
  current: string;         // Current version
  latest: string;          // Latest version
  releaseDate?: string;    // Release date of latest version
  downloadUrl?: string;    // Download URL if available
  description?: string;    // Version description
  changelog?: string;      // Changelog content
  changelogUrl?: string;   // URL to full changelog
  urgent: boolean;         // Urgent update flag
  breaking: boolean;       // Breaking changes flag
  external: boolean;       // External addon flag
  author?: string;         // Addon author
  homepage?: string;       // Addon homepage
}
```

## Discord Bot Integration

```javascript
const { Client } = require('discord.js');
const VersionChecker = require('./VersionChecker.js');

const client = new Client({ intents: [...] });
const checker = new VersionChecker(
  'my-discord-bot',
  require('./package.json').version
);

client.once('ready', async () => {
  console.log(`Logged in as ${client.user.tag}`);
  
  // Check on startup
  const result = await checker.checkAndLog();
  
  // Notify admin of urgent updates
  if (result.isOutdated && result.urgent) {
    console.warn('⚠️ URGENT UPDATE AVAILABLE!');
  }
});

client.login(process.env.DISCORD_TOKEN);
```

## Analytics Tracking

By default, the version checker sends your current version to the API when checking for updates. This allows addon owners (with Pro/Premium) to see:

- Which versions of their addon are being used
- Total unique users
- Version distribution

To disable analytics tracking:

```javascript
const checker = new VersionChecker('MyAddon', '1.0.0', {
  trackAnalytics: false
});
```

## Publishing Your Addon

1. Create an account at [addons.plexdev.live](https://addons.plexdev.live) using Discord OAuth
2. Register your addon in the dashboard
3. Add versions with changelogs
4. Integrate this version checker in your addon
5. Upgrade to Pro/Premium to access analytics!

## License

AGPL-3.0 - See [LICENSE](LICENSE) for details.

## Links

- 🌐 **Website**: [addons.plexdev.live](https://addons.plexdev.live)
- 📚 **API Docs**: [addons.plexdev.live/api/docs](https://addons.plexdev.live/api/docs)
- 🐛 **Issues**: [GitHub Issues](https://github.com/Bali0531-RC/PlexAddons/issues)
