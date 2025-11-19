import {
  GitBranch,
  History,
  AlertTriangle,
  PanelLeft,
  PanelRight,
  PanelBottom,
  RefreshCw,
  Save,
} from 'lucide-react';
import { useStore } from '../store';
import { api } from '../api/client';
import { useMutation, useQueryClient } from '@tanstack/react-query';

export function Header() {
  const {
    viewMode,
    setViewMode,
    toggleLeftPanel,
    toggleRightPanel,
    toggleBottomPanel,
    showLeftPanel,
    showRightPanel,
    showBottomPanel,
    setIsLoading,
    setError,
  } = useStore();

  const queryClient = useQueryClient();

  const createSnapshotMutation = useMutation({
    mutationFn: (description: string) => api.createSnapshot(description),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['snapshots'] });
    },
    onError: (error: Error) => {
      setError(error.message);
    },
  });

  const handleCreateSnapshot = () => {
    const description = prompt('Enter snapshot description:');
    if (description) {
      createSnapshotMutation.mutate(description);
    }
  };

  const handleRefresh = async () => {
    setIsLoading(true);
    try {
      await queryClient.invalidateQueries({ queryKey: ['graph'] });
      await queryClient.invalidateQueries({ queryKey: ['snapshots'] });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <header className="h-12 bg-panel-bg border-b border-border flex items-center justify-between px-4">
      {/* Logo and Title */}
      <div className="flex items-center gap-3">
        <div className="w-6 h-6 bg-accent rounded flex items-center justify-center">
          <GitBranch size={14} />
        </div>
        <span className="font-semibold text-sm">CodeGraph</span>
        <span className="text-text-secondary text-xs">Software Physics Visualizer</span>
      </div>

      {/* View Mode Tabs */}
      <div className="flex items-center gap-1 bg-graph-bg rounded p-1">
        <button
          onClick={() => setViewMode('graph')}
          className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
            viewMode === 'graph'
              ? 'bg-accent text-white'
              : 'text-text-secondary hover:text-text-primary'
          }`}
        >
          Graph
        </button>
        <button
          onClick={() => setViewMode('diff')}
          className={`px-3 py-1 rounded text-xs font-medium transition-colors flex items-center gap-1 ${
            viewMode === 'diff'
              ? 'bg-accent text-white'
              : 'text-text-secondary hover:text-text-primary'
          }`}
        >
          <History size={12} />
          Diff
        </button>
        <button
          onClick={() => setViewMode('validation')}
          className={`px-3 py-1 rounded text-xs font-medium transition-colors flex items-center gap-1 ${
            viewMode === 'validation'
              ? 'bg-accent text-white'
              : 'text-text-secondary hover:text-text-primary'
          }`}
        >
          <AlertTriangle size={12} />
          Validation
        </button>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        <button
          onClick={handleCreateSnapshot}
          className="p-2 rounded hover:bg-border transition-colors"
          title="Create Snapshot"
        >
          <Save size={16} />
        </button>
        <button
          onClick={handleRefresh}
          className="p-2 rounded hover:bg-border transition-colors"
          title="Refresh"
        >
          <RefreshCw size={16} />
        </button>
        <div className="w-px h-6 bg-border mx-1" />
        <button
          onClick={toggleLeftPanel}
          className={`p-2 rounded transition-colors ${
            showLeftPanel ? 'bg-border' : 'hover:bg-border'
          }`}
          title="Toggle Left Panel"
        >
          <PanelLeft size={16} />
        </button>
        <button
          onClick={toggleBottomPanel}
          className={`p-2 rounded transition-colors ${
            showBottomPanel ? 'bg-border' : 'hover:bg-border'
          }`}
          title="Toggle Bottom Panel"
        >
          <PanelBottom size={16} />
        </button>
        <button
          onClick={toggleRightPanel}
          className={`p-2 rounded transition-colors ${
            showRightPanel ? 'bg-border' : 'hover:bg-border'
          }`}
          title="Toggle Right Panel"
        >
          <PanelRight size={16} />
        </button>
      </div>
    </header>
  );
}
