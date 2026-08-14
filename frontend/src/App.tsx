import React, { useState } from 'react';
import { ConfigProvider, theme } from 'antd';
import { AppLayout } from './components/layout/AppLayout';
import { NavTab } from './components/layout/Sidebar';
import { OverviewDashboard } from './components/dashboard/OverviewDashboard';
import { StorageExplorer } from './components/explorer/StorageExplorer';
import { RepositoryManager } from './components/repos/RepositoryManager';
import { UserManager } from './components/users/UserManager';
import { SnippetModal } from './components/snippets/SnippetModal';
import { ApiTokenModal } from './components/users/ApiTokenModal';
import { LoginModal } from './components/auth/LoginModal';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<NavTab>('dashboard');
  const [snippetOpen, setSnippetOpen] = useState<boolean>(false);
  const [snippetTargetRepo, setSnippetTargetRepo] = useState<string>('');
  const [tokensOpen, setTokensOpen] = useState<boolean>(false);

  const handleOpenSnippetWithRepo = (repoName: string) => {
    setSnippetTargetRepo(repoName);
    setSnippetOpen(true);
  };

  const renderActiveTab = () => {
    switch (activeTab) {
      case 'dashboard':
        return (
          <OverviewDashboard
            onSelectTab={setActiveTab}
            onOpenSnippet={() => setSnippetOpen(true)}
          />
        );
      case 'explorer':
        return <StorageExplorer />;
      case 'repositories':
        return (
          <RepositoryManager
            onOpenSnippetWithRepo={handleOpenSnippetWithRepo}
          />
        );
      case 'snippets':
        return (
          <div className="space-y-4">
            <h2 className="text-xl font-bold text-slate-100">Client Connect Quick Access</h2>
            <p className="text-xs text-slate-400">Ready-to-copy configuration files for package build systems.</p>
            <div className="glass-panel p-6 rounded-2xl">
              <button
                onClick={() => setSnippetOpen(true)}
                className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold transition-colors"
              >
                Open Snippet Generator Modal
              </button>
            </div>
          </div>
        );
      case 'users':
        return <UserManager />;
      default:
        return <OverviewDashboard onSelectTab={setActiveTab} onOpenSnippet={() => setSnippetOpen(true)} />;
    }
  };

  return (
    <ConfigProvider
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          colorPrimary: '#2563eb',
          colorBgBase: '#0b0f19',
          colorBgContainer: '#0f172a',
          colorBorder: '#334155',
          colorText: '#f8fafc',
          borderRadius: 8,
          fontFamily: 'Inter, sans-serif',
        },
      }}
    >
      <AppLayout
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        onOpenTokens={() => setTokensOpen(true)}
        onOpenSnippet={() => setSnippetOpen(true)}
      >
        {renderActiveTab()}
      </AppLayout>

      {/* Global Modals */}
      <SnippetModal
        isOpen={snippetOpen}
        onClose={() => setSnippetOpen(false)}
        initialRepoName={snippetTargetRepo}
      />

      <ApiTokenModal
        isOpen={tokensOpen}
        onClose={() => setTokensOpen(false)}
      />

      <LoginModal />
    </ConfigProvider>
  );
};

export default App;
