import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { 
  Server, 
  ShieldCheck, 
  Key, 
  LogOut, 
  LogIn, 
  User as UserIcon,
  Activity,
  Terminal
} from 'lucide-react';
import { Dropdown, Button, Tag } from 'antd';

interface HeaderProps {
  onOpenTokens: () => void;
  onOpenSnippet: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onOpenTokens, onOpenSnippet }) => {
  const { user, isAuthenticated, logout, openLoginModal } = useAuth();

  const userMenuItems = [
    {
      key: 'user-info',
      label: (
        <div className="px-2 py-1.5 border-b border-slate-700">
          <p className="font-semibold text-slate-100">{user?.username}</p>
          <p className="text-xs text-slate-400">{user?.email}</p>
          <div className="mt-1">
            <Tag color={user?.role === 'admin' ? 'red' : user?.role === 'developer' ? 'blue' : 'green'}>
              {user?.role?.toUpperCase()}
            </Tag>
          </div>
        </div>
      ),
    },
    {
      key: 'tokens',
      icon: <Key className="w-4 h-4 text-blue-400" />,
      label: <span onClick={onOpenTokens}>API Access Tokens</span>,
    },
    {
      type: 'divider' as const,
    },
    {
      key: 'logout',
      icon: <LogOut className="w-4 h-4 text-rose-400" />,
      danger: true,
      label: <span onClick={logout}>Sign Out</span>,
    },
  ];

  return (
    <header className="h-16 border-b border-slate-800 bg-[#0c1222]/90 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-30">
      {/* Brand & Status */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-cyan-400 flex items-center justify-center shadow-lg shadow-blue-500/20">
          <Server className="w-5 h-5 text-white" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-extrabold text-lg tracking-tight bg-gradient-to-r from-blue-400 via-sky-300 to-indigo-300 bg-clip-text text-transparent">
              Zero9Repo
            </span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/10 border border-blue-500/30 text-blue-400 font-mono font-medium">
              v1.0.0
            </span>
          </div>
          <p className="text-xs text-slate-400 hidden sm:block">Enterprise Universal Package Registry</p>
        </div>
      </div>

      {/* Center status indicators */}
      <div className="hidden md:flex items-center gap-4 text-xs">
        <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="font-medium">System Online</span>
        </div>
        <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-800/80 border border-slate-700/60 text-slate-300 font-mono">
          <Activity className="w-3.5 h-3.5 text-blue-400" />
          <span>HTTP 2.0 / Async I/O</span>
        </div>
      </div>

      {/* Right User & Actions */}
      <div className="flex items-center gap-3">
        <Button
          type="primary"
          ghost
          icon={<Terminal className="w-3.5 h-3.5" />}
          onClick={onOpenSnippet}
          className="flex items-center gap-1.5 border-blue-500/40 text-blue-400 hover:text-blue-300 hover:border-blue-400 text-xs h-8"
        >
          Connect Client
        </Button>

        {isAuthenticated ? (
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight" trigger={['click']}>
            <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-800 border border-slate-700/80 transition-colors">
              <div className="w-6 h-6 rounded-full bg-gradient-to-tr from-blue-500 to-indigo-500 flex items-center justify-center text-white text-xs font-bold">
                {user?.username?.[0]?.toUpperCase() || 'U'}
              </div>
              <span className="text-xs font-medium text-slate-200">{user?.username}</span>
              <ShieldCheck className="w-3.5 h-3.5 text-blue-400" />
            </button>
          </Dropdown>
        ) : (
          <Button
            type="primary"
            icon={<LogIn className="w-3.5 h-3.5" />}
            onClick={openLoginModal}
            className="bg-blue-600 hover:bg-blue-500 border-none flex items-center gap-1.5 text-xs h-8"
          >
            Sign In
          </Button>
        )}
      </div>
    </header>
  );
};
