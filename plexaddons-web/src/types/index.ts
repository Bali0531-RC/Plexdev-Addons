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

// Ticket Types
export type TicketStatus = 'open' | 'in_progress' | 'resolved' | 'closed';
export type TicketPriority = 'low' | 'normal' | 'high' | 'urgent';
export type TicketCategory = 'general' | 'billing' | 'technical' | 'feature_request' | 'bug_report';

export interface TicketAttachment {
  id: number;
  original_filename: string;
  file_size: number;
  compressed_size: number | null;
  mime_type: string | null;
  is_compressed: boolean;
  created_at: string;
}

export interface TicketMessage {
  id: number;
  ticket_id: number;
  author_id: number | null;
  author_username: string | null;
  content: string;
  is_staff_reply: boolean;
  is_system_message: boolean;
  created_at: string;
  edited_at: string | null;
  attachments: TicketAttachment[];
}

export interface Ticket {
  id: number;
  user_id: number;
  user_username: string | null;
  subject: string;
  category: TicketCategory;
  priority: TicketPriority;
  status: TicketStatus;
  assigned_admin_id: number | null;
  assigned_admin_username: string | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  closed_at: string | null;
}

export interface TicketDetail extends Ticket {
  messages: TicketMessage[];
}

export interface TicketListResponse {
  tickets: Ticket[];
  total: number;
  page: number;
  per_page: number;
}

export interface TicketCreate {
  subject: string;
  content: string;
  category: TicketCategory;
}

export interface TicketStats {
  total_tickets: number;
  tickets_open: number;
  tickets_in_progress: number;
  tickets_resolved: number;
  tickets_closed: number;
  active_low_priority: number;
  active_normal_priority: number;
  active_high_priority: number;
  active_urgent_priority: number;
  unassigned_tickets: number;
  avg_resolution_hours: number | null;
}

export interface CannedResponse {
  id: number;
  title: string;
  content: string;
  category: TicketCategory | null;
  created_by: number | null;
  creator_username: string | null;
  usage_count: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CannedResponseListResponse {
  responses: CannedResponse[];
  total: number;
}
