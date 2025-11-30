/**
 * PlexAddons Version Checker
 * 
 * A lightweight version checker for Plex addons that integrates with
 * the PlexAddons API at addons.plexdev.live
 * 
 * @example
 * const VersionChecker = require('./VersionChecker');
 * const checker = new VersionChecker('MyAddon', '1.0.0');
 * const result = await checker.checkForUpdates();
 * console.log(checker.formatVersionMessage(result));
 * 
 * @author bali0531
 * @license AGPL-3.0
 */

const fetch = require('node-fetch');

class VersionChecker {
    /**
     * Create a new VersionChecker instance
     * @param {string} addonName - The name of your addon (must match registry)
     * @param {string} currentVersion - Your addon's current version (e.g., "1.0.0")
     * @param {Object} options - Configuration options
     * @param {string} [options.apiUrl] - Custom API URL (default: addons.plexdev.live)
     * @param {string} [options.repositoryUrl] - Legacy versions.json URL (fallback)
     * @param {boolean} [options.checkOnStartup] - Auto-check on startup (default: true)
     * @param {number} [options.timeout] - Request timeout in ms (default: 10000)
     * @param {number} [options.retries] - Number of retry attempts (default: 2)
     * @param {boolean} [options.useLegacyApi] - Force use of legacy versions.json (default: false)
     */
    constructor(addonName, currentVersion, options = {}) {
        this.addonName = addonName;
        this.currentVersion = currentVersion;
        this.options = {
            apiUrl: options.apiUrl || 'https://addons.plexdev.live',
            repositoryUrl: options.repositoryUrl || 'https://addons.plexdev.live/versions.json',
            checkOnStartup: options.checkOnStartup !== false,
            timeout: options.timeout || 10000,
            retries: options.retries || 2,
            useLegacyApi: options.useLegacyApi || false,
            ...options
        };
        
        // Generate slug from addon name
        this.addonSlug = this.slugify(addonName);
    }

    /**
     * Convert addon name to URL-safe slug
     * @param {string} name - Addon name
     * @returns {string} URL-safe slug
     */
    slugify(name) {
        return name
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, '-')
            .replace(/^-+|-+$/g, '');
    }

    /**
     * Parse version string to numbers for comparison
     * @param {string} version - Version string (e.g., "1.2.3")
     * @returns {number[]} Array of version parts
     */
    parseVersion(version) {
        // Remove 'v' prefix if present
        const cleanVersion = version.replace(/^v/i, '');
        return cleanVersion.split('.').map(num => parseInt(num, 10) || 0);
    }

    /**
     * Compare two version strings
     * @param {string} current - Current version
     * @param {string} latest - Latest version
     * @returns {number} -1 if current < latest, 0 if equal, 1 if current > latest
     */
    compareVersions(current, latest) {
        const currentParts = this.parseVersion(current);
        const latestParts = this.parseVersion(latest);
        
        const maxLength = Math.max(currentParts.length, latestParts.length);
        
        for (let i = 0; i < maxLength; i++) {
            const currentPart = currentParts[i] || 0;
            const latestPart = latestParts[i] || 0;
            
            if (currentPart < latestPart) return -1;
            if (currentPart > latestPart) return 1;
        }
        
        return 0;
    }

    /**
     * Make HTTP request with timeout and retries
     * @param {string} url - URL to fetch
     * @returns {Promise<Object>} Parsed JSON response
     */
    async fetchWithRetry(url) {
        for (let attempt = 1; attempt <= this.options.retries; attempt++) {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), this.options.timeout);
                
                const response = await fetch(url, {
                    signal: controller.signal,
                    headers: {
                        'User-Agent': `PlexAddons-VersionChecker/${this.addonName}/2.0.0`,
                        'Accept': 'application/json'
                    }
                });
                
                clearTimeout(timeoutId);
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                return await response.json();
            } catch (error) {
                if (attempt === this.options.retries) {
                    throw new Error(`Failed after ${this.options.retries} attempts: ${error.message}`);
                }
                
                // Exponential backoff
                await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
            }
        }
    }

    /**
     * Fetch addon data from the new API
     * @returns {Promise<Object>} Addon and version data
     */
    async fetchFromApi() {
        // Public API endpoints (no v1 prefix)
        const latestUrl = `${this.options.apiUrl}/api/addons/${this.addonName}/latest`;
        
        // Try to get addon info from the latest endpoint
        const latestVersion = await this.fetchWithRetry(latestUrl);
        
        return {
            addon: {
                name: latestVersion.name || this.addonName,
                slug: latestVersion.slug || this.addonSlug,
                external: latestVersion.external || false,
                homepage: latestVersion.homepage || null,
                description: latestVersion.description || null,
            },
            latestVersion: latestVersion
        };
    }

    /**
     * Fetch version data from legacy versions.json
     * @returns {Promise<Object>} Version data
     */
    async fetchFromLegacy() {
        const data = await this.fetchWithRetry(this.options.repositoryUrl);
        
        if (!data.addons || !data.addons[this.addonName]) {
            throw new Error(`Addon '${this.addonName}' not found in registry`);
        }
        
        return {
            addon: {
                name: this.addonName,
                slug: this.addonSlug,
                external: data.addons[this.addonName].external || false,
                homepage: data.addons[this.addonName].homepage || null,
                description: data.addons[this.addonName].description || null
            },
            latestVersion: data.addons[this.addonName],
            repository: data.repository,
            supportContact: data.supportContact || data.supportServer,
            lastUpdated: data.lastUpdated
        };
    }

    /**
     * Check for updates
     * @returns {Promise<Object>} Update check result
     */
    async checkForUpdates() {
        try {
            let data;
            
            if (this.options.useLegacyApi) {
                // Use legacy versions.json
                data = await this.fetchFromLegacy();
            } else {
                // Try new API first, fall back to legacy
                try {
                    data = await this.fetchFromApi();
                } catch (apiError) {
                    console.log(`[VersionChecker] API unavailable, falling back to legacy endpoint`);
                    data = await this.fetchFromLegacy();
                }
            }
            
            const { addon, latestVersion } = data;
            
            if (!latestVersion) {
                return {
                    success: true,
                    isOutdated: false,
                    isCurrent: true,
                    isNewer: false,
                    current: this.currentVersion,
                    latest: this.currentVersion,
                    message: 'No version information available'
                };
            }
            
            const latestVersionStr = latestVersion.version;
            const comparison = this.compareVersions(this.currentVersion, latestVersionStr);
            
            return {
                success: true,
                isOutdated: comparison < 0,
                isNewer: comparison > 0,
                isCurrent: comparison === 0,
                current: this.currentVersion,
                latest: latestVersionStr,
                releaseDate: latestVersion.release_date || latestVersion.releaseDate,
                downloadUrl: latestVersion.download_url || latestVersion.downloadUrl,
                description: latestVersion.description || addon.description,
                changelog: latestVersion.changelog_content || latestVersion.changelog,
                changelogUrl: latestVersion.changelog_url || latestVersion.changelogUrl,
                urgent: latestVersion.urgent || false,
                breaking: latestVersion.breaking || false,
                external: addon.external || false,
                author: addon.owner?.discord_username || latestVersion.author || null,
                homepage: addon.homepage || latestVersion.homepage || null,
                repository: data.repository || 'https://github.com/Bali0531-RC/Plexdev-Addons',
                supportContact: data.supportContact || 'https://discord.gg/plexdev',
                apiSource: this.options.useLegacyApi ? 'legacy' : 'api'
            };
        } catch (error) {
            return {
                success: false,
                error: error.message,
                isOutdated: false,
                isCurrent: false,
                isNewer: false
            };
        }
    }

    /**
     * Get all versions for this addon
     * @param {number} [limit=10] - Maximum versions to retrieve
     * @returns {Promise<Object>} Versions list result
     */
    async getAllVersions(limit = 10) {
        try {
            if (this.options.useLegacyApi) {
                // Legacy API only has latest version
                const result = await this.checkForUpdates();
                return {
                    success: result.success,
                    versions: result.success ? [{
                        version: result.latest,
                        releaseDate: result.releaseDate,
                        description: result.description,
                        downloadUrl: result.downloadUrl,
                        urgent: result.urgent,
                        breaking: result.breaking
                    }] : [],
                    error: result.error
                };
            }
            
            // Use v1 API for authenticated version listing (requires auth)
            // For public use, fall back to legacy which only has latest
            const result = await this.checkForUpdates();
            return {
                success: result.success,
                versions: result.success ? [{
                    version: result.latest,
                    releaseDate: result.releaseDate,
                    description: result.description,
                    downloadUrl: result.downloadUrl,
                    urgent: result.urgent,
                    breaking: result.breaking
                }] : [],
                error: result.error,
                note: 'Public API only returns latest version. Use versions.json for all versions.'
            };
        } catch (error) {
            return {
                success: false,
                error: error.message,
                versions: []
            };
        }
    }

    /**
     * Generate colored console message for version status
     * @param {Object} checkResult - Result from checkForUpdates()
     * @returns {string} Formatted console message with ANSI colors
     */
    formatVersionMessage(checkResult) {
        if (!checkResult.success) {
            return `   \x1b[33m[WARN]\x1b[0m Version Check: \x1b[33mFailed (${checkResult.error})\x1b[0m`;
        }
        
        const { isOutdated, isCurrent, isNewer, current, latest, urgent, breaking } = checkResult;
        
        if (isOutdated) {
            let urgencyIndicator = '';
            if (urgent) urgencyIndicator = ' \x1b[91m[URGENT]\x1b[0m';
            if (breaking) urgencyIndicator += ' \x1b[95m[BREAKING]\x1b[0m';
            
            return `   \x1b[31m[UPDATE]\x1b[0m Version Check: \x1b[31mOutdated\x1b[0m (v${current} → v${latest})${urgencyIndicator}`;
        } else if (isCurrent) {
            return `   \x1b[32m[OK]\x1b[0m Version Check: \x1b[32mUp to date\x1b[0m (v${current})`;
        } else if (isNewer) {
            return `   \x1b[36m[DEV]\x1b[0m Version Check: \x1b[36mDevelopment version\x1b[0m (v${current} > v${latest})`;
        }
        
        return `   \x1b[90m[INFO]\x1b[0m Version Check: \x1b[90mUnknown status\x1b[0m`;
    }

    /**
     * Generate detailed update information box
     * @param {Object} checkResult - Result from checkForUpdates()
     * @returns {string} Detailed update information with ANSI formatting
     */
    getUpdateDetails(checkResult) {
        if (!checkResult.success || !checkResult.isOutdated) return '';
        
        const source = checkResult.external ? 'Free Addon Update' : 'Paid Addon Update';
        let details = `\n\x1b[1m📦 ${source} Available for ${this.addonName}\x1b[0m\n`;
        details += `   Current: v${checkResult.current}\n`;
        details += `   Latest:  v${checkResult.latest}`;
        
        if (checkResult.releaseDate) {
            const date = new Date(checkResult.releaseDate).toLocaleDateString();
            details += ` (${date})`;
        }
        details += '\n';
        
        if (checkResult.author) {
            details += `   Author:  ${checkResult.author}\n`;
        }
        
        if (checkResult.description) {
            details += `   Changes: ${checkResult.description}\n`;
        }
        
        if (checkResult.urgent) {
            details += `   \x1b[91m⚠️  URGENT UPDATE RECOMMENDED\x1b[0m\n`;
        }
        
        if (checkResult.breaking) {
            details += `   \x1b[95m🔄 BREAKING CHANGES - Review before updating\x1b[0m\n`;
        }
        
        if (checkResult.downloadUrl) {
            details += `   Download: ${checkResult.downloadUrl}\n`;
        }
        
        if (checkResult.changelogUrl) {
            details += `   Changelog: ${checkResult.changelogUrl}\n`;
        } else if (checkResult.changelog) {
            details += `   Changelog:\n`;
            const lines = checkResult.changelog.split('\n').slice(0, 5);
            lines.forEach(line => {
                details += `      ${line}\n`;
            });
            if (checkResult.changelog.split('\n').length > 5) {
                details += `      ... (more in full changelog)\n`;
            }
        }
        
        if (checkResult.homepage) {
            details += `   Homepage: ${checkResult.homepage}\n`;
        }
        
        if (checkResult.repository) {
            details += `   Repository: ${checkResult.repository}\n`;
        }
        
        if (checkResult.supportContact) {
            details += `   Support: ${checkResult.supportContact}\n`;
        }
        
        return details;
    }

    /**
     * Generate a plain text summary (no ANSI colors)
     * @param {Object} checkResult - Result from checkForUpdates()
     * @returns {string} Plain text summary
     */
    getPlainSummary(checkResult) {
        if (!checkResult.success) {
            return `Version Check Failed: ${checkResult.error}`;
        }
        
        if (checkResult.isOutdated) {
            let msg = `Update Available: v${checkResult.current} → v${checkResult.latest}`;
            if (checkResult.urgent) msg += ' [URGENT]';
            if (checkResult.breaking) msg += ' [BREAKING]';
            return msg;
        } else if (checkResult.isCurrent) {
            return `Up to date: v${checkResult.current}`;
        } else if (checkResult.isNewer) {
            return `Development version: v${checkResult.current} (latest: v${checkResult.latest})`;
        }
        
        return 'Unknown version status';
    }

    /**
     * Convenience method to check and log results
     * @returns {Promise<Object>} Check result
     */
    async checkAndLog() {
        const result = await this.checkForUpdates();
        console.log(this.formatVersionMessage(result));
        
        if (result.isOutdated) {
            console.log(this.getUpdateDetails(result));
        }
        
        return result;
    }
}

module.exports = VersionChecker;
