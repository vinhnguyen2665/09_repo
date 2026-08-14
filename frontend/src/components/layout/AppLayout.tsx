import React from 'react';
import { Header } from './Header';
import { Sidebar, NavTab } from './Sidebar';

interface AppLayoutProps {
  activeTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  onOpenTokens: () => void;
  onOpenSnippet: () => void;
  children: React.ReactNode;
}

export const AppLayout: React.FC<AppLayoutProps> = ({
  activeTab,
  onSelectTab,
  onOpenTokens,
  onOpenSnippet,
  children,
}) => {
  return (
    <div className="min-h-screen flex flex-col bg-[#070b14] text-slate-100 selection:bg-blue-600 selection:text-white">
      <Header onOpenTokens={onOpenTokens} onOpenSnippet={onOpenSnippet} />
      
      <div className="flex-1 flex overflow-hidden">
        <Sidebar activeTab={activeTab} onSelectTab={onSelectTab} />
        
        <main className="flex-1 overflow-y-auto p-6 md:p-8 bg-[#090e1c]/40">
          <div className="max-w-7xl mx-auto space-y-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};
