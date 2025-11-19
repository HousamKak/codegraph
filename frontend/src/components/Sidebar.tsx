import { Files, GitBranch, Database } from 'lucide-react';
import { useStore, SidebarTab } from '../store';

const SIDEBAR_TABS = [
  { id: 'explorer' as SidebarTab, icon: Files, label: 'Explorer' },
  { id: 'source-control' as SidebarTab, icon: GitBranch, label: 'Source Control' },
  { id: 'query' as SidebarTab, icon: Database, label: 'Query' },
];

export function Sidebar() {
  const { sidebarTab, setSidebarTab } = useStore();

  return (
    <div className="w-12 bg-graph-bg border-r border-border flex flex-col">
      {SIDEBAR_TABS.map((tab) => (
        <button
          key={tab.id}
          onClick={() => setSidebarTab(tab.id)}
          className={`h-12 w-12 flex items-center justify-center transition-colors ${
            sidebarTab === tab.id
              ? 'bg-panel-bg border-l-2 border-accent text-text-primary'
              : 'text-text-secondary hover:text-text-primary hover:bg-border/50'
          }`}
          title={tab.label}
        >
          <tab.icon size={20} />
        </button>
      ))}
    </div>
  );
}
