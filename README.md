# PlexAddons

A full SaaS platform for managing Plex addons with version tracking, Discord OAuth2 authentication, and tiered subscriptions.

**Live at:** [addons.plexdev.live](https://addons.plexdev.live)

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
  - [Environment Variables](#environment-variables)
  - [Discord OAuth2 Setup](#discord-oauth2-setup)
  - [Stripe Setup](#stripe-setup)
  - [PayPal Setup](#paypal-setup)
- [Deployment](#deployment)
  - [Docker Compose](#docker-compose)
  - [Nginx Reverse Proxy](#nginx-reverse-proxy)
  - [SSL with Certbot](#ssl-with-certbot)
- [Database Migrations](#database-migrations)
- [Importing Existing Addons](#importing-existing-addons)
- [API Documentation](#api-documentation)
- [Subscription Tiers](#subscription-tiers)
- [Admin Management](#admin-management)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Features

- **Discord OAuth2 Authentication** - Login with Discord accounts
- **Addon Management** - Create and manage addons with metadata (no file storage)
- **Version Tracking** - Track versions with changelogs and semver sorting
- **Tiered Subscriptions** - Free, Pro ($1/mo), and Premium ($5/mo) plans
- **Storage Quotas** - 50MB / 500MB / 5GB by tier
- **Version History Limits** - 5 / 10 / Unlimited by tier
- **Rate Limiting** - Per-IP and per-user rate limiting with Redis
- **Admin Dashboard** - User management, audit logs, system overview
- **Backward Compatible API** - `/versions.json` endpoint for existing integrations
- **Dual Payment Providers** - Stripe and PayPal support
- **90-Day Audit Log Auto-Purge** - Automatic cleanup of old audit logs

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Docker Compose                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐      ┌─────────────────┐                   │
│  │   plexaddons-web │      │  plexaddons-api │                   │
│  │   (React + Vite) │      │    (FastAPI)    │                   │
│  │     Port 3310    │      │    Port 3311    │                   │
│  └────────┬────────┘      └────────┬────────┘                   │
│           │                        │                             │
│           └────────────┬───────────┘                             │
│                        │                                         │
│           ┌────────────┴───────────┐                             │
│           │                        │                             │
│  ┌────────▼────────┐      ┌────────▼────────┐                   │
│  │   PostgreSQL    │      │     Redis       │                   │
│  │   (Database)    │      │  (Rate Limit)   │                   │
│  │   Port 5432     │      │   Port 6379     │                   │
│  └─────────────────┘      └─────────────────┘                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

- **Docker** (20.10+) and **Docker Compose** (2.0+)
- **Domain name** pointed to your server (e.g., `addons.plexdev.live`)
- **Discord Application** for OAuth2
- **Stripe Account** (optional, for payments)
- **PayPal Business Account** (optional, for payments)

---

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/plexdev/plexaddons.git
cd plexaddons
```

### 2. Create Environment File

```bash
cp .env.example .env
```

### 3. Configure Environment Variables

Edit `.env` with your values (see [Configuration](#configuration) section for details):

```bash
nano .env
```

### 4. Start the Services

```bash
docker-compose up -d --build
```

### 5. Run Database Migrations

```bash
docker-compose exec api alembic upgrade head
```

### 6. Access the Application

- **Frontend:** http://localhost:3310
- **API:** http://localhost:3311
- **API Docs:** http://localhost:3311/docs

---

## Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# =============================================================================
# DATABASE
# =============================================================================
POSTGRES_USER=plexaddons
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=plexaddons
DATABASE_URL=postgresql+asyncpg://plexaddons:your_secure_password_here@db:5432/plexaddons

# =============================================================================
# REDIS
# =============================================================================
REDIS_URL=redis://redis:6379/0

# =============================================================================
# SECURITY
# =============================================================================
# Generate with: openssl rand -hex 32
SECRET_KEY=your_64_character_hex_secret_key_here

# =============================================================================
# DISCORD OAUTH2
# =============================================================================
DISCORD_CLIENT_ID=your_discord_client_id
DISCORD_CLIENT_SECRET=your_discord_client_secret
DISCORD_REDIRECT_URI=https://addons.plexdev.live/auth/callback

# =============================================================================
# STRIPE (Optional - for payments)
# =============================================================================
STRIPE_SECRET_KEY=sk_live_your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=whsec_your_stripe_webhook_secret
STRIPE_PRO_PRICE_ID=price_your_pro_price_id
STRIPE_PREMIUM_PRICE_ID=price_your_premium_price_id

# =============================================================================
# PAYPAL (Optional - for payments)
# =============================================================================
PAYPAL_CLIENT_ID=your_paypal_client_id
PAYPAL_CLIENT_SECRET=your_paypal_client_secret
PAYPAL_WEBHOOK_ID=your_paypal_webhook_id
PAYPAL_PRO_PLAN_ID=P-your_paypal_pro_plan_id
PAYPAL_PREMIUM_PLAN_ID=P-your_paypal_premium_plan_id

# =============================================================================
# APPLICATION
# =============================================================================
FRONTEND_URL=https://addons.plexdev.live
API_URL=https://addons.plexdev.live/api

# =============================================================================
# ADMIN BOOTSTRAP
# =============================================================================
# Discord User ID to set as initial admin (get from Discord Developer Mode)
INITIAL_ADMIN_DISCORD_ID=your_discord_user_id
```

### Discord OAuth2 Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)

2. Click **"New Application"** and give it a name (e.g., "PlexAddons")

3. Go to **OAuth2** → **General**

4. Copy the **Client ID** and **Client Secret** to your `.env` file

5. Add a **Redirect URI**:
   ```
   https://addons.plexdev.live/auth/callback
   ```
   For local development:
   ```
   http://localhost:3310/auth/callback
   ```

6. Go to **OAuth2** → **URL Generator**:
   - Select scopes: `identify`, `email`
   - This is for testing; the app generates URLs automatically

7. (Optional) Customize your app with a logo in **General Information**

### Stripe Setup

1. Create a [Stripe Account](https://stripe.com)

2. Get your API keys from **Developers** → **API Keys**:
   - Copy **Secret key** to `STRIPE_SECRET_KEY`

3. Create Products and Prices:
   - Go to **Products** → **Add Product**
   - Create "Pro" plan at $1/month (recurring)
   - Create "Premium" plan at $5/month (recurring)
   - Copy the Price IDs to `STRIPE_PRO_PRICE_ID` and `STRIPE_PREMIUM_PRICE_ID`

4. Set up Webhooks:
   - Go to **Developers** → **Webhooks**
   - Add endpoint: `https://addons.plexdev.live/api/webhooks/stripe`
   - Select events:
     - `checkout.session.completed`
     - `customer.subscription.updated`
     - `customer.subscription.deleted`
     - `invoice.payment_succeeded`
     - `invoice.payment_failed`
   - Copy **Signing secret** to `STRIPE_WEBHOOK_SECRET`

### PayPal Setup

1. Create a [PayPal Business Account](https://www.paypal.com/business)

2. Go to [PayPal Developer Dashboard](https://developer.paypal.com/dashboard/)

3. Create an App:
   - Go to **Apps & Credentials**
   - Create app (Live mode for production)
   - Copy **Client ID** and **Secret** to `.env`

4. Create Subscription Plans:
   - Go to **Subscriptions** → **Plans**
   - Create "Pro" plan at $1/month
   - Create "Premium" plan at $5/month
   - Copy Plan IDs to `.env`

5. Set up Webhooks:
   - Go to **Webhooks** in your app settings
   - Add webhook URL: `https://addons.plexdev.live/api/webhooks/paypal`
   - Select events:
     - `BILLING.SUBSCRIPTION.ACTIVATED`
     - `BILLING.SUBSCRIPTION.CANCELLED`
     - `BILLING.SUBSCRIPTION.SUSPENDED`
     - `BILLING.SUBSCRIPTION.UPDATED`
     - `PAYMENT.SALE.COMPLETED`
   - Copy **Webhook ID** to `PAYPAL_WEBHOOK_ID`

---

## Deployment

### Docker Compose

The application runs on the following ports:
- **3310** - Frontend (React/Nginx)
- **3311** - Backend API (FastAPI)

```bash
# Build and start all services
docker-compose up -d --build

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f api
docker-compose logs -f web

# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes data)
docker-compose down -v

# Restart a specific service
docker-compose restart api
```

### Nginx Reverse Proxy

If you're running nginx on the host to proxy to Docker, use this configuration:

```nginx
# /etc/nginx/sites-available/addons.plexdev.live

# Rate limiting zone
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

# Upstream servers
upstream plexaddons_web {
    server 127.0.0.1:3310;
}

upstream plexaddons_api {
    server 127.0.0.1:3311;
}

server {
    listen 80;
    server_name addons.plexdev.live;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name addons.plexdev.live;

    # SSL Configuration (managed by Certbot)
    ssl_certificate /etc/letsencrypt/live/addons.plexdev.live/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/addons.plexdev.live/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
    gzip_min_length 1000;

    # API Routes
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;
        
        proxy_pass http://plexaddons_api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Webhook Routes (no rate limit for payment webhooks)
    location /api/webhooks/ {
        proxy_pass http://plexaddons_api/webhooks/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Public versions.json endpoint
    location /versions.json {
        proxy_pass http://plexaddons_api/versions.json;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_cache_valid 200 5m;
    }

    # Frontend (catch-all)
    location / {
        proxy_pass http://plexaddons_web;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/addons.plexdev.live /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### SSL with Certbot

Install Certbot and obtain SSL certificate:

```bash
# Install Certbot
sudo apt update
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d addons.plexdev.live

# Test auto-renewal
sudo certbot renew --dry-run
```

---

## Database Migrations

The project uses Alembic for database migrations.

```bash
# Run all pending migrations
docker-compose exec api alembic upgrade head

# Check current revision
docker-compose exec api alembic current

# View migration history
docker-compose exec api alembic history

# Create a new migration
docker-compose exec api alembic revision --autogenerate -m "Description of changes"

# Downgrade one revision
docker-compose exec api alembic downgrade -1

# Downgrade to beginning
docker-compose exec api alembic downgrade base
```

---

## Importing Existing Addons

If you have an existing `versions.json` file from PlexAddons, you can import it:

### From Local File

```bash
# Copy your versions.json to the container
docker cp /path/to/versions.json plexaddons-api:/app/versions.json

# Run the import script
docker-compose exec api python -m app.scripts.import_versions /app/versions.json
```

### From URL

```bash
docker-compose exec api python -m app.scripts.import_versions https://raw.githubusercontent.com/user/PlexAddons/main/versions.json
```

The import script will:
- Create addon entries for each addon in the JSON
- Import all versions with their changelogs
- Assign default ownership to the first admin user
- Skip duplicates if run multiple times

---

## API Documentation

Once the API is running, interactive documentation is available at:

- **Swagger UI:** http://localhost:3311/docs (dev only)
- **ReDoc:** http://localhost:3311/redoc (dev only)
- **ReDoc (production):** https://addons.plexdev.live/redocs

### Key Endpoints

#### Public API (no authentication required)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/versions.json` | GET | Backward-compatible versions endpoint |
| `/api/addons` | GET | List all public addons with basic info |
| `/api/addons/{name}/latest` | GET | Get latest version for a specific addon |

#### Authenticated API (requires Bearer token)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/discord` | GET | Start Discord OAuth flow |
| `/api/v1/auth/callback` | GET | OAuth callback handler |
| `/api/v1/users/me` | GET | Get current user |
| `/api/v1/addons` | GET | List all public addons (detailed) |
| `/api/v1/addons` | POST | Create new addon |
| `/api/v1/addons/{slug}` | GET | Get addon by slug |
| `/api/v1/addons/{slug}/versions` | GET | List addon versions |
| `/api/v1/addons/{slug}/versions` | POST | Create new version |
| `/api/v1/payments/stripe/checkout` | POST | Create Stripe checkout |
| `/api/v1/payments/paypal/checkout` | POST | Create PayPal subscription |
| `/api/v1/admin/users` | GET | List all users (admin) |
| `/api/v1/admin/addons` | GET | List all addons (admin) |
| `/api/v1/admin/audit-log` | GET | View audit logs (admin) |

---

## Subscription Tiers

| Feature | Free | Pro ($1/mo) | Premium ($5/mo) |
|---------|------|-------------|-----------------|
| Storage Quota | 50 MB | 500 MB | 5 GB |
| Version History | 5 versions | 10 versions | Unlimited |
| Rate Limit | 30 req/min | 60 req/min | 120 req/min |
| Public Addons | ✓ | ✓ | ✓ |
| Private Addons | ✗ | ✓ | ✓ |
| Priority Support | ✗ | ✗ | ✓ |

---

## Admin Management

### Initial Admin Setup

Set the `INITIAL_ADMIN_DISCORD_ID` environment variable to your Discord User ID before first launch. To get your Discord User ID:

1. Enable Developer Mode in Discord (Settings → Advanced → Developer Mode)
2. Right-click your username and select "Copy User ID"
3. Add to `.env`: `INITIAL_ADMIN_DISCORD_ID=123456789012345678`

### Managing Admins via Dashboard

1. Log in as an admin
2. Go to **Admin** → **Users**
3. Click on a user to view details
4. Toggle the **Admin** switch to grant/revoke admin privileges

### Admin Actions Audit Log

All admin actions are logged and viewable at **Admin** → **Audit Logs**:
- User modifications
- Subscription changes
- Addon deletions
- Role changes

Audit logs are automatically purged after 90 days.

---

## Troubleshooting

### Container won't start

```bash
# Check container status
docker-compose ps

# View detailed logs
docker-compose logs api
docker-compose logs web
docker-compose logs db

# Check if ports are in use
sudo lsof -i :3310
sudo lsof -i :3311
```

### Database connection errors

```bash
# Ensure database is running
docker-compose ps db

# Check database logs
docker-compose logs db

# Test connection
docker-compose exec db psql -U plexaddons -d plexaddons -c "SELECT 1"
```

### Redis connection errors

```bash
# Check Redis status
docker-compose exec redis redis-cli ping
# Should return: PONG

# View Redis info
docker-compose exec redis redis-cli info
```

### OAuth callback errors

1. Verify `DISCORD_REDIRECT_URI` matches exactly what's configured in Discord Developer Portal
2. Ensure `FRONTEND_URL` is correct in `.env`
3. Check API logs for detailed error messages

### Migration errors

```bash
# Check current state
docker-compose exec api alembic current

# View pending migrations
docker-compose exec api alembic history

# Reset and re-run (WARNING: data loss)
docker-compose exec api alembic downgrade base
docker-compose exec api alembic upgrade head
```

### Webhook not working

1. Verify webhook URLs are accessible from the internet
2. Check webhook secrets match
3. View webhook logs in Stripe/PayPal dashboards
4. Check API logs: `docker-compose logs api | grep webhook`

### Clear all data and start fresh

```bash
# Stop everything and remove volumes
docker-compose down -v

# Remove any orphaned volumes
docker volume prune

# Rebuild and start
docker-compose up -d --build

# Run migrations
docker-compose exec api alembic upgrade head
```

---

## Development

### Running Locally (without Docker)

**Backend:**
```bash
cd plexaddons-api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/plexaddons
export REDIS_URL=redis://localhost:6379/0
# ... other variables

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd plexaddons-web
npm install
npm run dev
```

### Code Structure

```
plexaddons/
├── docker-compose.yml      # Container orchestration
├── .env.example            # Environment template
├── init-db.sql             # Database initialization
│
├── plexaddons-api/         # FastAPI Backend
│   ├── app/
│   │   ├── main.py         # Application entry
│   │   ├── config.py       # Settings
│   │   ├── database.py     # Database connection
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic
│   │   ├── api/            # Route handlers
│   │   ├── core/           # Security, rate limiting
│   │   ├── webhooks/       # Payment webhooks
│   │   └── scripts/        # CLI utilities
│   ├── alembic/            # Migrations
│   ├── requirements.txt
│   └── Dockerfile
│
└── plexaddons-web/         # React Frontend
    ├── src/
    │   ├── main.tsx        # Entry point
    │   ├── App.tsx         # Router setup
    │   ├── pages/          # Page components
    │   ├── components/     # Shared components
    │   ├── context/        # React context
    │   ├── services/       # API client
    │   └── types/          # TypeScript types
    ├── package.json
    ├── vite.config.ts
    └── Dockerfile
```

---

## License

GNU Affero General Public License v3.0 - see [LICENSE](LICENSE) file for details.

---

## Support

- **Issues:** [GitHub Issues](https://github.com/Bali0531-RC/Plexdev-Addons/issues)
- **Discord:** [PlexDevelopment Discord](https://discord.gg/plexdev)
- **Email:** bali0531@plexdev.live
