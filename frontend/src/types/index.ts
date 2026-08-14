export type UserRole = 'admin' | 'developer' | 'reader';

export interface User {
  id: number;
  username: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface ApiToken {
  id: number;
  name: string;
  token_prefix: string;
  created_at: string;
  expires_at?: string | null;
  raw_token?: string;
}

export type RepoFormat = 'maven' | 'npm' | 'docker' | 'pypi';
export type RepoType = 'hosted' | 'proxy' | 'group';

export interface Repository {
  id: number;
  name: string;
  format: RepoFormat;
  type: RepoType;
  description?: string;
  is_online: boolean;
  upstream_url?: string | null;
  cache_ttl_hours?: number;
  member_repo_names?: string[];
  extra_config?: Record<string, any>;
  endpoint_url?: string;
  total_artifacts?: number;
  total_size_bytes?: number;
  created_at: string;
  updated_at: string;
}

export interface Artifact {
  id: number;
  repo_name: string;
  path: string;
  filename: string;
  size_bytes: number;
  content_type: string;
  sha1?: string | null;
  md5?: string | null;
  sha256?: string | null;
  is_cached_proxy: boolean;
  downloads_count: number;
  created_at: string;
  updated_at: string;
  last_downloaded_at?: string | null;
}

export interface FileTreeNode {
  name: string;
  path: string;
  is_dir: boolean;
  size_bytes?: number;
  updated_at?: string;
  sha1?: string;
  md5?: string;
  sha256?: string;
  is_cached_proxy?: boolean;
  children?: FileTreeNode[] | null;
}

export interface FilePreview {
  filename: string;
  path: string;
  content_type: string;
  size_bytes: number;
  content: string;
  is_text: boolean;
}

export interface StorageStats {
  total_size_bytes: number;
  private_hosted_bytes: number;
  proxy_cached_bytes: number;
  total_artifacts: number;
  total_downloads: number;
  total_repositories: number;
  storage_free_bytes: number;
  storage_total_bytes: number;
}

export interface RepoStats {
  name: string;
  format: string;
  type: string;
  artifacts_count: number;
  total_size_bytes: number;
  downloads_count: number;
}

export interface RecentActivityItem {
  action: 'upload' | 'download' | 'cache_miss_fetched' | 'delete';
  repo_name: string;
  artifact_path: string;
  size_bytes: number;
  timestamp: string;
}

export interface SystemOverviewStats {
  storage: StorageStats;
  repositories: RepoStats[];
  recent_activity: RecentActivityItem[];
}
