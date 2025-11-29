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

  async listAllAddons(page = 1, perPage = 50, search?: string): Promise<AddonListResponse> {
    const params = new URLSearchParams({ page: String(page), per_page: String(perPage) });
    if (search) params.append('search', search);
    return this.fetch(`/v1/admin/addons?${params}`);
  }

  async adminDeleteAddon(addonId: number): Promise<{ status: string }> {
    return this.fetch(`/v1/admin/addons/${addonId}`, { method: 'DELETE' });
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
}

export const api = new ApiClient();
