# PlexAddons

A SaaS platform for managing addon versions, changelogs, and releases. Built for the PlexDevelopment ecosystem.

## Features

- **Discord OAuth2 Authentication** - Sign in with your Discord account
- **Addon & Version Management** - Create and manage addons with version history
- **Storage Quotas** - Tiered storage limits (50MB free, 500MB Pro, 5GB Premium)
- **Version History Limits** - 5 versions (free), 10 (Pro), unlimited (Premium)
- **Stripe & PayPal Subscriptions** - Multiple payment options
- **Backward Compatible API** - `/versions.json` endpoint for PlexInstaller compatibility
- **Admin Panel** - User management, addon oversight, audit logging
- **Rate Limiting** - Per-IP and per-user rate limiting with Redis

## Architecture

```
plexaddons/
├── plexaddons-api/     # FastAPI backend
├── plexaddons-web/     # React frontend
├── docker-compose.yml  # Docker orchestration
├── .env.example        # Environment variables template
└── init-db.sql         # Database initialization
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Discord Application (for OAuth2)
- Stripe Account (optional, for payments)
- PayPal Business Account (optional, for payments)

### Setup

1. **Clone and configure**
   ```bash
   cd plexaddons
   cp .env.example .env
   # Edit .env with your credentials
   ```

2. **Configure Discord OAuth2**
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a new application
   - Add OAuth2 redirect URI: `https://addons.plexdev.live/auth/callback`
   - Copy Client ID and Client Secret to `.env`

3. **Configure Payments (optional)**
   - **Stripe**: Create products/prices in Stripe Dashboard, add keys to `.env`
   - **PayPal**: Create subscription plans in PayPal Developer Dashboard

4. **Start services**
   ```bash
   docker-compose up -d
   ```

5. **Run migrations**
   ```bash
   docker-compose exec api alembic upgrade head
   ```

6. **Access the site**
   - Web UI: http://localhost (or your configured domain)
   - API: http://localhost/api/v1/docs

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DISCORD_CLIENT_ID` | Discord OAuth2 Client ID | Yes |
| `DISCORD_CLIENT_SECRET` | Discord OAuth2 Client Secret | Yes |
| `SECRET_KEY` | JWT signing key (generate random) | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `STRIPE_SECRET_KEY` | Stripe API secret key | No |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret | No |
| `PAYPAL_CLIENT_ID` | PayPal Client ID | No |
| `PAYPAL_CLIENT_SECRET` | PayPal Client Secret | No |
| `INITIAL_ADMIN_DISCORD_ID` | Bootstrap admin user's Discord ID | No |

## API Documentation

Once running, API documentation is available at:
- Swagger UI: `/api/v1/docs`
- ReDoc: `/api/v1/redoc`

### Public Endpoints

- `GET /versions.json` - Backward-compatible versions list
- `GET /api/v1/addons` - List public addons
- `GET /api/v1/addons/{slug}` - Get addon details
- `GET /api/v1/addons/{slug}/versions` - List addon versions

### Authenticated Endpoints

All `/api/v1/users/*`, `/api/v1/addons/*` (write), `/api/v1/payments/*` endpoints require Bearer token authentication.

## Subscription Tiers

| Tier | Price | Storage | Version History | Rate Limit |
|------|-------|---------|-----------------|------------|
| Free | $0/mo | 50 MB | 5 versions | 30/min |
| Pro | $1/mo | 500 MB | 10 versions | 60/min |
| Premium | $5/mo | 5 GB | Unlimited | 120/min |

## Development

### Backend (FastAPI)

```bash
cd plexaddons-api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend (React)

```bash
cd plexaddons-web
npm install
npm run dev
```

## Deployment

The project is designed to run on a single VPS with Docker Compose. For production:

1. Use a reverse proxy (nginx/Caddy) for SSL termination
2. Set proper environment variables
3. Configure firewall rules
4. Set up monitoring and backups

### Example Caddy config:

```caddyfile
addons.plexdev.live {
    reverse_proxy localhost:80
}
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

For issues and feature requests, please use the GitHub Issues tracker.
