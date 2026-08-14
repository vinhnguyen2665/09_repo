import React from 'react';
import { 
  LayoutDashboard, 
  FolderTree, 
  Boxes, 
  Users, 
  Terminal, 
  Layers,
  FileCode2
} from 'lucide-react';

export type NavTab = 'dashboard' | 'explorer' | 'repositories' | 'users' | 'snippets';

interface SidebarProps {
  activeTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, onSelectTab }) => {
  const navItems = [
    {
      id: 'dashboard' as NavTab,
      label: 'Overview',
      icon: LayoutDashboard,
      desc: 'Health & Storage Metrics',
    },
    {
      id: 'explorer' as NavTab,
      label: 'Storage Explorer',
      icon: FolderTree,
      desc: 'Browse Artifacts & Code',
    },
    {
      id: 'repositories' as NavTab,
      label: 'Repositories',
      icon: Boxes,
      desc: 'Hosted, Proxy & Groups',
    },
    {
      id: 'snippets' as NavTab,
      label: 'Client Configs',
      icon: Terminal,
      desc: 'Maven, NPM, Docker, Pip',
    },
    {
      id: 'users' as NavTab,
      label: 'Access & Users',
      icon: Users,
      desc: 'RBAC & API Tokens',
    },
  ];

  return (
    <aside className="w-64 border-r border-slate-800/80 bg-[#0a0e1a]/95 flex flex-col justify-between py-6 px-3">
      <div className="space-y-6">
        <div className="px-3">
          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Management</p>
        </div>

        <nav className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left transition-all duration-150 group ${
                  isActive
                    ? 'bg-blue-600/15 border border-blue-500/40 text-blue-400 font-medium shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-transparent'
                }`}
              >
                <div
                  className={`w-8 h-8 rounded-lg flex items-center justify-center transition-colors ${
                    isActive ? 'bg-blue-600 text-white' : 'bg-slate-800/70 text-slate-400 group-hover:text-slate-200'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                </div>
                <div className="overflow-hidden">
                  <div className="text-sm font-medium leading-tight">{item.label}</div>
                  <div className="text-[11px] text-slate-500 truncate group-hover:text-slate-400">
                    {item.desc}
                  </div>
                </div>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Ecosystem formats preview badge */}
      <div className="px-3 py-4 rounded-xl bg-slate-900/60 border border-slate-800/80 space-y-2">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
          <Layers className="w-3.5 h-3.5 text-indigo-400" />
          <span>Active Engines</span>
        </div>
        <div className="grid grid-cols-2 gap-1.5 text-[11px]">
          <div className="px-2 py-1 rounded bg-slate-800/60 text-slate-300 font-mono flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-orange-400" /> Maven
          </div>
          <div className="px-2 py-1 rounded bg-slate-800/60 text-slate-300 font-mono flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-red-400" /> NPM
          </div>
          <div className="px-2 py-1 rounded bg-slate-800/60 text-slate-300 font-mono flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-sky-400" /> Docker
          </div>
          <div className="px-2 py-1 rounded bg-slate-800/60 text-slate-300 font-mono flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400" /> PyPI
          </div>
        </div>
      </div>
    </aside>
  );
};
