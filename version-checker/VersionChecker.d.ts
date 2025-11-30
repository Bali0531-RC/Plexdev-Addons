declare module 'plexaddons-version-checker' {
  export interface VersionInfo {
    version: string;
    changelog?: string;
    releaseDate?: string;
    downloadUrl?: string;
    minimumRequirements?: {
      node?: string;
      discordjs?: string;
    };
  }

  export interface VersionCheckResult {
    success: boolean;
    error?: string;
    isOutdated: boolean;
    isCurrent: boolean;
    isNewer: boolean;
    current: string;
    latest: string;
    releaseDate?: string;
    downloadUrl?: string;
    description?: string;
    changelog?: string;
    changelogUrl?: string;
    urgent: boolean;
    breaking: boolean;
    external: boolean;
    author?: string;
    homepage?: string;
    repository?: string;
    supportContact?: string;
    apiSource?: 'api' | 'legacy';
  }

  export interface VersionCheckerOptions {
    /**
     * URL to fetch versions.json from (fallback)
     * @default "https://addons.plexdev.live/versions.json"
     */
    repositoryUrl?: string;

    /**
     * Base URL for the PlexAddons API
     * @default "https://addons.plexdev.live"
     */
    apiUrl?: string;

    /**
     * Request timeout in milliseconds
     * @default 10000
     */
    timeout?: number;

    /**
     * Number of retry attempts
     * @default 2
     */
    retries?: number;

    /**
     * Force use of legacy versions.json API
     * @default false
     */
    useLegacyApi?: boolean;

    /**
     * Send current version to API for analytics tracking
     * Allows addon owners to see version distribution
     * @default true
     */
    trackAnalytics?: boolean;

    /**
     * API key for authenticated requests (Premium only)
     * Required for accessing analytics endpoints
     * Format: pa_<64_hex_chars>
     */
    apiKey?: string;
  }

  export interface VersionsJson {
    [addonName: string]: VersionInfo;
  }

  export interface AnalyticsResult {
    success: boolean;
    error?: string;
    total_version_checks?: number;
    total_unique_users?: number;
    addons?: Array<{
      addon_id: number;
      addon_name: string;
      version_checks: number;
      unique_users: number;
    }>;
    version_breakdown?: Record<string, number>;
  }

  export interface UserValidation {
    success: boolean;
    valid: boolean;
    error?: string;
    user?: {
      id: number;
      username: string;
      tier: 'free' | 'pro' | 'premium';
      effectiveTier: 'free' | 'pro' | 'premium';
      tempTier?: 'free' | 'pro' | 'premium' | null;
      tempTierExpiresAt?: string | null;
      hasApiKey: boolean;
    };
  }

  export interface AddonsResult {
    success: boolean;
    error?: string;
    addons: Array<{
      id: number;
      name: string;
      slug: string;
      description?: string;
    }>;
    total?: number;
  }

  export class VersionChecker {
    /**
     * Create a new VersionChecker instance
     * @param addonName - The name of your addon (must match registry)
     * @param currentVersion - Your addon's current version (e.g., "1.0.0")
     * @param options - Configuration options
     */
    constructor(addonName: string, currentVersion: string, options?: VersionCheckerOptions);

    /** The addon name */
    addonName: string;

    /** Current version string */
    currentVersion: string;

    /** URL-safe slug generated from addon name */
    addonSlug: string;

    /**
     * Check for updates
     * @returns Promise resolving to version check result
     */
    checkForUpdates(): Promise<VersionCheckResult>;

    /**
     * Get all versions for this addon
     * @param limit - Maximum versions to retrieve
     */
    getAllVersions(limit?: number): Promise<{
      success: boolean;
      versions: VersionInfo[];
      error?: string;
      note?: string;
    }>;

    /**
     * Generate colored console message for version status
     * @param checkResult - Result from checkForUpdates()
     */
    formatVersionMessage(checkResult: VersionCheckResult): string;

    /**
     * Generate detailed update information box
     * @param checkResult - Result from checkForUpdates()
     */
    getUpdateDetails(checkResult: VersionCheckResult): string;

    /**
     * Generate a plain text summary (no ANSI colors)
     * @param checkResult - Result from checkForUpdates()
     */
    getPlainSummary(checkResult: VersionCheckResult): string;

    /**
     * Convenience method to check and log results
     */
    checkAndLog(): Promise<VersionCheckResult>;

    // ============== Analytics Methods (requires API key - Premium only) ==============

    /**
     * Get analytics summary for all your addons
     * Requires Premium subscription and API key
     */
    getAnalyticsSummary(): Promise<AnalyticsResult>;

    /**
     * Get detailed analytics for a specific addon
     * Requires Premium subscription and API key
     * @param addonId - The addon ID (from your addon list)
     */
    getAddonAnalytics(addonId: number): Promise<AnalyticsResult>;

    /**
     * Get your addon list (requires API key)
     * Useful for getting addon IDs for analytics
     */
    getMyAddons(): Promise<AddonsResult>;

    /**
     * Validate API key and get user info
     */
    validateApiKey(): Promise<UserValidation>;

    /**
     * Format analytics data for console output
     * @param analytics - Analytics data from getAddonAnalytics or getAnalyticsSummary
     */
    formatAnalytics(analytics: AnalyticsResult): string;

    /**
     * Compare two semantic version strings
     * @param current - Current version string
     * @param latest - Latest version string
     * @returns -1 if current < latest, 0 if equal, 1 if current > latest
     */
    compareVersions(current: string, latest: string): -1 | 0 | 1;

    /**
     * Parse version string to numbers for comparison
     * @param version - Version string (e.g., "1.2.3")
     * @returns Array of version parts
     */
    parseVersion(version: string): number[];
  }

  export default VersionChecker;
}
