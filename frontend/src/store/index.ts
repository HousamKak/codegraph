import { create } from 'zustand';
import type {
  GraphData,
  GraphNode,
  GraphEdge,
  Snapshot,
  GitCommit,
  ValidationReport,
  SelectedElement,
  ViewMode,
  DiffHighlightMode,
} from '../types';

export type SidebarTab = 'explorer' | 'source-control' | 'query';

interface AppState {
  // Sidebar state
  sidebarTab: SidebarTab;
  setSidebarTab: (tab: SidebarTab) => void;
  sidebarWidth: number;
  setSidebarWidth: (width: number) => void;

  // File explorer state
  rootDirectory: string | null;
  setRootDirectory: (dir: string | null) => void;
  selectedFiles: string[];
  setSelectedFiles: (files: string[]) => void;
  expandedDirectories: Set<string>;
  toggleDirectory: (path: string) => void;

  // View state
  viewMode: ViewMode;
  setViewMode: (mode: ViewMode) => void;

  // Graph data
  graphData: GraphData | null;
  setGraphData: (data: GraphData | null) => void;

  // Selection
  selectedNode: GraphNode | null;
  setSelectedNode: (node: GraphNode | null) => void;
  selectedEdge: GraphEdge | null;
  setSelectedEdge: (edge: GraphEdge | null) => void;
  selectedElement: SelectedElement | null;
  setSelectedElement: (element: SelectedElement | null) => void;

  // Snapshots (legacy)
  snapshots: Snapshot[];
  setSnapshots: (snapshots: Snapshot[]) => void;
  removeSnapshot: (id: string) => void;
  selectedSnapshot: string | null;
  setSelectedSnapshot: (id: string | null) => void;

  // Git commits
  commits: GitCommit[];
  setCommits: (commits: GitCommit[]) => void;
  selectedCommit: string | null;
  setSelectedCommit: (hash: string | null) => void;
  indexingCommit: string | null;
  setIndexingCommit: (hash: string | null) => void;
  markCommitIndexed: (hash: string) => void;

  // Diff
  diffData: any | null;  // Can be GraphDiff or CommitDiff
  setDiffData: (diff: any | null) => void;
  compareFrom: string | null;
  setCompareFrom: (id: string | null) => void;
  compareTo: string | null;
  setCompareTo: (id: string | null) => void;
  compareFromGraph: GraphData | null;
  setCompareFromGraph: (data: GraphData | null) => void;
  compareToGraph: GraphData | null;
  setCompareToGraph: (data: GraphData | null) => void;
  diffHighlightMode: DiffHighlightMode;
  setDiffHighlightMode: (mode: DiffHighlightMode) => void;

  // Validation
  validationReport: ValidationReport | null;
  setValidationReport: (report: ValidationReport | null) => void;

  // Query
  queryHistory: string[];
  addQueryToHistory: (query: string) => void;
  clearQueryHistory: () => void;

  // UI state
  leftPanelWidth: number;
  setLeftPanelWidth: (width: number) => void;
  rightPanelWidth: number;
  setRightPanelWidth: (width: number) => void;
  bottomPanelHeight: number;
  setBottomPanelHeight: (height: number) => void;
  showLeftPanel: boolean;
  toggleLeftPanel: () => void;
  showRightPanel: boolean;
  toggleRightPanel: () => void;
  showBottomPanel: boolean;
  toggleBottomPanel: () => void;

  // Loading states
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
  loadingMessage: string;
  setLoadingMessage: (message: string) => void;

  // Error state
  error: string | null;
  setError: (error: string | null) => void;

  // WebSocket state
  wsConnected: boolean;
  setWsConnected: (connected: boolean) => void;
  realtimeEnabled: boolean;
  setRealtimeEnabled: (enabled: boolean) => void;
  lastFileChange: string | null;
  setLastFileChange: (file: string | null) => void;
}

export const useStore = create<AppState>((set) => ({
  // Sidebar state
  sidebarTab: 'explorer',
  setSidebarTab: (tab) => set({ sidebarTab: tab }),
  sidebarWidth: 250,
  setSidebarWidth: (width) => set({ sidebarWidth: width }),

  // File explorer state
  rootDirectory: null,
  setRootDirectory: (dir) => set({ rootDirectory: dir }),
  selectedFiles: [],
  setSelectedFiles: (files) => set({ selectedFiles: files }),
  expandedDirectories: new Set<string>(),
  toggleDirectory: (path) =>
    set((state) => {
      const newSet = new Set(state.expandedDirectories);
      if (newSet.has(path)) {
        newSet.delete(path);
      } else {
        newSet.add(path);
      }
      return { expandedDirectories: newSet };
    }),

  // View state
  viewMode: 'graph',
  setViewMode: (mode) => set({ viewMode: mode }),

  // Graph data
  graphData: null,
  setGraphData: (data) => set({ graphData: data }),

  // Selection
  selectedNode: null,
  setSelectedNode: (node) => set({ selectedNode: node }),
  selectedEdge: null,
  setSelectedEdge: (edge) => set({ selectedEdge: edge }),
  selectedElement: null,
  setSelectedElement: (element) => set({ selectedElement: element }),

  // Snapshots (legacy)
  snapshots: [],
  setSnapshots: (snapshots) => set({ snapshots }),
  removeSnapshot: (id) =>
    set((state) => ({
      snapshots: state.snapshots.filter((snapshot) => snapshot.snapshot_id !== id),
    })),
  selectedSnapshot: null,
  setSelectedSnapshot: (id) => set({ selectedSnapshot: id }),

  // Git commits
  commits: [],
  setCommits: (commits) => set({ commits }),
  selectedCommit: null,
  setSelectedCommit: (hash) => set({ selectedCommit: hash }),
  indexingCommit: null,
  setIndexingCommit: (hash) => set({ indexingCommit: hash }),
  markCommitIndexed: (hash) =>
    set((state) => ({
      commits: state.commits.map((commit) =>
        commit.hash === hash ? { ...commit, indexed: true } : commit
      ),
    })),

  // Diff
  diffData: null,
  setDiffData: (diff) => set({ diffData: diff }),
  compareFrom: null,
  setCompareFrom: (id) => set({ compareFrom: id }),
  compareTo: null,
  setCompareTo: (id) => set({ compareTo: id }),
  compareFromGraph: null,
  setCompareFromGraph: (data) => set({ compareFromGraph: data }),
  compareToGraph: null,
  setCompareToGraph: (data) => set({ compareToGraph: data }),
  diffHighlightMode: 'all',
  setDiffHighlightMode: (mode) => set({ diffHighlightMode: mode }),

  // Validation
  validationReport: null,
  setValidationReport: (report) => set({ validationReport: report }),

  // Query
  queryHistory: [],
  addQueryToHistory: (query) =>
    set((state) => ({
      queryHistory: [query, ...state.queryHistory.filter((q) => q !== query)].slice(0, 50),
    })),
  clearQueryHistory: () => set({ queryHistory: [] }),

  // UI state
  leftPanelWidth: 280,
  setLeftPanelWidth: (width) => set({ leftPanelWidth: width }),
  rightPanelWidth: 320,
  setRightPanelWidth: (width) => set({ rightPanelWidth: width }),
  bottomPanelHeight: 200,
  setBottomPanelHeight: (height) => set({ bottomPanelHeight: height }),
  showLeftPanel: true,
  toggleLeftPanel: () => set((state) => ({ showLeftPanel: !state.showLeftPanel })),
  showRightPanel: true,
  toggleRightPanel: () => set((state) => ({ showRightPanel: !state.showRightPanel })),
  showBottomPanel: true,
  toggleBottomPanel: () => set((state) => ({ showBottomPanel: !state.showBottomPanel })),

  // Loading states
  isLoading: false,
  setIsLoading: (loading) => set({ isLoading: loading }),
  loadingMessage: '',
  setLoadingMessage: (message) => set({ loadingMessage: message }),

  // Error state
  error: null,
  setError: (error) => set({ error }),

  // WebSocket state
  wsConnected: false,
  setWsConnected: (connected) => set({ wsConnected: connected }),
  realtimeEnabled: false,
  setRealtimeEnabled: (enabled) => set({ realtimeEnabled: enabled }),
  lastFileChange: null,
  setLastFileChange: (file) => set({ lastFileChange: file }),
}));
