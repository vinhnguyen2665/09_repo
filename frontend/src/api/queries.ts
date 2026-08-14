import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from './client';
import {
  User,
  ApiToken,
  Repository,
  Artifact,
  FileTreeNode,
  FilePreview,
  SystemOverviewStats,
} from '../types';

// ================= AUTH & USER =================

export const useCurrentUser = () => {
  return useQuery({
    queryKey: ['auth', 'me'],
    queryFn: async () => {
      const { data } = await apiClient.get<User>('/auth/me');
      return data;
    },
    retry: false,
  });
};

export const useUserTokens = () => {
  return useQuery({
    queryKey: ['auth', 'tokens'],
    queryFn: async () => {
      const { data } = await apiClient.get<ApiToken[]>('/auth/tokens');
      return data;
    },
  });
};

export const useCreateApiToken = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { name: string }) => {
      const { data } = await apiClient.post<ApiToken>('/auth/tokens', payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auth', 'tokens'] });
    },
  });
};

export const useRevokeApiToken = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (tokenId: number) => {
      const { data } = await apiClient.delete(`/auth/tokens/${tokenId}`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auth', 'tokens'] });
    },
  });
};

// ================= STATS & DASHBOARD =================

export const useOverviewStats = () => {
  return useQuery({
    queryKey: ['stats', 'overview'],
    queryFn: async () => {
      const { data } = await apiClient.get<SystemOverviewStats>('/stats/overview');
      return data;
    },
    refetchInterval: 10000,
  });
};

// ================= REPOSITORIES =================

export const useRepositories = () => {
  return useQuery({
    queryKey: ['repositories'],
    queryFn: async () => {
      const { data } = await apiClient.get<Repository[]>('/repositories');
      return data;
    },
  });
};

export const useCreateRepository = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<Repository>) => {
      const { data } = await apiClient.post<Repository>('/repositories', payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['repositories'] });
      queryClient.invalidateQueries({ queryKey: ['stats', 'overview'] });
    },
  });
};

export const useUpdateRepository = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ name, data }: { name: string; data: Partial<Repository> }) => {
      const res = await apiClient.put<Repository>(`/repositories/${name}`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['repositories'] });
    },
  });
};

export const useDeleteRepository = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (name: string) => {
      const { data } = await apiClient.delete(`/repositories/${name}`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['repositories'] });
      queryClient.invalidateQueries({ queryKey: ['stats', 'overview'] });
    },
  });
};

// ================= STORAGE EXPLORER =================

export const useFileTree = (repoName: string) => {
  return useQuery({
    queryKey: ['storage', 'tree', repoName],
    queryFn: async () => {
      if (!repoName) return [];
      const { data } = await apiClient.get<FileTreeNode[]>(`/storage/tree?repo_name=${encodeURIComponent(repoName)}`);
      return data;
    },
    enabled: !!repoName,
  });
};

export const useInspectArtifact = (repoName: string, path: string) => {
  return useQuery({
    queryKey: ['storage', 'inspect', repoName, path],
    queryFn: async () => {
      if (!repoName || !path) return null;
      const { data } = await apiClient.get<Artifact>(`/storage/inspect?repo_name=${encodeURIComponent(repoName)}&path=${encodeURIComponent(path)}`);
      return data;
    },
    enabled: !!repoName && !!path,
  });
};

export const usePreviewFile = (repoName: string, path: string) => {
  return useQuery({
    queryKey: ['storage', 'preview', repoName, path],
    queryFn: async () => {
      if (!repoName || !path) return null;
      const { data } = await apiClient.get<FilePreview>(`/storage/preview?repo_name=${encodeURIComponent(repoName)}&path=${encodeURIComponent(path)}`);
      return data;
    },
    enabled: !!repoName && !!path,
  });
};

export const useDeleteArtifact = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ repoName, path }: { repoName: string; path: string }) => {
      const { data } = await apiClient.delete(`/storage/artifact?repo_name=${encodeURIComponent(repoName)}&path=${encodeURIComponent(path)}`);
      return data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['storage', 'tree', variables.repoName] });
      queryClient.invalidateQueries({ queryKey: ['stats', 'overview'] });
      queryClient.invalidateQueries({ queryKey: ['repositories'] });
    },
  });
};

// ================= USERS MANAGEMENT =================

export const useUsers = () => {
  return useQuery({
    queryKey: ['users'],
    queryFn: async () => {
      const { data } = await apiClient.get<User[]>('/users');
      return data;
    },
  });
};

export const useCreateUser = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { username: string; email: string; password: string; role: string }) => {
      const { data } = await apiClient.post<User>('/users', payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
};

export const useDeleteUser = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (userId: number) => {
      const { data } = await apiClient.delete(`/users/${userId}`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
};
