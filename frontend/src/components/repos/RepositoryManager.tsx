import React, { useState } from 'react';
import { useRepositories, useDeleteRepository } from '../../api/queries';
import { CreateRepoModal } from './CreateRepoModal';
import { EditRepoModal } from './EditRepoModal';
import { formatBytes } from '../dashboard/StorageGauge';
import { 
  Boxes, 
  Plus, 
  Copy, 
  Check, 
  Terminal, 
  Trash2, 
  Pencil,
  Globe, 
  Layers, 
  Server, 
  Clock, 
  Database,
  ExternalLink,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  LogIn
} from 'lucide-react';
import { Button, Tag, Input, Modal, message, Segmented, Spin, Empty } from 'antd';
import { Repository, RepoFormat, RepoType } from '../../types';
import { useAuth } from '../../context/AuthContext';

interface RepositoryManagerProps {
  onOpenSnippetWithRepo: (repoName: string) => void;
}

export const RepositoryManager: React.FC<RepositoryManagerProps> = ({ onOpenSnippetWithRepo }) => {
  const { isAuthenticated, openLoginModal } = useAuth();
  const { data: repos, isLoading } = useRepositories();
  const deleteMutation = useDeleteRepository();

  if (!isAuthenticated) {
    return (
      <div className="glass-panel rounded-3xl p-12 text-center max-w-lg mx-auto my-12 space-y-6 border border-slate-800 shadow-2xl">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center mx-auto shadow-lg shadow-blue-500/20">
          <ShieldAlert className="w-8 h-8 text-white" />
        </div>
        <div className="space-y-2">
          <h2 className="text-xl font-bold text-slate-100">Sign In Required</h2>
          <p className="text-sm text-slate-400">
            Please sign in to view and manage your Hosted, Proxy, and Group repositories.
          </p>
        </div>
        <Button
          type="primary"
          size="large"
          icon={<LogIn className="w-4 h-4" />}
          onClick={openLoginModal}
          className="bg-blue-600 hover:bg-blue-500 border-none font-semibold text-sm h-11 px-8 rounded-xl shadow-lg shadow-blue-600/30 flex items-center gap-2 mx-auto"
        >
          Sign In Now
        </Button>
      </div>
    );
  }

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editingRepo, setEditingRepo] = useState<Repository | null>(null);
  const [formatFilter, setFormatFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [copiedRepo, setCopiedRepo] = useState<string>('');

  const handleCopyEndpoint = (repo: Repository) => {
    const url = repo.endpoint_url || `${window.location.origin}/repository/${repo.name}`;
    navigator.clipboard.writeText(url);
    setCopiedRepo(repo.name);
    message.success(`Copied endpoint for ${repo.name}`);
    setTimeout(() => setCopiedRepo(''), 2000);
  };

  const handleDelete = (repo: Repository) => {
    Modal.confirm({
      title: 'Delete Repository',
      content: `Are you sure you want to permanently delete repository '${repo.name}' and all its stored artifacts?`,
      okText: 'Delete Forever',
      okType: 'danger',
      cancelText: 'Cancel',
      onOk: async () => {
        try {
          await deleteMutation.mutateAsync(repo.name);
          message.success(`Repository ${repo.name} deleted`);
        } catch {
          message.error('Failed to delete repository');
        }
      },
    });
  };

  const filteredRepos = repos?.filter((r) => {
    const matchesFormat = formatFilter === 'all' || r.format === formatFilter;
    const matchesType = typeFilter === 'all' || r.type === typeFilter;
    return matchesFormat && matchesType;
  }) || [];

  const getFormatBadge = (fmt: RepoFormat) => {
    switch (fmt) {
      case 'maven': return { label: 'Maven', color: 'orange', icon: '☕' };
      case 'npm': return { label: 'NPM', color: 'red', icon: '📦' };
      case 'docker': return { label: 'Docker', color: 'blue', icon: '🐳' };
      case 'pypi': return { label: 'PyPI', color: 'gold', icon: '🐍' };
    }
  };

  const getTypeBadge = (type: RepoType) => {
    switch (type) {
      case 'hosted': return { label: 'HOSTED', color: 'blue' };
      case 'proxy': return { label: 'PROXY', color: 'orange' };
      case 'group': return { label: 'GROUP', color: 'purple' };
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100 tracking-tight flex items-center gap-2.5">
            <Boxes className="w-5 h-5 text-blue-400" />
            Repository Management
          </h2>
          <p className="text-xs text-slate-400">Configure Hosted packages, Remote Proxy caches, and Group routers</p>
        </div>

        <Button
          type="primary"
          icon={<Plus className="w-4 h-4" />}
          onClick={() => setCreateModalOpen(true)}
          className="bg-blue-600 hover:bg-blue-500 border-none flex items-center gap-1.5 text-xs h-9 px-4 rounded-xl shadow-lg shadow-blue-600/20"
        >
          Create Repository
        </Button>
      </div>

      {/* Filters Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80">
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-xs text-slate-400 font-medium">Format:</span>
          <Segmented
            value={formatFilter}
            onChange={(val) => setFormatFilter(val as string)}
            options={[
              { label: 'All Formats', value: 'all' },
              { label: '☕ Maven', value: 'maven' },
              { label: '📦 NPM', value: 'npm' },
              { label: '🐳 Docker', value: 'docker' },
              { label: '🐍 PyPI', value: 'pypi' },
            ]}
          />
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-400 font-medium">Type:</span>
          <Segmented
            value={typeFilter}
            onChange={(val) => setTypeFilter(val as string)}
            options={[
              { label: 'All Types', value: 'all' },
              { label: 'Hosted', value: 'hosted' },
              { label: 'Proxy', value: 'proxy' },
              { label: 'Group', value: 'group' },
            ]}
          />
        </div>
      </div>

      {/* Repository Cards Grid */}
      {isLoading ? (
        <div className="h-64 flex flex-col items-center justify-center gap-3 text-slate-500 text-xs">
          <Spin size="large" />
          <span>Loading repositories...</span>
        </div>
      ) : filteredRepos.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredRepos.map((repo) => {
            const fmt = getFormatBadge(repo.format);
            const type = getTypeBadge(repo.type);

            return (
              <div
                key={repo.id}
                className="glass-panel glass-panel-hover rounded-2xl p-5 flex flex-col justify-between space-y-4 relative"
              >
                <div className="space-y-3">
                  {/* Top Bar */}
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2.5">
                      <span className="text-2xl">{fmt.icon}</span>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-mono font-bold text-slate-100 text-sm">{repo.name}</h3>
                          {!repo.is_online && (
                            <span className="text-[10px] px-1.5 py-0.2 rounded bg-rose-500/20 text-rose-400 border border-rose-500/30">
                              OFFLINE
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-slate-400 truncate max-w-[180px]">
                          {repo.description || `${fmt.label} ${type.label}`}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <Tag color={type.color} className="mr-0 text-[10px] font-semibold">
                        {type.label}
                      </Tag>
                    </div>
                  </div>

                  {/* Endpoint URL Box */}
                  <div className="flex items-center justify-between px-3 py-1.5 rounded-lg bg-slate-900/90 border border-slate-800 text-xs font-mono">
                    <span className="text-slate-400 truncate max-w-[210px]" title={repo.endpoint_url}>
                      {repo.endpoint_url || `/repository/${repo.name}`}
                    </span>
                    <Button
                      type="text"
                      size="small"
                      icon={copiedRepo === repo.name ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-slate-400" />}
                      onClick={() => handleCopyEndpoint(repo)}
                      title="Copy Endpoint URL"
                    />
                  </div>

                  {/* Specific config info */}
                  {repo.type === 'proxy' && repo.upstream_url && (
                    <div className="text-[11px] text-slate-400 bg-amber-950/20 border border-amber-500/20 p-2.5 rounded-lg space-y-1">
                      <div className="flex items-center gap-1.5 text-amber-300 font-medium">
                        <Globe className="w-3.5 h-3.5" />
                        <span>Upstream Remote:</span>
                      </div>
                      <p className="font-mono text-slate-300 truncate" title={repo.upstream_url}>{repo.upstream_url}</p>
                      <p className="text-[10px] flex items-center gap-1">
                        {repo.cache_ttl_hours === 0 || repo.cache_ttl_hours === null ? (
                          <span className="text-amber-300 font-semibold inline-flex items-center gap-1">
                            <span>TTL:</span> <Tag color="gold" className="mr-0 text-[9px] py-0 px-1 font-bold">Lưu vĩnh viễn (∞)</Tag>
                          </span>
                        ) : (
                          <span className="text-slate-400">TTL: {repo.cache_ttl_hours}h cache retention</span>
                        )}
                      </p>
                    </div>
                  )}

                  {repo.type === 'group' && repo.member_repo_names && (
                    <div className="text-[11px] text-slate-400 bg-purple-950/20 border border-purple-500/20 p-2.5 rounded-lg space-y-1.5">
                      <div className="flex items-center gap-1.5 text-purple-300 font-medium">
                        <Layers className="w-3.5 h-3.5" />
                        <span>Merged Group Priority:</span>
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {repo.member_repo_names.map((m, i) => (
                          <span key={i} className="px-1.5 py-0.5 rounded bg-purple-900/40 text-purple-200 font-mono text-[10px]">
                            {i + 1}. {m}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Bottom Stats & Actions */}
                <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs">
                  <div className="text-slate-400 font-mono text-[11px]">
                    <strong>{repo.total_artifacts || 0}</strong> items • <span>{formatBytes(repo.total_size_bytes || 0)}</span>
                  </div>

                  <div className="flex items-center gap-1">
                    <Button
                      type="text"
                      size="small"
                      icon={<Pencil className="w-3.5 h-3.5 text-slate-400 hover:text-blue-400" />}
                      onClick={() => setEditingRepo(repo)}
                      title="Edit Repository Info"
                    />
                    <Button
                      type="text"
                      size="small"
                      icon={<Terminal className="w-3.5 h-3.5 text-blue-400" />}
                      onClick={() => onOpenSnippetWithRepo(repo.name)}
                      title="View Connect Snippets"
                    />
                    <Button
                      type="text"
                      size="small"
                      danger
                      icon={<Trash2 className="w-3.5 h-3.5 text-rose-400" />}
                      onClick={() => handleDelete(repo)}
                      title="Delete Repository"
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="p-12 text-center text-slate-500 text-xs">
          <Empty description={<span className="text-slate-500">No repositories found matching filters</span>} />
        </div>
      )}

      {/* Create Modal */}
      {createModalOpen && (
        <CreateRepoModal
          isOpen={createModalOpen}
          onClose={() => setCreateModalOpen(false)}
        />
      )}

      {/* Edit Modal */}
      {editingRepo && (
        <EditRepoModal
          repo={editingRepo}
          isOpen={!!editingRepo}
          onClose={() => setEditingRepo(null)}
        />
      )}
    </div>
  );
};
