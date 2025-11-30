# Services
from app.services.auth_service import AuthService
from app.services.user_service import UserService, AVAILABLE_BADGES
from app.services.addon_service import AddonService
from app.services.version_service import VersionService
from app.services.stripe_service import StripeService
from app.services.paypal_service import PayPalService
from app.services.email_service import EmailService, email_service
from app.services.email_templates import EmailTemplates
from app.services.ticket_service import TicketService, ticket_service
from app.services.discord_service import DiscordService, discord_service
from app.services.analytics_service import AnalyticsService
from app.services.webhook_service import WebhookService, webhook_service
