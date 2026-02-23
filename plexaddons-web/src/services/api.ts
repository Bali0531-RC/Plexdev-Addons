import { 
  User, 
  Addon, 
  Version, 
  Subscription, 
  PaymentPlan, 
  StorageInfo,
  AdminStats,
  AuditLogEntry,
  AddonListResponse,
  VersionListResponse,
  AddonCreate,
  AddonUpdate,
  VersionCreate,
  VersionUpdate,
  ReleaseChannel,
  Ticket,
  TicketDetail,
  TicketListResponse,
  TicketCreate,
  TicketMessage,
  TicketAttachment,
  TicketStatus,
  TicketPriority,
  TicketCategory,
  TicketStats,
  CannedResponse,
  CannedResponseListResponse,
  UserPublicProfile,
  UserProfileUpdate,
  ApiKeyInfo,
  ApiKeyCreated,
  AnalyticsSummary,
  AddonAnalytics,
  ApiUsageAnalytics,
  WebhookConfig,
  WebhookUpdate,
  WebhookTestResponse,
  AddonTag,
  Organization,
  Collaborator,
  CollaboratorRole,
  CollaborationInvitation,
  OrganizationDetail,
  OrganizationCreate,
  OrganizationUpdate,
  OrganizationMember,
  OrganizationRole,
  StarStatus,
  Review,
  ReviewListResponse,
  ReviewCreate,
  ReviewUpdate,
  TrendingAddon,
  NotificationListResponse,
  AddonLicense,
  LicenseListResponse,
  LicenseVerifyResponse,
  PurchaseAddonResponse,
  StripeConnectStatus,
  RevenueStats,
  OrgAuditLogListResponse,
  OrgApiKeyCreateResponse,
  OrgApiKeyListResponse,
  OrgAnalyticsSummary,
  OrgPublicPage,
  WebhookEndpoint,
  WebhookEndpointCreate,
  WebhookEndpointUpdate,
  WebhookDelivery,
  RealtimeStats,
  RecentCheck,
  HourlyBreakdown,
  AnalyticsAlert,
  CohortAnalysisResponse,
  PredictiveEstimate,
  SelfHostedConfig,
} from '../types';

const API_BASE = import.meta.env.VITE_API_URL || '/api';

const ALLOWED_REDIRECT_DOMAINS = [
  'checkout.stripe.com',
  'billing.stripe.com',
  'discord.com',
  'www.paypal.com',
  'paypal.com',
];

/**
 * Validates that a URL is safe to redirect to.
 * Only allows HTTPS URLs on known, trusted domains.
 */
export function isAllowedRedirectUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== 'https:') return false;
    return ALLOWED_REDIRECT_DOMAINS.includes(parsed.hostname);
  } catch {
    return false;
  }
}

/**
 * Safely redirect to a URL, but only if it's on an allowed domain.
 * Throws an error if the URL is not allowed.
 */
export function safeRedirect(url: string): void {
  if (!isAllowedRedirectUrl(url)) {
    throw new Error('Redirect blocked: untrusted URL');
  }
  window.location.href = url;
}

class ApiClient {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
  }

  private async fetch<T>(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<T> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.token) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  }

  // Auth
  async getAuthUrl(): Promise<{ url: string; state: string }> {
    return this.fetch('/v1/auth/url');
  }

  async handleCallback(code: string, state?: string): Promise<{ access_token: string; user: User }> {
    const params = new URLSearchParams({ code });
    if (state) params.append('state', state);
    return this.fetch(`/v1/auth/discord/callback/api?${params}`);
  }

  // Users
  async getMe(): Promise<User> {
    return this.fetch('/v1/users/me');
  }

  async updateMe(data: { email?: string }): Promise<User> {
    return this.fetch('/v1/users/me', {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteMyAccount(): Promise<void> {
    return this.fetch('/v1/users/me', {
      method: 'DELETE',
    });
  }

  async getMyStorage(): Promise<StorageInfo> {
    return this.fetch('/v1/users/me/storage');
  }

  async getMySubscription(): Promise<Subscription | null> {
    return this.fetch('/v1/users/me/subscription');
  }

  // Addons
  async listAddons(page = 1, perPage = 20, search?: string, tag?: AddonTag, sortBy?: string): Promise<AddonListResponse> {
    const params = new URLSearchParams({ page: String(page), per_page: String(perPage) });
    if (search) params.append('search', search);
    if (tag) params.append('tag', tag);
    if (sortBy) params.append('sort_by', sortBy);
    return this.fetch(`/v1/addons?${params}`);
  }

  // Tags
  async getTags(): Promise<{ tags: AddonTag[] }> {
    return this.fetch('/v1/tags');
  }

  async listMyAddons(page = 1, perPage = 20): Promise<AddonListResponse> {
    const params = new URLSearchParams({ page: String(page), per_page: String(perPage) });
    return this.fetch(`/v1/addons/mine?${params}`);
  }

  async getAddon(slug: string): Promise<Addon> {
    return this.fetch(`/v1/addons/${slug}`);
  }

  async createAddon(data: AddonCreate): Promise<Addon> {
    return this.fetch('/v1/addons', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateAddon(slug: string, data: AddonUpdate): Promise<Addon> {
    return this.fetch(`/v1/addons/${slug}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteAddon(slug: string): Promise<void> {
    return this.fetch(`/v1/addons/${slug}`, { method: 'DELETE' });
  }

  // Stars / Favorites
  async starAddon(slug: string): Promise<StarStatus> {
    return this.fetch(`/v1/stars/addons/${slug}`, { method: 'POST' });
  }

  async unstarAddon(slug: string): Promise<StarStatus> {
    return this.fetch(`/v1/stars/addons/${slug}`, { method: 'DELETE' });
  }

  async getStarStatus(slug: string): Promise<StarStatus> {
    return this.fetch(`/v1/stars/addons/${slug}`);
  }

  async getMyStarredAddons(page = 1, perPage = 20): Promise<AddonListResponse> {
    const params = new URLSearchParams({ page: String(page), per_page: String(perPage) });
    return this.fetch(`/v1/stars/mine?${params}`);
  }

  // Reviews
  async getReviews(slug: string, page = 1, perPage = 20): Promise<ReviewListResponse> {
    const params = new URLSearchParams({ page: String(page), per_page: String(perPage) });
    return this.fetch(`/v1/addons/${slug}/reviews?${params}`);
  }

  async createReview(slug: string, data: ReviewCreate): Promise<Review> {
    return this.fetch(`/v1/addons/${slug}/reviews`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateReview(slug: string, data: ReviewUpdate): Promise<Review> {
    return this.fetch(`/v1/addons/${slug}/reviews`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteReview(slug: string): Promise<void> {
    return this.fetch(`/v1/addons/${slug}/reviews`, { method: 'DELETE' });
  }

  // Trending
  async getTrendingAddons(limit = 10): Promise<{ trending: TrendingAddon[] }> {
    return this.fetch(`/v1/addons/trending?limit=${limit}`);
  }

  // Versions
  async listVersions(slug: string, skip = 0, limit = 50, channel?: ReleaseChannel): Promise<VersionListResponse> {
    const params = new URLSearchParams({ skip: String(skip), limit: String(limit) });
    if (channel) params.set('channel', channel);
    return this.fetch(`/v1/addons/${slug}/versions?${params}`);
  }

  async getVersion(slug: string, version: string): Promise<Version> {
    return this.fetch(`/v1/addons/${slug}/versions/${version}`);
  }

  async getLatestVersion(slug: string): Promise<Version> {
    return this.fetch(`/v1/addons/${slug}/versions/latest`);
  }

  async createVersion(slug: string, data: VersionCreate): Promise<Version> {
    return this.fetch(`/v1/addons/${slug}/versions`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateVersion(slug: string, version: string, data: VersionUpdate): Promise<Version> {
    return this.fetch(`/v1/addons/${slug}/versions/${version}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteVersion(slug: string, version: string): Promise<void> {
    return this.fetch(`/v1/addons/${slug}/versions/${version}`, { method: 'DELETE' });
  }

  async deprecateVersion(slug: string, version: string, reason: string): Promise<Version> {
    return this.fetch(`/v1/addons/${slug}/versions/${version}/deprecate`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    });
  }

  async undeprecateVersion(slug: string, version: string): Promise<Version> {
    return this.fetch(`/v1/addons/${slug}/versions/${version}/undeprecate`, {
      method: 'POST',
    });
  }

  async rollbackToVersion(slug: string, version: string): Promise<Version> {
    return this.fetch(`/v1/addons/${slug}/versions/${version}/rollback`, {
      method: 'POST',
    });
  }

  // Payments
  async getPlans(): Promise<{ plans: PaymentPlan[] }> {
    return this.fetch('/v1/payments/plans');
  }

  async createStripeCheckout(tier: 'pro' | 'premium'): Promise<{ checkout_url: string; session_id: string }> {
    return this.fetch('/v1/payments/stripe/create-checkout', {
      method: 'POST',
      body: JSON.stringify({ tier, provider: 'stripe' }),
    });
  }

  async createStripePortal(): Promise<{ portal_url: string }> {
    return this.fetch('/v1/payments/stripe/create-portal', { method: 'POST' });
  }

  async getPayPalSubscriptionDetails(tier: 'pro' | 'premium'): Promise<{ plan_id: string; custom_id: string }> {
    return this.fetch('/v1/payments/paypal/subscription-details', {
      method: 'POST',
      body: JSON.stringify({ tier, provider: 'paypal' }),
    });
  }

  async activatePayPalSubscription(subscriptionId: string): Promise<{ status: string; tier: string }> {
    return this.fetch(`/v1/payments/paypal/activate?subscription_id=${subscriptionId}`, {
      method: 'POST',
    });
  }

  // Admin
  async getAdminStats(): Promise<AdminStats> {
    return this.fetch('/v1/admin/stats');
  }

  async listUsers(page = 1, perPage = 50, search?: string, tier?: string, isAdmin?: boolean): Promise<{
    users: User[];
    total: number;
    page: number;
    per_page: number;
  }> {
    const params = new URLSearchParams({ page: String(page), per_page: String(perPage) });
    if (search) params.append('search', search);
    if (tier) params.append('tier', tier);
    if (isAdmin !== undefined) params.append('is_admin', String(isAdmin));
    return this.fetch(`/v1/admin/users?${params}`);
  }

  async getUser(userId: number): Promise<User> {
    return this.fetch(`/v1/admin/users/${userId}`);
  }

  async updateUser(userId: number, data: { is_admin?: boolean; subscription_tier?: string; storage_quota_bytes?: number }): Promise<User> {
    return this.fetch(`/v1/admin/users/${userId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async promoteToAdmin(userId: number): Promise<{ status: string }> {
    return this.fetch(`/v1/admin/users/${userId}/promote`, { method: 'POST' });
  }

  async demoteFromAdmin(userId: number): Promise<{ status: string }> {
    return this.fetch(`/v1/admin/users/${userId}/demote`, { method: 'POST' });
  }

  async grantTempTier(userId: number, tier: string, days: number, reason?: string): Promise<{ status: string; temp_tier: string; expires_at: string; days: number }> {
    return this.fetch(`/v1/admin/users/${userId}/grant-temp-tier`, {
      method: 'POST',
      body: JSON.stringify({ tier, days, reason }),
    });
  }

  async revokeTempTier(userId: number): Promise<{ status: string; revoked_tier: string }> {
    return this.fetch(`/v1/admin/users/${userId}/revoke-temp-tier`, { method: 'POST' });
  }

  async getUserBadges(userId: number): Promise<{ user_id: number; badges: string[] }> {
    return this.fetch(`/v1/admin/users/${userId}/badges`);
  }

  async addUserBadge(userId: number, badge: string): Promise<{ status: string; badges: string[] }> {
    return this.fetch(`/v1/admin/users/${userId}/badges?badge=${encodeURIComponent(badge)}`, { method: 'POST' });
  }

  async removeUserBadge(userId: number, badge: string): Promise<{ status: string; badges: string[] }> {
    return this.fetch(`/v1/admin/users/${userId}/badges?badge=${encodeURIComponent(badge)}`, { method: 'DELETE' });
  }

  async setVerifiedDeveloper(userId: number, verified: boolean): Promise<{ status: string; is_verified_developer: boolean }> {
    return this.fetch(`/v1/admin/users/${userId}/verified-developer?verified=${verified}`, { method: 'PATCH' });
  }

  async listAllAddons(page = 1, perPage = 50, search?: string): Promise<AddonListResponse> {
    const params = new URLSearchParams({ page: String(page), per_page: String(perPage) });
    if (search) params.append('search', search);
    return this.fetch(`/v1/admin/addons?${params}`);
  }

  async adminGetAddon(addonId: number): Promise<{ addon: Addon; versions: Version[] }> {
    return this.fetch(`/v1/admin/addons/${addonId}`);
  }

  async adminUpdateAddon(addonId: number, data: AddonUpdate): Promise<Addon> {
    return this.fetch(`/v1/admin/addons/${addonId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async adminDeleteAddon(addonId: number): Promise<{ status: string }> {
    return this.fetch(`/v1/admin/addons/${addonId}`, { method: 'DELETE' });
  }

  async adminUpdateVersion(addonId: number, versionId: number, data: VersionUpdate): Promise<Version> {
    return this.fetch(`/v1/admin/addons/${addonId}/versions/${versionId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async adminDeleteVersion(addonId: number, versionId: number): Promise<{ status: string }> {
    return this.fetch(`/v1/admin/addons/${addonId}/versions/${versionId}`, { method: 'DELETE' });
  }

  async getAuditLog(page = 1, perPage = 50): Promise<{
    entries: AuditLogEntry[];
    total: number;
    page: number;
    per_page: number;
  }> {
    const params = new URLSearchParams({ page: String(page), per_page: String(perPage) });
    return this.fetch(`/v1/admin/audit-log?${params}`);
  }

  async cleanupAuditLog(): Promise<{ status: string; deleted_count: number }> {
    return this.fetch('/v1/admin/audit-log/cleanup', { method: 'POST' });
  }

  // ============== TICKETS ==============

  // User ticket methods
  async listMyTickets(page = 1, perPage = 20, status?: TicketStatus): Promise<TicketListResponse> {
    const params = new URLSearchParams({ page: String(page), per_page: String(perPage) });
    if (status) params.append('status', status);
    return this.fetch(`/v1/tickets?${params}`);
  }

  async getTicket(ticketId: number): Promise<TicketDetail> {
    return this.fetch(`/v1/tickets/${ticketId}`);
  }

  async createTicket(data: TicketCreate): Promise<TicketDetail> {
    return this.fetch('/v1/tickets', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async addTicketMessage(ticketId: number, content: string): Promise<TicketMessage> {
    return this.fetch(`/v1/tickets/${ticketId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    });
  }

  async uploadTicketAttachment(ticketId: number, messageId: number, file: File): Promise<TicketAttachment> {
    const formData = new FormData();
    formData.append('file', file);
    
    const headers: HeadersInit = {};
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${API_BASE}/v1/tickets/${ticketId}/messages/${messageId}/attachments`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(error.detail);
    }

    return response.json();
  }

  async downloadAttachment(ticketId: number, attachmentId: number): Promise<Blob> {
    const headers: HeadersInit = {};
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${API_BASE}/v1/tickets/${ticketId}/attachments/${attachmentId}/download`, {
      headers,
    });

    if (!response.ok) {
      throw new Error('Download failed');
    }

    return response.blob();
  }

  async closeTicket(ticketId: number): Promise<Ticket> {
    return this.fetch(`/v1/tickets/${ticketId}/close`, { method: 'POST' });
  }

  async reopenTicket(ticketId: number): Promise<Ticket> {
    return this.fetch(`/v1/tickets/${ticketId}/reopen`, { method: 'POST' });
  }

  // Admin ticket methods
  async getTicketStats(): Promise<TicketStats> {
    return this.fetch('/v1/admin/tickets/stats');
  }

  async listAllTickets(
    page = 1, 
    perPage = 50, 
    status?: TicketStatus,
    priority?: TicketPriority,
    category?: TicketCategory,
    assignedToMe?: boolean,
    unassigned?: boolean
  ): Promise<TicketListResponse> {
    const params = new URLSearchParams({ page: String(page), per_page: String(perPage) });
    if (status) params.append('status', status);
    if (priority) params.append('priority', priority);
    if (category) params.append('category', category);
    if (assignedToMe) params.append('assigned_to_me', 'true');
    if (unassigned) params.append('unassigned', 'true');
    return this.fetch(`/v1/admin/tickets?${params}`);
  }

  async adminGetTicket(ticketId: number): Promise<TicketDetail> {
    return this.fetch(`/v1/admin/tickets/${ticketId}`);
  }

  async adminAddTicketMessage(ticketId: number, content: string): Promise<TicketMessage> {
    return this.fetch(`/v1/admin/tickets/${ticketId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    });
  }

  async updateTicketStatus(ticketId: number, status: TicketStatus): Promise<Ticket> {
    return this.fetch(`/v1/admin/tickets/${ticketId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    });
  }

  async updateTicketPriority(ticketId: number, priority: TicketPriority): Promise<Ticket> {
    return this.fetch(`/v1/admin/tickets/${ticketId}/priority`, {
      method: 'PATCH',
      body: JSON.stringify({ priority }),
    });
  }

  async assignTicket(ticketId: number, adminId: number): Promise<Ticket> {
    return this.fetch(`/v1/admin/tickets/${ticketId}/assign`, {
      method: 'PATCH',
      body: JSON.stringify({ admin_id: adminId }),
    });
  }

  async assignTicketToMe(ticketId: number): Promise<Ticket> {
    return this.fetch(`/v1/admin/tickets/${ticketId}/assign-to-me`, { method: 'POST' });
  }

  // Canned responses
  async listCannedResponses(category?: TicketCategory, includeInactive?: boolean): Promise<CannedResponseListResponse> {
    const params = new URLSearchParams();
    if (category) params.append('category', category);
    if (includeInactive) params.append('include_inactive', 'true');
    return this.fetch(`/v1/admin/canned-responses?${params}`);
  }

  async createCannedResponse(data: { title: string; content: string; category?: TicketCategory }): Promise<CannedResponse> {
    return this.fetch('/v1/admin/canned-responses', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateCannedResponse(id: number, data: { title?: string; content?: string; category?: TicketCategory; is_active?: boolean }): Promise<CannedResponse> {
    return this.fetch(`/v1/admin/canned-responses/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteCannedResponse(id: number): Promise<{ status: string }> {
    return this.fetch(`/v1/admin/canned-responses/${id}`, { method: 'DELETE' });
  }

  async useCannedResponse(id: number): Promise<CannedResponse> {
    return this.fetch(`/v1/admin/canned-responses/${id}/use`);
  }

  // ============== PROFILES ==============

  async listPublicUsers(page = 1, perPage = 24, search?: string): Promise<{
    users: Array<{
      discord_id: string;
      discord_username: string;
      discord_avatar: string | null;
      subscription_tier: string;
      profile_slug: string | null;
      badges: string[];
      bio: string | null;
      is_verified_developer: boolean;
      addon_count: number;
      created_at: string;
    }>;
    total: number;
    page: number;
    per_page: number;
  }> {
    const params = new URLSearchParams({ page: String(page), per_page: String(perPage) });
    if (search) params.append('search', search);
    return this.fetch(`/v1/u?${params}`);
  }

  async getPublicProfile(identifier: string): Promise<UserPublicProfile> {
    return this.fetch(`/v1/u/${identifier}`);
  }

  async updateMyProfile(data: UserProfileUpdate): Promise<User> {
    return this.fetch('/v1/users/me/profile', {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  // ============== API KEYS ==============

  // Legacy single-key methods (kept for backwards compatibility)
  async getMyApiKey(): Promise<ApiKeyInfo> {
    return this.fetch('/v1/users/me/api-key');
  }

  async createMyApiKey(): Promise<ApiKeyCreated> {
    return this.fetch('/v1/users/me/api-key', { method: 'POST' });
  }

  async revokeMyApiKey(): Promise<void> {
    return this.fetch('/v1/users/me/api-key', { method: 'DELETE' });
  }

  // New multi-key API
  async listApiKeys(): Promise<{
    keys: Array<{
      id: number;
      name: string;
      key_prefix: string;
      scopes: string[];
      is_active: boolean;
      expires_at: string | null;
      last_used_at: string | null;
      usage_count: number;
      created_at: string;
    }>;
    count: number;
    max_keys: number;
  }> {
    return this.fetch('/v1/api-keys');
  }

  async getAvailableScopes(): Promise<{
    scopes: Array<{
      scope: string;
      name: string;
      description: string;
      min_tier: string;
    }>;
    tier: string;
    max_keys: number;
  }> {
    return this.fetch('/v1/api-keys/scopes');
  }

  async createApiKey(data: {
    name: string;
    scopes: string[];
    expires_at?: string;
  }): Promise<{
    key: {
      id: number;
      name: string;
      key_prefix: string;
      scopes: string[];
      is_active: boolean;
      expires_at: string | null;
      last_used_at: string | null;
      usage_count: number;
      created_at: string;
    };
    api_key: string;
    warning: string;
  }> {
    return this.fetch('/v1/api-keys', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getApiKey(keyId: number): Promise<{
    id: number;
    name: string;
    key_prefix: string;
    scopes: string[];
    is_active: boolean;
    expires_at: string | null;
    last_used_at: string | null;
    usage_count: number;
    created_at: string;
  }> {
    return this.fetch(`/v1/api-keys/${keyId}`);
  }

  async updateApiKey(keyId: number, data: {
    name?: string;
    scopes?: string[];
    expires_at?: string;
  }): Promise<{
    id: number;
    name: string;
    key_prefix: string;
    scopes: string[];
    is_active: boolean;
    expires_at: string | null;
    last_used_at: string | null;
    usage_count: number;
    created_at: string;
  }> {
    return this.fetch(`/v1/api-keys/${keyId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async revokeApiKey(keyId: number): Promise<void> {
    return this.fetch(`/v1/api-keys/${keyId}/revoke`, { method: 'POST' });
  }

  async deleteApiKey(keyId: number): Promise<void> {
    return this.fetch(`/v1/api-keys/${keyId}`, { method: 'DELETE' });
  }

  // ============== ANALYTICS ==============

  async getAnalyticsSummary(days?: number): Promise<AnalyticsSummary> {
    const params = days ? `?days=${days}` : '';
    return this.fetch(`/v1/analytics/summary${params}`);
  }

  async getAddonAnalytics(addonId: number, days?: number): Promise<AddonAnalytics> {
    const params = days ? `?days=${days}` : '';
    return this.fetch(`/v1/analytics/addons/${addonId}${params}`);
  }

  async exportAddonAnalytics(addonId: number, format: 'csv' | 'json', days?: number): Promise<Blob> {
    const params = new URLSearchParams({ format });
    if (days) params.set('days', String(days));
    const headers: HeadersInit = {};
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    const response = await fetch(`${API_BASE}/v1/analytics/addons/${addonId}/export?${params}`, {
      headers,
    });
    if (!response.ok) throw new Error('Export failed');
    return response.blob();
  }

  async getApiUsageAnalytics(days?: number): Promise<ApiUsageAnalytics> {
    const params = days ? `?days=${days}` : '';
    return this.fetch(`/v1/analytics/api-usage${params}`);
  }

  // ============== COLLABORATORS ==============

  async listCollaborators(addonId: number): Promise<Collaborator[]> {
    return this.fetch(`/v1/addons/${addonId}/collaborators`);
  }

  async inviteCollaborator(addonId: number, userId: number, role: CollaboratorRole): Promise<Collaborator> {
    return this.fetch(`/v1/addons/${addonId}/collaborators`, {
      method: 'POST',
      body: JSON.stringify({ user_id: userId, role }),
    });
  }

  async updateCollaborator(addonId: number, collaboratorId: number, role: CollaboratorRole): Promise<Collaborator> {
    return this.fetch(`/v1/addons/${addonId}/collaborators/${collaboratorId}`, {
      method: 'PATCH',
      body: JSON.stringify({ role }),
    });
  }

  async removeCollaborator(addonId: number, collaboratorId: number): Promise<void> {
    return this.fetch(`/v1/addons/${addonId}/collaborators/${collaboratorId}`, { method: 'DELETE' });
  }

  async transferOwnership(addonId: number, newOwnerId: number): Promise<{ message: string }> {
    return this.fetch(`/v1/addons/${addonId}/transfer`, {
      method: 'POST',
      body: JSON.stringify({ new_owner_id: newOwnerId }),
    });
  }

  async getMyInvitations(): Promise<CollaborationInvitation[]> {
    return this.fetch('/v1/collaborations/invitations');
  }

  async acceptInvitation(collaboratorId: number): Promise<{ message: string }> {
    return this.fetch(`/v1/collaborations/invitations/${collaboratorId}/accept`, { method: 'POST' });
  }

  async declineInvitation(collaboratorId: number): Promise<{ message: string }> {
    return this.fetch(`/v1/collaborations/invitations/${collaboratorId}`, { method: 'DELETE' });
  }

  // ============== WEBHOOKS ==============

  async getMyWebhook(): Promise<WebhookConfig> {
    return this.fetch('/v1/users/me/webhook');
  }

  async updateMyWebhook(data: WebhookUpdate): Promise<WebhookConfig> {
    return this.fetch('/v1/users/me/webhook', {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async regenerateWebhookSecret(): Promise<{ secret: string }> {
    return this.fetch('/v1/users/me/webhook/secret', { method: 'POST' });
  }

  async testMyWebhook(): Promise<WebhookTestResponse> {
    return this.fetch('/v1/users/me/webhook/test', { method: 'POST' });
  }

  async deleteMyWebhook(): Promise<void> {
    return this.fetch('/v1/users/me/webhook', { method: 'DELETE' });
  }

  // ============== ORGANIZATIONS (Premium) ==============

  async listMyOrganizations(): Promise<{ organizations: Organization[]; total: number }> {
    return this.fetch('/v1/organizations');
  }

  async getOrganization(orgSlug: string): Promise<OrganizationDetail> {
    return this.fetch(`/v1/organizations/${orgSlug}`);
  }

  async createOrganization(data: OrganizationCreate): Promise<Organization> {
    return this.fetch('/v1/organizations', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateOrganization(orgSlug: string, data: OrganizationUpdate): Promise<Organization> {
    return this.fetch(`/v1/organizations/${orgSlug}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteOrganization(orgSlug: string): Promise<void> {
    return this.fetch(`/v1/organizations/${orgSlug}`, { method: 'DELETE' });
  }

  async inviteOrganizationMember(orgSlug: string, discordUsername: string, role: OrganizationRole = 'member'): Promise<OrganizationMember> {
    return this.fetch(`/v1/organizations/${orgSlug}/members`, {
      method: 'POST',
      body: JSON.stringify({ discord_username: discordUsername, role }),
    });
  }

  async updateOrganizationMemberRole(orgSlug: string, userId: number, role: OrganizationRole): Promise<OrganizationMember> {
    return this.fetch(`/v1/organizations/${orgSlug}/members/${userId}`, {
      method: 'PATCH',
      body: JSON.stringify({ role }),
    });
  }

  async removeOrganizationMember(orgSlug: string, userId: number): Promise<void> {
    return this.fetch(`/v1/organizations/${orgSlug}/members/${userId}`, { method: 'DELETE' });
  }

  async updateMemberPermissions(orgSlug: string, userId: number, permissions: Record<string, boolean>): Promise<OrganizationMember> {
    return this.fetch(`/v1/organizations/${orgSlug}/members/${userId}/permissions`, {
      method: 'PUT',
      body: JSON.stringify({ permissions }),
    });
  }

  // Organization Audit Logs
  async getOrgAuditLogs(orgSlug: string, page = 1, perPage = 50): Promise<OrgAuditLogListResponse> {
    return this.fetch(`/v1/organizations/${orgSlug}/audit-logs?page=${page}&per_page=${perPage}`);
  }

  // Organization API Keys
  async createOrgApiKey(orgSlug: string, data: { name: string; scopes?: string[]; expires_at?: string }): Promise<OrgApiKeyCreateResponse> {
    return this.fetch(`/v1/organizations/${orgSlug}/api-keys`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async listOrgApiKeys(orgSlug: string): Promise<OrgApiKeyListResponse> {
    return this.fetch(`/v1/organizations/${orgSlug}/api-keys`);
  }

  async deleteOrgApiKey(orgSlug: string, keyId: number): Promise<void> {
    return this.fetch(`/v1/organizations/${orgSlug}/api-keys/${keyId}`, { method: 'DELETE' });
  }

  // Organization Analytics
  async getOrgAnalytics(orgSlug: string): Promise<OrgAnalyticsSummary> {
    return this.fetch(`/v1/organizations/${orgSlug}/analytics`);
  }

  // Public Organization Page
  async getPublicOrgPage(orgSlug: string): Promise<OrgPublicPage> {
    return this.fetch(`/v1/organizations/public/${orgSlug}`);
  }

  // Notifications
  async getNotifications(page = 1, perPage = 20, unreadOnly = false): Promise<NotificationListResponse> {
    const params = new URLSearchParams({ page: String(page), per_page: String(perPage) });
    if (unreadOnly) params.set('unread_only', 'true');
    return this.fetch(`/v1/notifications?${params}`);
  }

  async getUnreadNotificationCount(): Promise<{ unread_count: number }> {
    return this.fetch('/v1/notifications/unread-count');
  }

  async markNotificationRead(id: number): Promise<void> {
    return this.fetch(`/v1/notifications/${id}/read`, { method: 'POST' });
  }

  async markAllNotificationsRead(): Promise<void> {
    return this.fetch('/v1/notifications/read-all', { method: 'POST' });
  }

  async deleteNotification(id: number): Promise<void> {
    return this.fetch(`/v1/notifications/${id}`, { method: 'DELETE' });
  }

  // ============== Marketplace & Sponsorship (Premium Feature) ==============

  async updateAddonPricing(addonId: number, data: { is_paid?: boolean; price_cents?: number; revenue_split_percent?: number }): Promise<Addon> {
    return this.fetch(`/v1/marketplace/addons/${addonId}/pricing`, { method: 'PUT', body: JSON.stringify(data) });
  }

  async purchaseAddon(addonId: number, serverId?: string): Promise<PurchaseAddonResponse> {
    return this.fetch(`/v1/marketplace/addons/${addonId}/purchase`, {
      method: 'POST',
      body: JSON.stringify({ server_id: serverId }),
    });
  }

  async listAddonLicenses(addonId: number, skip = 0, limit = 50): Promise<LicenseListResponse> {
    return this.fetch(`/v1/marketplace/addons/${addonId}/licenses?skip=${skip}&limit=${limit}`);
  }

  async listMyLicenses(skip = 0, limit = 50): Promise<LicenseListResponse> {
    return this.fetch(`/v1/marketplace/my-licenses?skip=${skip}&limit=${limit}`);
  }

  async revokeLicense(licenseId: number): Promise<AddonLicense> {
    return this.fetch(`/v1/marketplace/licenses/${licenseId}/revoke`, { method: 'POST' });
  }

  async verifyLicense(licenseKey: string, serverId?: string): Promise<LicenseVerifyResponse> {
    return this.fetch('/v1/marketplace/verify-license', {
      method: 'POST',
      body: JSON.stringify({ license_key: licenseKey, server_id: serverId }),
    });
  }

  async getRevenueStats(addonId: number): Promise<RevenueStats> {
    return this.fetch(`/v1/marketplace/addons/${addonId}/revenue`);
  }

  async getStripeConnectStatus(): Promise<StripeConnectStatus> {
    return this.fetch('/v1/stripe-connect/status');
  }

  async startStripeConnectOnboarding(returnUrl: string, refreshUrl: string): Promise<{ onboarding_url: string }> {
    return this.fetch('/v1/stripe-connect/onboard', {
      method: 'POST',
      body: JSON.stringify({ return_url: returnUrl, refresh_url: refreshUrl }),
    });
  }

  async getSponsorUrl(addonId: number): Promise<{ sponsor_url: string | null }> {
    return this.fetch(`/v1/addons/${addonId}/sponsorship`);
  }

  async updateSponsorUrl(addonId: number, sponsorUrl: string | null): Promise<{ sponsor_url: string | null }> {
    return this.fetch(`/v1/addons/${addonId}/sponsorship`, {
      method: 'PUT',
      body: JSON.stringify({ sponsor_url: sponsorUrl }),
    });
  }

  // ============== Premium Analytics (PREM-15 through 19) ==============

  // Self-Hosted Config (PREM-15)
  async getSelfHostedConfig(addonId: number): Promise<SelfHostedConfig> {
    return this.fetch(`/v1/addons/${addonId}/self-hosted`);
  }

  async createSelfHostedConfig(addonId: number, data: Record<string, unknown>): Promise<SelfHostedConfig> {
    return this.fetch(`/v1/addons/${addonId}/self-hosted`, { method: 'POST', body: JSON.stringify(data) });
  }

  async updateSelfHostedConfig(addonId: number, data: Record<string, unknown>): Promise<SelfHostedConfig> {
    return this.fetch(`/v1/addons/${addonId}/self-hosted`, { method: 'PUT', body: JSON.stringify(data) });
  }

  async deleteSelfHostedConfig(addonId: number): Promise<void> {
    return this.fetch(`/v1/addons/${addonId}/self-hosted`, { method: 'DELETE' });
  }

  async verifySelfHostedDomain(addonId: number): Promise<{ verified: boolean; instructions: string }> {
    return this.fetch(`/v1/addons/${addonId}/self-hosted/verify-domain`, { method: 'POST' });
  }

  // Analytics Alerts (PREM-17)
  async listAlerts(addonId: number): Promise<{ alerts: AnalyticsAlert[] }> {
    return this.fetch(`/v1/addons/${addonId}/alerts`);
  }

  async createAlert(addonId: number, data: Record<string, unknown>): Promise<AnalyticsAlert> {
    return this.fetch(`/v1/addons/${addonId}/alerts`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateAlert(addonId: number, alertId: number, data: Record<string, unknown>): Promise<AnalyticsAlert> {
    return this.fetch(`/v1/addons/${addonId}/alerts/${alertId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteAlert(addonId: number, alertId: number): Promise<void> {
    return this.fetch(`/v1/addons/${addonId}/alerts/${alertId}`, { method: 'DELETE' });
  }

  async testAlert(addonId: number, alertId: number): Promise<{ success: boolean }> {
    return this.fetch(`/v1/addons/${addonId}/alerts/${alertId}/test`, { method: 'POST' });
  }

  // Cohort Analysis (PREM-18)
  async getCohortAnalysis(addonId: number, days = 30, fromVersion?: string, toVersion?: string): Promise<CohortAnalysisResponse> {
    const params = new URLSearchParams({ days: String(days) });
    if (fromVersion) params.set('from_version', fromVersion);
    if (toVersion) params.set('to_version', toVersion);
    return this.fetch(`/v1/addons/${addonId}/cohorts?${params}`);
  }

  // Predictive Analytics (PREM-19)
  async getPredictiveAnalytics(addonId: number, targetVersion: string, days = 14): Promise<PredictiveEstimate> {
    const params = new URLSearchParams({ target_version: targetVersion, days: String(days) });
    return this.fetch(`/v1/addons/${addonId}/predictive?${params}`);
  }

  // Real-Time Analytics (PREM-16)
  async getRealtimeStats(addonId: number): Promise<RealtimeStats> {
    return this.fetch(`/v1/addons/${addonId}/realtime`);
  }

  async getRecentChecks(addonId: number, limit = 50): Promise<{ checks: RecentCheck[] }> {
    return this.fetch(`/v1/addons/${addonId}/realtime/recent?limit=${limit}`);
  }

  async getHourlyBreakdown(addonId: number, hours = 24): Promise<{ hourly: HourlyBreakdown[] }> {
    return this.fetch(`/v1/addons/${addonId}/realtime/hourly?hours=${hours}`);
  }

  // ============== Code Signing (PREM-5) ==============

  async listSigningKeys(addonId: number): Promise<import('../types').SigningKeyListResponse> {
    return this.fetch(`/v1/addons/${addonId}/signing-keys`);
  }

  async createSigningKey(addonId: number, data: import('../types').SigningKeyCreate): Promise<import('../types').SigningKey> {
    return this.fetch(`/v1/addons/${addonId}/signing-keys`, { method: 'POST', body: JSON.stringify(data) });
  }

  async revokeSigningKey(addonId: number, keyId: number): Promise<void> {
    return this.fetch(`/v1/addons/${addonId}/signing-keys/${keyId}`, { method: 'DELETE' });
  }

  async listVersionSignatures(versionId: number): Promise<import('../types').VersionSignature[]> {
    return this.fetch(`/v1/versions/${versionId}/signatures`);
  }

  async createVersionSignature(versionId: number, data: { signing_key_id: number; signature: string; signed_hash: string }): Promise<import('../types').VersionSignature> {
    return this.fetch(`/v1/versions/${versionId}/signatures`, { method: 'POST', body: JSON.stringify(data) });
  }

  // ============== Vulnerability Scanning (PREM-6) ==============

  async initiateScan(versionId: number): Promise<import('../types').VulnerabilityScan> {
    return this.fetch(`/v1/versions/${versionId}/scans`, { method: 'POST' });
  }

  async listScans(versionId: number): Promise<import('../types').VulnerabilityScanListResponse> {
    return this.fetch(`/v1/versions/${versionId}/scans`);
  }

  async getScan(versionId: number, scanId: number): Promise<import('../types').VulnerabilityScan> {
    return this.fetch(`/v1/versions/${versionId}/scans/${scanId}`);
  }

  // ============== SBOM (PREM-7) ==============

  async uploadSBOM(versionId: number, data: { format: string; raw_content: string }): Promise<import('../types').SBOMEntry> {
    return this.fetch(`/v1/versions/${versionId}/sbom`, { method: 'POST', body: JSON.stringify(data) });
  }

  async listSBOMs(versionId: number): Promise<import('../types').SBOMListResponse> {
    return this.fetch(`/v1/versions/${versionId}/sbom`);
  }

  // ============== IP Allowlist (PREM-8) ==============

  async getIPAllowlist(keyId: number): Promise<{ ip_allowlist: string[] | null }> {
    return this.fetch(`/v1/api-keys/${keyId}/ip-allowlist`);
  }

  async updateIPAllowlist(keyId: number, ipAllowlist: string[] | null): Promise<{ ip_allowlist: string[] | null }> {
    return this.fetch(`/v1/api-keys/${keyId}/ip-allowlist`, { method: 'PUT', body: JSON.stringify({ ip_allowlist: ipAllowlist }) });
  }

  // ============== 2FA (PREM-9) ==============

  async create2FAChallenge(action: string): Promise<import('../types').TwoFactorChallengeResponse> {
    return this.fetch('/v1/security/2fa/challenge', { method: 'POST', body: JSON.stringify({ action }) });
  }

  async verify2FAChallenge(challengeId: number, code: string): Promise<import('../types').TwoFactorVerifyResponse> {
    return this.fetch('/v1/security/2fa/verify', { method: 'POST', body: JSON.stringify({ challenge_id: challengeId, code }) });
  }

  // ============== Staged Rollouts ==============

  async listRollouts(addonId: number, status?: string): Promise<import('../types').StagedRolloutListResponse> {
    const params = status ? `?status_filter=${status}` : '';
    return this.fetch(`/v1/addons/${addonId}/rollouts${params}`);
  }

  async createRollout(addonId: number, data: import('../types').StagedRolloutCreate): Promise<import('../types').StagedRollout> {
    return this.fetch(`/v1/addons/${addonId}/rollouts`, { method: 'POST', body: JSON.stringify(data) });
  }

  async getRollout(addonId: number, rolloutId: number): Promise<import('../types').StagedRollout> {
    return this.fetch(`/v1/addons/${addonId}/rollouts/${rolloutId}`);
  }

  async updateRollout(addonId: number, rolloutId: number, data: import('../types').StagedRolloutUpdate): Promise<import('../types').StagedRollout> {
    return this.fetch(`/v1/addons/${addonId}/rollouts/${rolloutId}`, { method: 'PATCH', body: JSON.stringify(data) });
  }

  async activateRollout(addonId: number, rolloutId: number): Promise<import('../types').StagedRollout> {
    return this.fetch(`/v1/addons/${addonId}/rollouts/${rolloutId}/activate`, { method: 'POST' });
  }

  async promoteRollout(addonId: number, rolloutId: number, targetStage?: string): Promise<import('../types').StagedRollout> {
    const body = targetStage ? JSON.stringify({ target_stage: targetStage }) : '{}';
    return this.fetch(`/v1/addons/${addonId}/rollouts/${rolloutId}/promote`, { method: 'POST', body });
  }

  async pauseRollout(addonId: number, rolloutId: number): Promise<import('../types').StagedRollout> {
    return this.fetch(`/v1/addons/${addonId}/rollouts/${rolloutId}/pause`, { method: 'POST' });
  }

  async cancelRollout(addonId: number, rolloutId: number): Promise<import('../types').StagedRollout> {
    return this.fetch(`/v1/addons/${addonId}/rollouts/${rolloutId}/cancel`, { method: 'POST' });
  }

  // ============== Feature Flags ==============

  async listFlags(addonId: number): Promise<import('../types').FeatureFlagListResponse> {
    return this.fetch(`/v1/addons/${addonId}/flags`);
  }

  async createFlag(addonId: number, data: import('../types').FeatureFlagCreate): Promise<import('../types').FeatureFlag> {
    return this.fetch(`/v1/addons/${addonId}/flags`, { method: 'POST', body: JSON.stringify(data) });
  }

  async updateFlag(addonId: number, flagId: number, data: import('../types').FeatureFlagUpdate): Promise<import('../types').FeatureFlag> {
    return this.fetch(`/v1/addons/${addonId}/flags/${flagId}`, { method: 'PATCH', body: JSON.stringify(data) });
  }

  async deleteFlag(addonId: number, flagId: number): Promise<void> {
    return this.fetch(`/v1/addons/${addonId}/flags/${flagId}`, { method: 'DELETE' });
  }

  // ============== Webhook Endpoints (Premium) ==============

  async listWebhookEndpoints(): Promise<WebhookEndpoint[]> {
    return this.fetch('/v1/webhooks/endpoints');
  }

  async createWebhookEndpoint(data: WebhookEndpointCreate): Promise<WebhookEndpoint> {
    return this.fetch('/v1/webhooks/endpoints', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateWebhookEndpoint(id: number, data: WebhookEndpointUpdate): Promise<WebhookEndpoint> {
    return this.fetch(`/v1/webhooks/endpoints/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteWebhookEndpoint(id: number): Promise<void> {
    return this.fetch(`/v1/webhooks/endpoints/${id}`, { method: 'DELETE' });
  }

  async rotateWebhookEndpointSecret(id: number): Promise<{ secret: string }> {
    return this.fetch(`/v1/webhooks/endpoints/${id}/rotate-secret`, { method: 'POST' });
  }

  async testWebhookEndpoint(id: number): Promise<{ success: boolean; status_code?: number; error?: string }> {
    return this.fetch(`/v1/webhooks/endpoints/${id}/test`, { method: 'POST' });
  }

  async getWebhookDeliveries(endpointId: number, page = 1, perPage = 20): Promise<WebhookDelivery[]> {
    const params = new URLSearchParams({ page: String(page), per_page: String(perPage) });
    return this.fetch(`/v1/webhooks/endpoints/${endpointId}/deliveries?${params}`);
  }

  async retryWebhookDelivery(deliveryId: number): Promise<{ success: boolean; status_code?: number; error?: string }> {
    return this.fetch(`/v1/webhooks/deliveries/${deliveryId}/retry`, { method: 'POST' });
  }
}

export const api = new ApiClient();
