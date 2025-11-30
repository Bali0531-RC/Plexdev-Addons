/**
 * PlexAddons Version Checker - Usage Examples
 * 
 * These examples show how to integrate the VersionChecker
 * into your Plex addon for automatic update notifications.
 */

const VersionChecker = require('./VersionChecker');

// =============================================================================
// BASIC USAGE
// =============================================================================

async function basicExample() {
    // Create a version checker for your addon
    // Analytics tracking is enabled by default (sends version to API)
    const checker = new VersionChecker('AiModeration', '1.3.0');
    
    // Check for updates
    const result = await checker.checkForUpdates();
    
    // Log formatted message
    console.log(checker.formatVersionMessage(result));
    
    // If outdated, show details
    if (result.isOutdated) {
        console.log(checker.getUpdateDetails(result));
    }
}

// =============================================================================
// ANALYTICS TRACKING (enabled by default)
// =============================================================================

async function analyticsExample() {
    // Analytics tracking is ON by default
    // When your users check for updates, their current version is sent to the API
    // You (the addon owner) can view version distribution in your dashboard
    // at addons.plexdev.live - no API key needed in the VersionChecker!
    
    const checker = new VersionChecker('MyAddon', '1.0.0');
    const result = await checker.checkForUpdates();
    console.log(checker.formatVersionMessage(result));
    
    // To disable analytics tracking (not recommended):
    const privateChecker = new VersionChecker('MyAddon', '1.0.0', {
        trackAnalytics: false
    });
}

// =============================================================================
// INTEGRATION WITH PLEX BOT STARTUP
// =============================================================================

async function botStartupExample() {
    const checker = new VersionChecker('MyAddon', '1.0.0');
    
    console.log('┌────────────────────────────────────────┐');
    console.log('│           MyAddon v1.0.0               │');
    console.log('└────────────────────────────────────────┘');
    
    // Check version on startup
    const result = await checker.checkAndLog();
    
    // You can also access the result programmatically
    if (result.isOutdated && result.urgent) {
        // Maybe notify admin or log warning
        console.warn('URGENT: Please update your addon immediately!');
    }
}

// =============================================================================
// CUSTOM API URL (Self-hosted PlexAddons)
// =============================================================================

async function customApiExample() {
    const checker = new VersionChecker('MyAddon', '1.0.0', {
        // Use a self-hosted PlexAddons instance
        apiUrl: 'https://my-plexaddons.example.com',
        
        // Or use a custom versions.json
        repositoryUrl: 'https://example.com/my-versions.json',
        useLegacyApi: true
    });
    
    const result = await checker.checkForUpdates();
    console.log(result);
}

// =============================================================================
// DISCORD EMBED NOTIFICATION
// =============================================================================

async function discordNotificationExample(discordClient) {
    const checker = new VersionChecker('TempVoice', '1.0.5');
    const result = await checker.checkForUpdates();
    
    if (result.isOutdated) {
        // Create Discord embed for update notification
        const embed = {
            title: `📦 Update Available: ${checker.addonName}`,
            color: result.urgent ? 0xff0000 : 0xffaa00,
            fields: [
                { name: 'Current Version', value: `v${result.current}`, inline: true },
                { name: 'Latest Version', value: `v${result.latest}`, inline: true },
                { name: 'Released', value: result.releaseDate || 'Unknown', inline: true },
            ],
            footer: { text: 'PlexAddons Version Checker' }
        };
        
        if (result.description) {
            embed.description = result.description;
        }
        
        if (result.urgent) {
            embed.fields.push({ name: '⚠️ Priority', value: 'URGENT UPDATE', inline: false });
        }
        
        if (result.breaking) {
            embed.fields.push({ name: '🔄 Notice', value: 'Contains breaking changes', inline: false });
        }
        
        // Send to your notification channel
        // await notificationChannel.send({ embeds: [embed] });
        
        console.log('Discord embed:', embed);
    }
}

// =============================================================================
// PERIODIC UPDATE CHECKS
// =============================================================================

function periodicCheckExample() {
    const checker = new VersionChecker('RewardSystem', '1.0.0');
    
    // Check every 6 hours
    const CHECK_INTERVAL = 6 * 60 * 60 * 1000;
    
    async function checkUpdates() {
        const result = await checker.checkForUpdates();
        
        if (result.isOutdated) {
            console.log(checker.formatVersionMessage(result));
            console.log(checker.getUpdateDetails(result));
        }
    }
    
    // Initial check
    checkUpdates();
    
    // Schedule periodic checks
    setInterval(checkUpdates, CHECK_INTERVAL);
}

// =============================================================================
// GET ALL VERSIONS (History)
// =============================================================================

async function versionHistoryExample() {
    const checker = new VersionChecker('InviteLogger', '1.0.0');
    
    // Get last 5 versions
    const history = await checker.getAllVersions(5);
    
    if (history.success) {
        console.log(`Found ${history.total} versions:`);
        history.versions.forEach(v => {
            console.log(`  - v${v.version} (${v.release_date || v.releaseDate})`);
            if (v.breaking) console.log('    [BREAKING CHANGES]');
        });
    }
}

// =============================================================================
// SILENT CHECK (No console output)
// =============================================================================

async function silentCheckExample() {
    const checker = new VersionChecker('MusicAddon', '1.0.0');
    const result = await checker.checkForUpdates();
    
    // Use result without logging
    return {
        needsUpdate: result.isOutdated,
        currentVersion: result.current,
        latestVersion: result.latest,
        downloadUrl: result.downloadUrl,
        isUrgent: result.urgent,
        hasBreakingChanges: result.breaking
    };
}

// =============================================================================
// ERROR HANDLING
// =============================================================================

async function errorHandlingExample() {
    const checker = new VersionChecker('NonExistentAddon', '1.0.0', {
        timeout: 5000,
        retries: 1
    });
    
    const result = await checker.checkForUpdates();
    
    if (!result.success) {
        console.error(`Version check failed: ${result.error}`);
        // Continue without crashing - addon still works
    } else if (result.isOutdated) {
        console.log(checker.formatVersionMessage(result));
    }
}

// =============================================================================
// RUN EXAMPLES
// =============================================================================

async function runExamples() {
    console.log('\n=== Basic Example ===');
    await basicExample();
    
    console.log('\n=== Bot Startup Example ===');
    await botStartupExample();
    
    console.log('\n=== Version History Example ===');
    await versionHistoryExample();
    
    console.log('\n=== Silent Check Example ===');
    const silentResult = await silentCheckExample();
    console.log('Silent result:', silentResult);
    
    console.log('\n=== Error Handling Example ===');
    await errorHandlingExample();
}

// Uncomment to run examples:
// runExamples().catch(console.error);

module.exports = { runExamples };
