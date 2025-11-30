# PlexAddons Version Checker

A version checker library for addons registered on [addons.plexdev.live](https://addons.plexdev.live).

## Installation

```bash
npm install plexaddons-version-checker
```

Or copy `VersionChecker.js` directly into your project.

## Quick Start

```javascript
const VersionChecker = require('plexaddons-version-checker');

const checker = new VersionChecker({
  addonName: 'your-addon-slug',    // Your addon's slug on addons.plexdev.live
  currentVersion: '1.0.0'          // Your current version
});

// Check for updates
const result = await checker.check();
if (result?.updateAvailable) {
  console.log(`Update available: v${result.latestVersion}`);
  console.log(`Changelog: ${result.changelog}`);
}
```

## Features

- 🔄 Automatic update checking with configurable intervals
- 📝 TypeScript support with included type definitions
- 🌐 Works with both versions.json and API endpoints
- ⚡ Lightweight with minimal dependencies
- 🎯 Semantic version comparison

## API

### Constructor Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `addonName` | `string` | **required** | Your addon's slug on addons.plexdev.live |
| `currentVersion` | `string` | **required** | Your current addon version |
| `repositoryUrl` | `string` | `https://addons.plexdev.live/versions.json` | URL to versions.json |
| `apiBaseUrl` | `string` | `https://addons.plexdev.live` | Base URL for API |
| `checkInterval` | `number` | `3600000` (1 hour) | Auto-check interval in ms |
| `logUpdates` | `boolean` | `true` | Log updates to console |
| `logger` | `function` | `console.log` | Custom logger function |

### Methods

#### `check(): Promise<VersionCheckResult | null>`
Check for updates using the public versions.json endpoint.

```javascript
const result = await checker.check();
```

#### `checkFromApi(): Promise<VersionCheckResult | null>`
Check for updates using the API endpoint directly (more detailed info).

```javascript
const result = await checker.checkFromApi();
```

#### `startAutoCheck(): void`
Start automatic periodic update checking.

```javascript
checker.startAutoCheck();
```

#### `stopAutoCheck(): void`
Stop automatic periodic update checking.

```javascript
checker.stopAutoCheck();
```

#### `getAllVersions(): Promise<VersionsJson>`
Fetch all addon versions from versions.json.

```javascript
const versions = await checker.getAllVersions();
```

#### `VersionChecker.compareVersions(v1, v2): -1 | 0 | 1`
Static method to compare two semantic version strings.

```javascript
VersionChecker.compareVersions('1.0.0', '2.0.0'); // -1
VersionChecker.compareVersions('2.0.0', '2.0.0'); // 0
VersionChecker.compareVersions('2.0.0', '1.0.0'); // 1
```

#### `VersionChecker.isValidVersion(version): boolean`
Static method to validate a semantic version string.

```javascript
VersionChecker.isValidVersion('1.0.0');   // true
VersionChecker.isValidVersion('invalid'); // false
```

### VersionCheckResult

```typescript
interface VersionCheckResult {
  addon: string;           // Addon name/slug
  currentVersion: string;  // Your current version
  latestVersion: string;   // Latest available version
  isOutdated: boolean;     // Whether current < latest
  updateAvailable: boolean;// Alias for isOutdated
  changelog?: string;      // Changelog for latest version
  releaseDate?: string;    // Release date of latest version
  downloadUrl?: string;    // Download URL if available
}
```

## Discord Bot Integration

```javascript
const { Client } = require('discord.js');
const VersionChecker = require('plexaddons-version-checker');

const client = new Client({ intents: [...] });
const checker = new VersionChecker({
  addonName: 'my-discord-bot',
  currentVersion: require('./package.json').version,
  logUpdates: true,
  logger: (msg) => console.log(`[UpdateChecker] ${msg}`)
});

client.once('ready', () => {
  console.log(`Logged in as ${client.user.tag}`);
  
  // Check on startup
  checker.check();
  
  // Start hourly checks
  checker.startAutoCheck();
});

// Cleanup on shutdown
process.on('SIGINT', () => {
  checker.stopAutoCheck();
  client.destroy();
  process.exit(0);
});

client.login(process.env.DISCORD_TOKEN);
```

## Publishing Your Addon

1. Create an account at [addons.plexdev.live](https://addons.plexdev.live) using Discord OAuth
2. Register your addon in the dashboard
3. Add versions with changelogs
4. Integrate this version checker in your addon
5. Users will automatically be notified of updates!

## License

AGPL-3.0 - See [LICENSE](LICENSE) for details.

## Links

- 🌐 **Website**: [addons.plexdev.live](https://addons.plexdev.live)
- 📚 **API Docs**: [addons.plexdev.live/api/docs](https://addons.plexdev.live/api/docs)
- 🐛 **Issues**: [GitHub Issues](https://github.com/Bali0531-RC/Plexdev-Addons/issues)
