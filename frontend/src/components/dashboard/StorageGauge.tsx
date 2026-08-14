import React from 'react';
import { StorageStats } from '../../types';
import { HardDrive, Database, CloudDownload, Disc } from 'lucide-react';

interface StorageGaugeProps {
  storage: StorageStats;
}

export const formatBytes = (bytes: number, decimals = 2) => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};

export const StorageGauge: React.FC<StorageGaugeProps> = ({ storage }) => {
  const totalUsed = storage.total_size_bytes;
  const hosted = storage.private_hosted_bytes;
  const proxy = storage.proxy_cached_bytes;

  const hostedPercent = totalUsed > 0 ? Math.round((hosted / totalUsed) * 100) : 50;
  const proxyPercent = totalUsed > 0 ? Math.round((proxy / totalUsed) * 100) : 50;

  return (
    <div className="glass-panel rounded-2xl p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400">
            <HardDrive className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-semibold text-slate-100 text-base">Storage Distribution Gauge</h3>
            <p className="text-xs text-slate-400">Hosted Private Artifacts vs Proxy Cache</p>
          </div>
        </div>
        <div className="text-right">
          <span className="text-2xl font-bold text-slate-100">{formatBytes(totalUsed)}</span>
          <p className="text-xs text-slate-400">Total Registry Footprint</p>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="space-y-2">
        <div className="h-4 w-full bg-slate-800/90 rounded-full overflow-hidden flex p-0.5 border border-slate-700/60">
          <div
            style={{ width: `${hostedPercent}%` }}
            className="h-full bg-gradient-to-r from-blue-600 to-indigo-500 rounded-l-full transition-all duration-500 relative group"
            title={`Hosted: ${formatBytes(hosted)}`}
          />
          <div
            style={{ width: `${proxyPercent}%` }}
            className="h-full bg-gradient-to-r from-amber-500 to-orange-500 rounded-r-full transition-all duration-500 relative group"
            title={`Proxy: ${formatBytes(proxy)}`}
          />
        </div>
        <div className="flex justify-between text-xs text-slate-400 font-mono">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-sm bg-indigo-500" />
            <span>Hosted Private ({hostedPercent}%)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-sm bg-amber-500" />
            <span>Proxy Cached ({proxyPercent}%)</span>
          </div>
        </div>
      </div>

      {/* Storage Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
            <Database className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-400">Private Hosted Storage</p>
            <p className="text-lg font-bold text-slate-100">{formatBytes(hosted)}</p>
            <p className="text-[11px] text-indigo-400">Permanent internal artifacts</p>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
            <CloudDownload className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-400">Upstream Proxy Cache</p>
            <p className="text-lg font-bold text-slate-100">{formatBytes(proxy)}</p>
            <p className="text-[11px] text-amber-400">Lazy fetched from central registries</p>
          </div>
        </div>
      </div>
    </div>
  );
};
