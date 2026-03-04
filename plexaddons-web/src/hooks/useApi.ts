/**
 * React Query hooks for data fetching with SWR caching.
 *
 * Usage:
 *   const { data: addon, isLoading } = useAddon('my-addon');
 *   const { data: addons } = useAddons({ search: 'cool', limit: 20 });
 */
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import type { Addon, User } from '../types';

// ─── Query Keys ───
export const queryKeys = {
  me: ['me'] as const,
  addons: (params?: Record<string, unknown>) => ['addons', params ?? {}] as const,
  addon: (slug: string) => ['addon', slug] as const,
  versions: (slug: string) => ['versions', slug] as const,
};

// ─── User ───
export function useMe() {
  return useQuery<User>({
    queryKey: queryKeys.me,
    queryFn: () => api.getMe(),
    retry: false,
  });
}

// ─── Addons ───
export function useAddon(slug: string) {
  return useQuery<Addon>({
    queryKey: queryKeys.addon(slug),
    queryFn: () => api.getAddon(slug),
    enabled: !!slug,
  });
}

// ─── Invalidation helpers ───
export function useInvalidateAddon() {
  const qc = useQueryClient();
  return (slug: string) => qc.invalidateQueries({ queryKey: queryKeys.addon(slug) });
}

export function useInvalidateAddons() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: ['addons'] });
}
