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
    addon: string;
    currentVersion: string;
    latestVersion: string;
    isOutdated: boolean;
    updateAvailable: boolean;
    changelog?: string;
    releaseDate?: string;
    downloadUrl?: string;
  }

  export interface VersionCheckerOptions {
    /**
     * The name/slug of your addon as registered on addons.plexdev.live
     */
    addonName: string;

    /**
     * Your current addon version (e.g., "1.0.0")
     */
    currentVersion: string;

    /**
     * URL to fetch versions.json from
     * @default "https://addons.plexdev.live/versions.json"
     */
    repositoryUrl?: string;

    /**
     * Base URL for the PlexAddons API
     * @default "https://addons.plexdev.live/api/v1"
     */
    apiBaseUrl?: string;

    /**
     * Check interval in milliseconds
     * @default 3600000 (1 hour)
     */
    checkInterval?: number;

    /**
     * Whether to log update notifications to console
     * @default true
     */
    logUpdates?: boolean;

    /**
     * Custom logger function
     */
    logger?: (message: string) => void;
  }

  export interface VersionsJson {
    [addonName: string]: VersionInfo;
  }

  export class VersionChecker {
    constructor(options: VersionCheckerOptions);

    /**
     * Check for updates using the versions.json endpoint
     * @returns Promise resolving to version check result, or null if check fails
     */
    check(): Promise<VersionCheckResult | null>;

    /**
     * Check for updates using the API endpoint directly
     * @returns Promise resolving to version check result, or null if check fails
     */
    checkFromApi(): Promise<VersionCheckResult | null>;

    /**
     * Start automatic periodic update checks
     */
    startAutoCheck(): void;

    /**
     * Stop automatic periodic update checks
     */
    stopAutoCheck(): void;

    /**
     * Get all versions from the versions.json
     * @returns Promise resolving to versions object
     */
    getAllVersions(): Promise<VersionsJson>;

    /**
     * Compare two semantic version strings
     * @param version1 First version string
     * @param version2 Second version string
     * @returns -1 if version1 < version2, 0 if equal, 1 if version1 > version2
     */
    static compareVersions(version1: string, version2: string): -1 | 0 | 1;

    /**
     * Check if a version string is valid semver
     * @param version Version string to validate
     */
    static isValidVersion(version: string): boolean;
  }

  export default VersionChecker;
}
