import React from 'react';
import { useOverviewStats, useRepositories } from '../../api/queries';
import { StorageGauge, formatBytes } from './StorageGauge';
import { 
  Package, 
  DownloadCloud, 
  Boxes, 
  CheckCircle2, 
  ArrowUpRight,
  Clock,
  Sparkles,
  FileCode,
  Shield,
  Layers,
  ArrowRight,
  Terminal
} from 'lucide-react';
import { Tag, Button, Spin, Empty } from 'antd';
import { NavTab } from '../layout/Sidebar';

interface OverviewDashboardProps {
  onSelectTab: (tab: NavTab) => void;
  onOpenSnippet: () => void;
}

export const OverviewDashboard: React.FC<OverviewDashboardProps> = ({ onSelectTab, onOpenSnippet }) => {
  const { data: stats, isLoading: statsLoading } = useOverviewStats();
  const { data: repos, isLoading: reposLoading } = useRepositories();

  if (statsLoading || !stats) {
    return (
      <div className="h-96 flex flex-col items-center justify-center gap-3">
        <Spin size="large" />
        <p className="text-sm text-slate-400">Loading Zero9Repo system metrics...</p>
      </div>
    );
  }

  const statCards = [
    {
      title: 'Total Artifacts',
      value: stats.storage.total_artifacts.toLocaleString(),
      subtitle: 'Indexed across all formats',
      icon: Package,
      gradient: 'from-blue-600/20 to-cyan-500/20',
      iconColor: 'text-cyan-400',
      borderColor: 'border-cyan-500/30',
    },
    {
      title: 'Total Downloads',
      value: stats.storage.total_downloads.toLocaleString(),
      subtitle: 'Client pull requests served',
      icon: DownloadCloud,
      gradient: 'from-indigo-600/20 to-purple-500/20',
      iconColor: 'text-indigo-400',
      borderColor: 'border-indigo-500/30',
    },
    {
      title: 'Active Repositories',
      value: stats.storage.total_repositories,
      subtitle: 'Hosted, Proxy & Groups',
      icon: Boxes,
      gradient: 'from-emerald-600/20 to-teal-500/20',
      iconColor: 'text-emerald-400',
      borderColor: 'border-emerald-500/30',
    },
    {
      title: 'Storage Used',
      value: formatBytes(stats.storage.total_size_bytes),
      subtitle: `Free: ${formatBytes(stats.storage.storage_free_bytes)}`,
      icon: Layers,
      gradient: 'from-amber-600/20 to-orange-500/20',
      iconColor: 'text-amber-400',
      borderColor: 'border-amber-500/30',
    },
  ];

  const formatBadges = [
    { name: 'Maven / Gradle', icon: '☕', desc: '.jar, .war, .pom & XML Merge', format: 'maven' },
    { name: 'NPM Registry', icon: '📦', desc: 'npm publish & upstream caching', format: 'npm' },
    { name: 'Docker / OCI', icon: '🐳', desc: 'v2 image manifests & layer blobs', format: 'docker' },
    { name: 'Python PyPI', icon: '🐍', desc: 'PEP 503 simple index & twine upload', format: 'pypi' },
  ];

  return (
    <div className="space-y-8">
      {/* Hero Banner */}
      <div className="relative overflow-hidden rounded-3xl p-8 bg-gradient-to-br from-[#111c38] via-[#0c1427] to-[#0a0f1d] border border-slate-800 shadow-2xl">
        <div className="absolute top-0 right-0 -mt-8 -mr-8 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-1/3 -mb-8 w-80 h-80 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
        
        <div className="relative z-10 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
          <div className="space-y-3 max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/30 text-blue-400 text-xs font-semibold">
              <Sparkles className="w-3.5 h-3.5" />
              High-Performance Universal Package Manager
            </div>
            <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              Enterprise Repository Infrastructure
            </h1>
            <p className="text-sm text-slate-300 leading-relaxed">
              Unified artifact management for Maven, Gradle, NPM, Docker OCI, and Python PyPI with smart upstream caching and dynamic XML metadata merging.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <Button
              type="primary"
              size="large"
              icon={<Terminal className="w-4 h-4" />}
              onClick={onOpenSnippet}
              className="bg-blue-600 hover:bg-blue-500 border-none font-medium text-sm h-11 px-5 rounded-xl shadow-lg shadow-blue-600/30 flex items-center gap-2"
            >
              Generate Connect Snippets
            </Button>
            <Button
              size="large"
              onClick={() => onSelectTab('explorer')}
              className="bg-slate-800/80 hover:bg-slate-700 text-slate-200 border-slate-700 font-medium text-sm h-11 px-5 rounded-xl flex items-center gap-2"
            >
              Browse Storage Explorer
            </Button>
          </div>
        </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {statCards.map((card, idx) => {
          const Icon = card.icon;
          return (
            <div
              key={idx}
              className="glass-panel glass-panel-hover rounded-2xl p-5 space-y-3 relative overflow-hidden"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-400">{card.title}</span>
                <div className={`w-9 h-9 rounded-xl bg-gradient-to-br ${card.gradient} border ${card.borderColor} flex items-center justify-center ${card.iconColor}`}>
                  <Icon className="w-5 h-5" />
                </div>
              </div>
              <div>
                <div className="text-2xl font-bold text-slate-100 tracking-tight">{card.value}</div>
                <div className="text-xs text-slate-400 mt-1">{card.subtitle}</div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Storage Gauge & Package Ecosystem */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <StorageGauge storage={stats.storage} />
        </div>

        {/* Ecosystem Engines Info Card */}
        <div className="glass-panel rounded-2xl p-6 flex flex-col justify-between space-y-4">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-slate-100 text-base">Supported Ecosystems</h3>
              <Tag color="blue">4 Engines</Tag>
            </div>
            <div className="space-y-2.5">
              {formatBadges.map((badge, idx) => (
                <div
                  key={idx}
                  onClick={() => onSelectTab('repositories')}
                  className="p-3 rounded-xl bg-slate-900/50 hover:bg-slate-800/80 border border-slate-800/80 hover:border-slate-700 cursor-pointer transition-all flex items-center justify-between group"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-xl">{badge.icon}</span>
                    <div>
                      <div className="text-sm font-semibold text-slate-200 group-hover:text-blue-400 transition-colors">
                        {badge.name}
                      </div>
                      <div className="text-[11px] text-slate-400">{badge.desc}</div>
                    </div>
                  </div>
                  <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-blue-400 group-hover:translate-x-0.5 transition-all" />
                </div>
              ))}
            </div>
          </div>
          <div className="p-3 rounded-xl bg-blue-950/30 border border-blue-900/40 text-[11px] text-blue-300/80 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-blue-400 shrink-0" />
            <span>Automatic proxy cache miss fallback active</span>
          </div>
        </div>
      </div>

      {/* Recent Activity Table */}
      <div className="glass-panel rounded-2xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400">
              <Clock className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-semibold text-slate-100 text-base">Recent Registry Activity</h3>
              <p className="text-xs text-slate-400">Latest uploaded and cached package events</p>
            </div>
          </div>
          <Button
            type="link"
            onClick={() => onSelectTab('explorer')}
            className="text-blue-400 hover:text-blue-300 text-xs p-0 flex items-center gap-1"
          >
            View all in Explorer <ArrowRight className="w-3.5 h-3.5" />
          </Button>
        </div>

        {stats.recent_activity.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-900/80 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3 rounded-l-lg">Event</th>
                  <th className="px-4 py-3">Repository</th>
                  <th className="px-4 py-3">Artifact Path</th>
                  <th className="px-4 py-3">Size</th>
                  <th className="px-4 py-3 rounded-r-lg">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
                {stats.recent_activity.map((act, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/40 transition-colors">
                    <td className="px-4 py-3">
                      {act.action === 'cache_miss_fetched' ? (
                        <Tag color="orange">PROXY FETCH</Tag>
                      ) : (
                        <Tag color="blue">HOSTED DEPLOY</Tag>
                      )}
                    </td>
                    <td className="px-4 py-3 font-semibold text-slate-200">{act.repo_name}</td>
                    <td className="px-4 py-3 text-slate-300 truncate max-w-xs" title={act.artifact_path}>
                      {act.artifact_path}
                    </td>
                    <td className="px-4 py-3 text-slate-400">{formatBytes(act.size_bytes)}</td>
                    <td className="px-4 py-3 text-slate-500">{new Date(act.timestamp).toLocaleTimeString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-8 text-center text-slate-500 text-xs">
            No recent artifact operations yet. Deploy a package via Maven, NPM, Docker, or PyPI.
          </div>
        )}
      </div>
    </div>
  );
};
