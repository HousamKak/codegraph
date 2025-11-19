// Graph node and edge types
export interface GraphNode {
  id: string;
  labels: string[];
  properties: Record<string, any>;
}

export interface GraphEdge {
  id?: string;
  source: string;
  target: string;
  type: string;
  properties: Record<string, any>;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// Snapshot types
export interface Snapshot {
  snapshot_id: string;
  timestamp: string;
  description: string;
  node_count: number;
  edge_count: number;
  metadata?: Record<string, any>;
}

// Git commit types
export interface GitCommit {
  hash: string;
  short_hash: string;
  message: string;
  author: string;
  date: string;
  indexed: boolean;
}

export interface CommitInfo extends GitCommit {
  files_changed?: string[];
}

export interface CommitDiff {
  old_commit: string;
  new_commit: string;
  old_info: {
    hash: string;
    message: string;
    date: string;
  };
  new_info: {
    hash: string;
    message: string;
    date: string;
  };
  summary: {
    nodes_added: number;
    nodes_removed: number;
    nodes_modified: number;
    edges_added: number;
    edges_removed: number;
    edges_modified: number;
  };
  nodes: {
    added: GraphNode[];
    removed: GraphNode[];
    modified: ModifiedNode[];
  };
  edges: {
    added: GraphEdge[];
    removed: GraphEdge[];
    modified: any[];
  };
}

export interface SnapshotStatistics {
  snapshot_id: string;
  timestamp: string;
  description: string;
  total_nodes: number;
  total_edges: number;
  nodes_by_type: Record<string, number>;
  edges_by_type: Record<string, number>;
}

// Diff types
export interface NodeDiff {
  added: GraphNode[];
  removed: GraphNode[];
  modified: ModifiedNode[];
}

export interface ModifiedNode {
  id: string;
  old: GraphNode;
  new: GraphNode;
  changes: Record<string, { old: any; new: any }>;
}

export interface EdgeDiff {
  added: GraphEdge[];
  removed: GraphEdge[];
  modified: ModifiedEdge[];
}

export interface ModifiedEdge {
  signature: string;
  old: GraphEdge;
  new: GraphEdge;
}

export interface GraphDiff {
  old_snapshot_id: string;
  new_snapshot_id: string;
  nodes: NodeDiff;
  edges: EdgeDiff;
  summary: {
    nodes_added: number;
    nodes_removed: number;
    nodes_modified: number;
    edges_added: number;
    edges_removed: number;
    edges_modified: number;
  };
}

export interface DiffSummary {
  old_snapshot: string;
  new_snapshot: string;
  summary: GraphDiff['summary'];
  nodes: {
    added_by_type: Record<string, number>;
    removed_by_type: Record<string, number>;
    total_added: number;
    total_removed: number;
    total_modified: number;
  };
  edges: {
    added_by_type: Record<string, number>;
    removed_by_type: Record<string, number>;
    total_added: number;
    total_removed: number;
    total_modified: number;
  };
}

// Validation types
export interface Violation {
  violation_type: string;
  severity: 'error' | 'warning';
  entity_id: string;
  message: string;
  details: Record<string, any>;
  suggested_fix?: string;
  file_path?: string;
  line_number?: number;
  column_number?: number;
  code_snippet?: string;
}

export interface ValidationLawReport {
  law: string;
  total_violations: number;
  errors: number;
  warnings: number;
  by_type: Record<string, number>;
  violations: Violation[];
  summary?: Record<string, number>;
}

export interface ValidationReport {
  total_violations: number;
  errors: number;
  warnings: number;
  changed_nodes?: number;
  by_type: Record<string, number>;
  violations: Violation[];
  summary?: {
    signature_conservation: number;
    reference_integrity: number;
    data_flow_consistency: number;
    structural_integrity: number;
  };
  laws?: Record<string, ValidationLawReport>;
}

// Query types
export interface QueryResult {
  columns: string[];
  rows: Record<string, any>[];
  execution_time_ms: number;
}

// UI State types
export interface SelectedElement {
  type: 'node' | 'edge';
  id: string;
  data: GraphNode | GraphEdge;
}

export type ViewMode = 'graph' | 'diff' | 'validation';

export type DiffHighlightMode = 'all' | 'added' | 'removed' | 'modified' | 'none';

// Node colors by type
export const NODE_COLORS: Record<string, string> = {
  Function: '#4fc3f7',
  Class: '#81c784',
  Module: '#ffb74d',
  Variable: '#ce93d8',
  Parameter: '#90a4ae',
  CallSite: '#f48fb1',
  Type: '#ba68c8',
  Decorator: '#80deea',
  Unresolved: '#ef4444', // Red for unresolved references
};

// File diff types (from explore-codebase-frontend branch)
export interface FileDiff {
  filepath: string;
  old_hash: string;
  new_hash: string;
  diff: string;
  lines_added: number;
  lines_removed: number;
  is_binary: boolean;
  error?: string;
}

export interface FileChange {
  filepath: string;
  status: 'added' | 'modified' | 'deleted' | 'renamed' | 'copied';
  lines_added: number;
  lines_removed: number;
  is_binary: boolean;
}

// Edge colors by type (Optimized schema - removed redundant relationships)
export const EDGE_COLORS: Record<string, string> = {
  RESOLVES_TO: '#4fc3f7',  // Unified call tracking (replaces CALLS)
  INHERITS: '#81c784',
  IMPORTS: '#ffb74d',
  HAS_PARAMETER: '#90a4ae',
  HAS_TYPE: '#64b5f6',
  RETURNS_TYPE: '#64b5f6',
  DECLARES: '#ff8a65',  // Unified declarations (module + class level)
  ASSIGNS_TO: '#ce93d8',
  READS_FROM: '#b39ddb',
  REFERENCES: '#80cbc4',
  IS_SUBTYPE_OF: '#90caf9',
  HAS_DECORATOR: '#80deea',
  DECORATES: '#80deea',
  HAS_CALLSITE: '#f48fb1',
};
