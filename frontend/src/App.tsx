import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useStore } from './store';
import { api } from './api/client';
import { useWebSocket } from './hooks/useWebSocket';
import { Sidebar } from './components/Sidebar';
import { FileExplorer } from './components/FileExplorer';
import { SourceControl } from './components/SourceControl';
import { QueryPanel } from './components/QueryPanel';
import { GraphView } from './components/GraphView';
import { RightPanel } from './components/RightPanel';
import { LoadingOverlay } from './components/LoadingOverlay';
import { ErrorBanner } from './components/ErrorBanner';

export default function App() {
  const {
    sidebarTab,
    setCommits,
    showRightPanel,
    isLoading,
    error,
    setError,
  } = useStore();

  // Initialize WebSocket connection for real-time updates
  useWebSocket();

  // Fetch git commits
  const { data: commits } = useQuery({
    queryKey: ['commits'],
    queryFn: () => api.listCommits(50),
  });

  // Update store when commits data changes
  useEffect(() => {
    if (commits) {
      setCommits(commits);
    }
  }, [commits, setCommits]);

  // Render sidebar content based on active tab
  const renderSidebarContent = () => {
    switch (sidebarTab) {
      case 'explorer':
        return <FileExplorer />;
      case 'source-control':
        return <SourceControl />;
      case 'query':
        return <QueryPanel />;
      default:
        return <FileExplorer />;
    }
  };

  return (
    <div className="h-screen w-screen flex bg-graph-bg overflow-hidden">
      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      <div className="flex-1 flex overflow-hidden h-full">
        {/* VS Code-style Sidebar */}
        <Sidebar />

        {/* Sidebar Content */}
        {renderSidebarContent()}

        {/* Main Content - Graph View Only */}
        <div className="flex-1 overflow-hidden">
          <GraphView />
        </div>

        {/* Right Panel - Inspector */}
        {showRightPanel && <RightPanel />}
      </div>

      {isLoading && <LoadingOverlay />}
    </div>
  );
}
