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
} from '../types';

const API_BASE = import.meta.env.VITE_API_URL || '/api';

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
  async listAddons(page = 1, perPage = 20, search?: string): Promise<AddonListResponse> {
    const params = new URLSearchParams({ page: String(page), per_page: String(perPage) });
    if (search) params.append('search', search);
    return this.fetch(`/v1/addons?${params}`);
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

  // Versions
  async listVersions(slug: string, skip = 0, limit = 50): Promise<VersionListResponse> {
    const params = new URLSearchParams({ skip: String(skip), limit: String(limit) });
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

  async getMyApiKey(): Promise<ApiKeyInfo> {
    return this.fetch('/v1/users/me/api-key');
  }

  async createMyApiKey(): Promise<ApiKeyCreated> {
    return this.fetch('/v1/users/me/api-key', { method: 'POST' });
  }

  async revokeMyApiKey(): Promise<void> {
    return this.fetch('/v1/users/me/api-key', { method: 'DELETE' });
  }

  // ============== ANALYTICS ==============

  async getAnalyticsSummary(): Promise<AnalyticsSummary> {
    return this.fetch('/v1/analytics/summary');
  }

  async getAddonAnalytics(addonId: number): Promise<AddonAnalytics> {
    return this.fetch(`/v1/analytics/addons/${addonId}`);
  }
}

export const api = new ApiClient();
