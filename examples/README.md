# PlexAddons CI/CD Examples

This folder contains example GitHub Actions workflows for automating addon publishing to [addons.plexdev.xyz](https://addons.plexdev.xyz).

## Quick Start

1. **Copy the workflow** into your addon's repository:
   ```bash
   mkdir -p .github/workflows
   cp publish-addon.yml .github/workflows/
   ```

2. **Create an API key** at https://addons.plexdev.xyz/dashboard/api-keys
   - Select the `versions:write` scope
   - Requires **Pro** or **Premium** subscription

3. **Add the secret** to your GitHub repository:
   - Go to **Settings → Secrets and variables → Actions**
   - Click **New repository secret**
   - Name: `PLEXADDONS_API_KEY`
   - Value: your API key (starts with `pa_`)

4. **Configure the workflow** — edit the `env` section in the YAML:
   ```yaml
   env:
     ADDON_SLUG: "your-addon-slug"     # Must match addons.plexdev.xyz
     DOWNLOAD_URL_TEMPLATE: "https://github.com/you/repo/releases/download/${TAG}/your-file.zip"
   ```

5. **Create a release** or push a version tag:
   ```bash
   git tag v1.2.3
   git push origin v1.2.3
   ```

## Available Workflows

### [`publish-addon.yml`](.github/workflows/publish-addon.yml)

Publishes a new addon version when you create a GitHub release or push a `v*` tag.

**Features:**
- Extracts version from git tag (strips `v` prefix)
- Auto-generates changelog from commit messages
- Uses release body as changelog when available
- Detects breaking/urgent releases
- Supports release channels (stable/beta/alpha/canary) — Pro+
- Supports gradual rollouts (0-100%) — Premium
- Posts a summary to the GitHub Actions run

**Triggers:**
- `release: published` — when you publish a GitHub release
- `push: tags: v*` — when you push a version tag

## API Key Scopes

| Scope | Description | Min Tier |
|-------|-------------|----------|
| `addons:read` | View addon info | Pro |
| `versions:read` | View version info | Pro |
| `versions:write` | **Publish new versions** | Pro |
| `analytics:read` | Access analytics | Pro |
| `addons:write` | Manage addons | Premium |
| `webhooks:manage` | Manage webhooks | Premium |

For CI/CD publishing, you only need `versions:write`.

## API Key Limits

| Tier | Max Keys |
|------|----------|
| Free | 0 |
| Pro | 3 |
| Premium | 10 |

## Security Notes

- **Never commit your API key** to the repository. Always use GitHub Secrets.
- API keys are prefixed with `pa_` and are 67 characters long.
- You can revoke keys at any time from the dashboard.
- Each key can be scoped to specific permissions.

## Example: Manual cURL Publish

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: pa_your_key_here" \
  -d '{
    "version": "1.2.3",
    "download_url": "https://example.com/addon-v1.2.3.zip",
    "description": "Bug fixes and improvements",
    "changelog_content": "- Fixed issue with startup\n- Improved performance",
    "channel": "stable",
    "rollout_percentage": 100
  }' \
  https://addons.plexdev.xyz/api/v1/addons/your-addon-slug/versions
```
