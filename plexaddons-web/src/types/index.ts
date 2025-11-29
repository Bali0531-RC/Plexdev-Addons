// API Types

export interface User {
  id: number;
  discord_id: string;
  discord_username: string;
  discord_avatar: string | null;
  email: string | null;
  subscription_tier: 'free' | 'pro' | 'premium';
  storage_used_bytes: number;
  storage_quota_bytes: number;
  is_admin: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface Addon {
  id: number;
  slug: string;
  name: string;
  description: string | null;
  homepage: string | null;
  external: boolean;
  is_active: boolean;
  is_public: boolean;
  owner_id: number;
  owner_username: string | null;
  latest_version: string | null;
  latest_release_date: string | null;
  version_count: number;
  created_at: string;
  updated_at: string;
}

export interface Version {
  id: number;
  addon_id: number;
  version: string;
  release_date: string;
  download_url: string;
  description: string | null;
  changelog_url: string | null;
  changelog_content: string | null;
  breaking: boolean;
  urgent: boolean;
  storage_size_bytes: number;
  created_at: string;
}

export interface Subscription {
  id: number;
  provider: 'stripe' | 'paypal';
  tier: 'pro' | 'premium';
  status: 'active' | 'past_due' | 'canceled' | 'unpaid' | 'trialing' | 'paused' | 'incomplete';
  current_period_start: string | null;
  current_period_end: string | null;
  canceled_at: string | null;
  created_at: string;
}

export interface PaymentPlan {
  tier: 'free' | 'pro' | 'premium';
  name: string;
  price_monthly: number;
  storage_quota_bytes: number;
  version_history_limit: number;
  rate_limit: number;
  features: string[];
}

export interface StorageInfo {
  storage_used_bytes: number;
  storage_quota_bytes: number;
  storage_used_percent: number;
  addon_count: number;
  version_count: number;
}

export interface AdminStats {
  total_users: number;
  total_addons: number;
  total_versions: number;
  active_subscriptions: number;
  users_by_tier: Record<string, number>;
  recent_signups: number;
}

export interface AuditLogEntry {
  id: number;
  admin_id: number | null;
  admin_username: string | null;
  action: string;
  target_type: string | null;
  target_id: number | null;
  details: string | null;
  ip_address: string | null;
  created_at: string;
}

// API Response Types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
}

export interface AddonListResponse {
  addons: Addon[];
  total: number;
  page: number;
  per_page: number;
}

export interface VersionListResponse {
  versions: Version[];
  total: number;
}

// Request Types
export interface AddonCreate {
  name: string;
  description?: string;
  homepage?: string;
  external?: boolean;
}

export interface AddonUpdate {
  name?: string;
  description?: string;
  homepage?: string;
  external?: boolean;
  is_active?: boolean;
  is_public?: boolean;
}

export interface VersionCreate {
  version: string;
  download_url: string;
  description?: string;
  changelog_url?: string;
  changelog_content?: string;
  breaking?: boolean;
  urgent?: boolean;
  release_date?: string;
}

export interface VersionUpdate {
  download_url?: string;
  description?: string;
  changelog_url?: string;
  changelog_content?: string;
  breaking?: boolean;
  urgent?: boolean;
}
