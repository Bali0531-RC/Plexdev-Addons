"""
Email Templates for PlexAddons
Professional HTML templates for all email types
"""
from datetime import datetime
from typing import Optional, Dict, Any


class EmailTemplates:
    """HTML email templates"""
    
    # Common styling
    STYLES = """
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                line-height: 1.6;
                color: #333;
                background-color: #f5f5f5;
                margin: 0;
                padding: 0;
            }
            .container {
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }
            .card {
                background: #ffffff;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                padding: 30px;
                margin-top: 20px;
            }
            .header {
                text-align: center;
                padding-bottom: 20px;
                border-bottom: 2px solid #e9a426;
            }
            .logo {
                font-size: 28px;
                font-weight: bold;
                color: #e9a426;
            }
            h1 {
                color: #333;
                font-size: 24px;
                margin-bottom: 20px;
            }
            p {
                margin-bottom: 15px;
                color: #555;
            }
            .highlight {
                background: linear-gradient(135deg, #e9a426 0%, #f5c542 100%);
                color: white;
                padding: 15px 20px;
                border-radius: 6px;
                text-align: center;
                margin: 20px 0;
            }
            .highlight-text {
                font-size: 18px;
                font-weight: bold;
            }
            .button {
                display: inline-block;
                background: #e9a426;
                color: white;
                padding: 12px 30px;
                border-radius: 6px;
                text-decoration: none;
                font-weight: bold;
                margin: 10px 0;
            }
            .button:hover {
                background: #d18f1f;
            }
            .info-box {
                background: #f8f9fa;
                border-left: 4px solid #e9a426;
                padding: 15px;
                margin: 20px 0;
            }
            .footer {
                text-align: center;
                padding-top: 20px;
                margin-top: 30px;
                border-top: 1px solid #eee;
                font-size: 12px;
                color: #888;
            }
            .stat-grid {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 15px;
                margin: 20px 0;
            }
            .stat-box {
                background: #f8f9fa;
                padding: 15px;
                border-radius: 6px;
                text-align: center;
            }
            .stat-value {
                font-size: 28px;
                font-weight: bold;
                color: #e9a426;
            }
            .stat-label {
                font-size: 12px;
                color: #666;
                text-transform: uppercase;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin: 15px 0;
            }
            th, td {
                padding: 10px;
                text-align: left;
                border-bottom: 1px solid #eee;
            }
            th {
                background: #f8f9fa;
                font-weight: 600;
            }
        </style>
    """
    
    @classmethod
    def _base_template(cls, content: str) -> str:
        """Wrap content in base template"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            {cls.STYLES}
        </head>
        <body>
            <div class="container">
                <div class="card">
                    <div class="header">
                        <div class="logo">🎬 PlexAddons</div>
                    </div>
                    {content}
                    <div class="footer">
                        <p>PlexAddons - Enhance your Plex experience</p>
                        <p>© {datetime.now().year} PlexAddons. All rights reserved.</p>
                        <p>
                            <a href="https://addons.plexdev.live" style="color: #e9a426;">Visit Website</a> |
                            <a href="https://addons.plexdev.live/docs" style="color: #e9a426;">Documentation</a>
                        </p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
    
    @classmethod
    def welcome_email(cls, username: str, email: str) -> str:
        """Welcome email for new users"""
        content = f"""
        <h1>Welcome to PlexAddons, {username}! 👋</h1>
        
        <p>Thank you for joining our community of Plex enthusiasts! Your account has been successfully created.</p>
        
        <div class="info-box">
            <strong>Your Account Details:</strong>
            <p style="margin-bottom: 0;">Username: <strong>{username}</strong><br>
            Email: <strong>{email}</strong></p>
        </div>
        
        <h2>What's Next?</h2>
        
        <p>Here are some things you can do to get started:</p>
        <ul>
            <li><strong>Explore Addons</strong> - Browse our collection of Plex addons</li>
            <li><strong>Install VersionChecker</strong> - Keep your addons up to date</li>
            <li><strong>Create Your Own Addon</strong> - Share your creations with the community</li>
            <li><strong>Upgrade to Pro</strong> - Get unlimited downloads and priority support</li>
        </ul>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="https://addons.plexdev.live/dashboard" class="button">Go to Dashboard</a>
        </div>
        
        <p>If you have any questions, feel free to reach out to our support team or check out our documentation.</p>
        
        <p>Happy streaming! 🎉</p>
        """
        return cls._base_template(content)
    
    @classmethod
    def subscription_confirmation(
        cls,
        username: str,
        plan_name: str,
        amount: float,
        next_billing_date: Optional[datetime] = None
    ) -> str:
        """Subscription confirmation email"""
        billing_info = ""
        if next_billing_date:
            billing_info = f"""
            <tr>
                <td>Next Billing Date</td>
                <td><strong>{next_billing_date.strftime('%B %d, %Y')}</strong></td>
            </tr>
            """
        
        content = f"""
        <h1>Subscription Confirmed! ✅</h1>
        
        <p>Hi {username},</p>
        
        <p>Thank you for subscribing to PlexAddons! Your subscription has been successfully activated.</p>
        
        <div class="highlight">
            <div class="highlight-text">{plan_name}</div>
            <div>${amount:.2f}/month</div>
        </div>
        
        <table>
            <tr>
                <td>Plan</td>
                <td><strong>{plan_name}</strong></td>
            </tr>
            <tr>
                <td>Amount</td>
                <td><strong>${amount:.2f}</strong></td>
            </tr>
            {billing_info}
        </table>
        
        <h2>What You Get:</h2>
        <ul>
            <li>✨ Unlimited addon downloads</li>
            <li>🚀 Priority support</li>
            <li>🔔 Early access to new features</li>
            <li>💎 Premium addons access</li>
        </ul>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="https://addons.plexdev.live/dashboard" class="button">View Subscription</a>
        </div>
        
        <p>Thank you for supporting PlexAddons!</p>
        """
        return cls._base_template(content)
    
    @classmethod
    def subscription_cancelled(
        cls,
        username: str,
        plan_name: str,
        end_date: Optional[datetime] = None
    ) -> str:
        """Subscription cancellation email"""
        end_info = ""
        if end_date:
            end_info = f"""
            <div class="info-box">
                <strong>Important:</strong> Your subscription will remain active until 
                <strong>{end_date.strftime('%B %d, %Y')}</strong>. You'll continue to have 
                access to all premium features until then.
            </div>
            """
        
        content = f"""
        <h1>Subscription Cancelled</h1>
        
        <p>Hi {username},</p>
        
        <p>We've received your request to cancel your <strong>{plan_name}</strong> subscription.</p>
        
        {end_info}
        
        <p>We're sorry to see you go! If you have any feedback about why you're cancelling, 
        we'd love to hear it to help us improve.</p>
        
        <h2>What Happens Now?</h2>
        <ul>
            <li>You'll continue to have access until your subscription period ends</li>
            <li>Your addons and data will remain in your account</li>
            <li>You can resubscribe anytime to regain premium access</li>
        </ul>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="https://addons.plexdev.live/pricing" class="button">Resubscribe</a>
        </div>
        
        <p>Thank you for being a part of PlexAddons!</p>
        """
        return cls._base_template(content)
    
    @classmethod
    def payment_received(
        cls,
        username: str,
        amount: float,
        plan_name: str,
        transaction_id: str
    ) -> str:
        """Payment receipt email"""
        content = f"""
        <h1>Payment Received 💳</h1>
        
        <p>Hi {username},</p>
        
        <p>We've received your payment. Thank you!</p>
        
        <div class="highlight">
            <div class="highlight-text">${amount:.2f}</div>
            <div>Payment Successful</div>
        </div>
        
        <h2>Receipt Details</h2>
        <table>
            <tr>
                <td>Amount</td>
                <td><strong>${amount:.2f}</strong></td>
            </tr>
            <tr>
                <td>Plan</td>
                <td><strong>{plan_name}</strong></td>
            </tr>
            <tr>
                <td>Transaction ID</td>
                <td><code>{transaction_id}</code></td>
            </tr>
            <tr>
                <td>Date</td>
                <td>{datetime.now().strftime('%B %d, %Y at %I:%M %p UTC')}</td>
            </tr>
        </table>
        
        <p style="font-size: 12px; color: #888; margin-top: 20px;">
            This receipt confirms your payment has been processed successfully. 
            Please keep this email for your records.
        </p>
        """
        return cls._base_template(content)
    
    # Admin Templates
    
    @classmethod
    def admin_new_user(cls, username: str, email: str, created_at: datetime) -> str:
        """Admin notification for new user"""
        content = f"""
        <h1>🆕 New User Registration</h1>
        
        <p>A new user has registered on PlexAddons.</p>
        
        <div class="info-box">
            <table style="margin: 0;">
                <tr>
                    <td><strong>Username:</strong></td>
                    <td>{username}</td>
                </tr>
                <tr>
                    <td><strong>Email:</strong></td>
                    <td>{email}</td>
                </tr>
                <tr>
                    <td><strong>Registered:</strong></td>
                    <td>{created_at.strftime('%B %d, %Y at %I:%M %p UTC')}</td>
                </tr>
            </table>
        </div>
        
        <div style="text-align: center; margin: 20px 0;">
            <a href="https://addons.plexdev.live/admin/users" class="button">View in Admin</a>
        </div>
        """
        return cls._base_template(content)
    
    @classmethod
    def admin_new_payment(
        cls,
        username: str,
        email: str,
        amount: float,
        plan_name: str,
        payment_provider: str
    ) -> str:
        """Admin notification for new payment"""
        content = f"""
        <h1>💰 New Payment Received</h1>
        
        <div class="highlight">
            <div class="highlight-text">${amount:.2f}</div>
            <div>{plan_name}</div>
        </div>
        
        <table>
            <tr>
                <td><strong>User:</strong></td>
                <td>{username}</td>
            </tr>
            <tr>
                <td><strong>Email:</strong></td>
                <td>{email}</td>
            </tr>
            <tr>
                <td><strong>Plan:</strong></td>
                <td>{plan_name}</td>
            </tr>
            <tr>
                <td><strong>Amount:</strong></td>
                <td>${amount:.2f}</td>
            </tr>
            <tr>
                <td><strong>Provider:</strong></td>
                <td>{payment_provider}</td>
            </tr>
            <tr>
                <td><strong>Time:</strong></td>
                <td>{datetime.now().strftime('%B %d, %Y at %I:%M %p UTC')}</td>
            </tr>
        </table>
        
        <div style="text-align: center; margin: 20px 0;">
            <a href="https://addons.plexdev.live/admin/subscriptions" class="button">View Subscriptions</a>
        </div>
        """
        return cls._base_template(content)
    
    @classmethod
    def admin_new_addon(cls, username: str, addon_name: str, addon_description: str) -> str:
        """Admin notification for new addon"""
        # Truncate description if too long
        desc = addon_description[:200] + "..." if len(addon_description) > 200 else addon_description
        
        content = f"""
        <h1>📦 New Addon Published</h1>
        
        <p>A new addon has been published on PlexAddons.</p>
        
        <div class="highlight">
            <div class="highlight-text">{addon_name}</div>
            <div>by {username}</div>
        </div>
        
        <div class="info-box">
            <strong>Description:</strong>
            <p style="margin-bottom: 0;">{desc}</p>
        </div>
        
        <table>
            <tr>
                <td><strong>Addon Name:</strong></td>
                <td>{addon_name}</td>
            </tr>
            <tr>
                <td><strong>Author:</strong></td>
                <td>{username}</td>
            </tr>
            <tr>
                <td><strong>Published:</strong></td>
                <td>{datetime.now().strftime('%B %d, %Y at %I:%M %p UTC')}</td>
            </tr>
        </table>
        
        <div style="text-align: center; margin: 20px 0;">
            <a href="https://addons.plexdev.live/admin/addons" class="button">View in Admin</a>
        </div>
        """
        return cls._base_template(content)
    
    @classmethod
    def admin_weekly_summary(
        cls,
        week_start: datetime,
        week_end: datetime,
        stats: Dict[str, Any]
    ) -> str:
        """Admin weekly summary email"""
        content = f"""
        <h1>📊 Weekly Summary</h1>
        
        <p>Here's your PlexAddons weekly report for 
        <strong>{week_start.strftime('%B %d')} - {week_end.strftime('%B %d, %Y')}</strong></p>
        
        <div class="stat-grid">
            <div class="stat-box">
                <div class="stat-value">{stats.get('new_users', 0)}</div>
                <div class="stat-label">New Users</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{stats.get('total_users', 0)}</div>
                <div class="stat-label">Total Users</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{stats.get('new_addons', 0)}</div>
                <div class="stat-label">New Addons</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{stats.get('total_addons', 0)}</div>
                <div class="stat-label">Total Addons</div>
            </div>
        </div>
        
        <h2>Subscription Stats</h2>
        <table>
            <tr>
                <td>New Subscriptions This Week</td>
                <td><strong>{stats.get('new_subscriptions', 0)}</strong></td>
            </tr>
            <tr>
                <td>Active Subscriptions</td>
                <td><strong>{stats.get('active_subscriptions', 0)}</strong></td>
            </tr>
        </table>
        
        <h2>API Usage</h2>
        <table>
            <tr>
                <td>API Requests This Week</td>
                <td><strong>{stats.get('api_requests', 'N/A')}</strong></td>
            </tr>
        </table>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="https://addons.plexdev.live/admin" class="button">View Admin Dashboard</a>
        </div>
        
        <p style="font-size: 12px; color: #888;">
            This is an automated weekly summary email. You can configure these notifications in admin settings.
        </p>
        """
        return cls._base_template(content)
    
    # Ticket Templates
    
    @classmethod
    def admin_new_ticket(
        cls,
        username: str,
        ticket_id: int,
        subject: str,
        category: str,
        priority: str,
        is_paid_user: bool
    ) -> str:
        """Admin notification for new support ticket"""
        priority_colors = {
            "low": "#28a745",
            "normal": "#ffc107",
            "high": "#fd7e14",
            "urgent": "#dc3545"
        }
        priority_color = priority_colors.get(priority, "#6c757d")
        
        paid_badge = "💎 Premium User" if is_paid_user else ""
        
        content = f"""
        <h1>🎫 New Support Ticket #{ticket_id}</h1>
        
        <p>A new support ticket has been submitted.</p>
        
        <div class="highlight" style="background: {priority_color};">
            <div class="highlight-text">{subject}</div>
            <div>Priority: {priority.upper()}</div>
        </div>
        
        <table>
            <tr>
                <td><strong>Ticket ID:</strong></td>
                <td>#{ticket_id}</td>
            </tr>
            <tr>
                <td><strong>User:</strong></td>
                <td>{username} {paid_badge}</td>
            </tr>
            <tr>
                <td><strong>Category:</strong></td>
                <td>{category.replace('_', ' ').title()}</td>
            </tr>
            <tr>
                <td><strong>Priority:</strong></td>
                <td style="color: {priority_color}; font-weight: bold;">{priority.upper()}</td>
            </tr>
            <tr>
                <td><strong>Submitted:</strong></td>
                <td>{datetime.now().strftime('%B %d, %Y at %I:%M %p UTC')}</td>
            </tr>
        </table>
        
        {"<div class='info-box' style='border-color: #dc3545; background: #fff5f5;'><strong>⚠️ Priority Support</strong><p style='margin-bottom: 0;'>This ticket is from a paid subscriber and requires priority attention.</p></div>" if is_paid_user else ""}
        
        <div style="text-align: center; margin: 20px 0;">
            <a href="https://addons.plexdev.live/admin/tickets/{ticket_id}" class="button">View Ticket</a>
        </div>
        """
        return cls._base_template(content)
    
    @classmethod
    def user_ticket_reply(
        cls,
        username: str,
        ticket_id: int,
        subject: str,
        staff_name: str,
        message_preview: str
    ) -> str:
        """User notification for staff reply on ticket"""
        # Truncate message preview
        if len(message_preview) > 300:
            message_preview = message_preview[:297] + "..."
        
        content = f"""
        <h1>💬 New Reply on Your Ticket</h1>
        
        <p>Hi {username},</p>
        
        <p>A support team member has replied to your ticket.</p>
        
        <div class="info-box">
            <strong>Ticket #{ticket_id}: {subject}</strong>
        </div>
        
        <table>
            <tr>
                <td><strong>Reply From:</strong></td>
                <td>{staff_name} (Support Staff)</td>
            </tr>
        </table>
        
        <div style="background: #f8f9fa; padding: 15px; border-radius: 6px; margin: 20px 0;">
            <p style="margin: 0; color: #555;">{message_preview}</p>
        </div>
        
        <div style="text-align: center; margin: 20px 0;">
            <a href="https://addons.plexdev.live/support/tickets/{ticket_id}" class="button">View Full Reply</a>
        </div>
        
        <p style="font-size: 12px; color: #888;">
            You can reply directly on the ticket page. Do not reply to this email.
        </p>
        """
        return cls._base_template(content)
    
    @classmethod
    def ticket_status_changed(
        cls,
        username: str,
        ticket_id: int,
        subject: str,
        old_status: str,
        new_status: str
    ) -> str:
        """User notification for ticket status change"""
        status_messages = {
            "in_progress": "Our team is actively working on your issue.",
            "resolved": "Your issue has been resolved! Please let us know if you need further assistance.",
            "closed": "This ticket has been closed. You can reopen it if needed.",
            "open": "Your ticket has been reopened and will be reviewed shortly."
        }
        
        message = status_messages.get(new_status, "The status of your ticket has been updated.")
        
        content = f"""
        <h1>📋 Ticket Status Updated</h1>
        
        <p>Hi {username},</p>
        
        <p>The status of your support ticket has been updated.</p>
        
        <div class="info-box">
            <strong>Ticket #{ticket_id}: {subject}</strong>
        </div>
        
        <table>
            <tr>
                <td><strong>Previous Status:</strong></td>
                <td>{old_status.replace('_', ' ').title()}</td>
            </tr>
            <tr>
                <td><strong>New Status:</strong></td>
                <td><strong style="color: #e9a426;">{new_status.replace('_', ' ').title()}</strong></td>
            </tr>
        </table>
        
        <p>{message}</p>
        
        <div style="text-align: center; margin: 20px 0;">
            <a href="https://addons.plexdev.live/support/tickets/{ticket_id}" class="button">View Ticket</a>
        </div>
        """
        return cls._base_template(content)

    @classmethod
    def temp_tier_granted(
        cls,
        username: str,
        tier_name: str,
        days: int,
        expires_at: datetime,
        reason: Optional[str] = None
    ) -> str:
        """Temporary tier grant notification email"""
        reason_text = ""
        if reason:
            reason_text = f"""
            <div class="info-box">
                <strong>Reason:</strong> {reason}
            </div>
            """
        
        tier_features = {
            "pro": [
                "📦 10 addon slots (up from 3)",
                "💾 500MB storage quota",
                "📊 30-day analytics history",
                "🔗 Custom profile URL",
                "🎨 Profile customization",
                "📧 Priority email support",
            ],
            "premium": [
                "📦 Unlimited addon slots",
                "💾 2GB storage quota", 
                "📊 90-day analytics history",
                "🔔 Webhook notifications",
                "⭐ Priority support",
                "🚀 Early access to new features",
                "🎨 Full profile customization",
            ],
        }
        
        features = tier_features.get(tier_name.lower(), [])
        features_html = "".join([f"<li>{f}</li>" for f in features])
        
        content = f"""
        <h1>🎉 You've Been Upgraded!</h1>
        
        <p>Hi {username},</p>
        
        <p>Great news! You've been granted temporary access to <strong>{tier_name}</strong> features on PlexAddons!</p>
        
        <div class="highlight">
            <div class="highlight-text">{tier_name.upper()}</div>
            <div>for {days} days</div>
        </div>
        
        {reason_text}
        
        <table>
            <tr>
                <td>Tier</td>
                <td><strong style="color: #e9a426;">{tier_name}</strong></td>
            </tr>
            <tr>
                <td>Duration</td>
                <td><strong>{days} days</strong></td>
            </tr>
            <tr>
                <td>Expires</td>
                <td><strong>{expires_at.strftime('%B %d, %Y at %H:%M UTC')}</strong></td>
            </tr>
        </table>
        
        <h2>What You Can Do Now:</h2>
        <ul>
            {features_html}
        </ul>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="https://addons.plexdev.live/dashboard" class="button">Explore Your New Features</a>
        </div>
        
        <p style="font-size: 12px; color: #888;">
            After your temporary access expires, you can subscribe to continue enjoying these features.
        </p>
        """
        return cls._base_template(content)
