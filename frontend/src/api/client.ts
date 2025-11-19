import type {
  GraphData,
  Snapshot,
  SnapshotStatistics,
  GraphDiff,
  DiffSummary,
  ValidationReport,
  ValidationLawReport,
  QueryResult,
  GitCommit,
  CommitInfo,
  CommitDiff,
} from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

class ApiClient {
  private async fetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
      },
      ...options,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new ApiError(errorText || `API error: ${response.status}`, response.status);
    }

    return response.json();
  }

  // Graph queries
  async getGraph(limit?: number): Promise<GraphData> {
    const params = limit ? `?limit=${limit}` : '';
    return this.fetch(`/graph${params}`);
  }

  async executeQuery(query: string): Promise<QueryResult> {
    return this.fetch('/graph/query', {
      method: 'POST',
      body: JSON.stringify({ query }),
    });
  }

  async getNodeById(nodeId: string): Promise<GraphData> {
    return this.fetch(`/graph/node/${encodeURIComponent(nodeId)}`);
  }

  async getNodeNeighbors(nodeId: string, depth?: number): Promise<GraphData> {
    const params = depth ? `?depth=${depth}` : '';
    return this.fetch(`/graph/node/${encodeURIComponent(nodeId)}/neighbors${params}`);
  }

  // Statistics
  async getStatistics(): Promise<Record<string, number>> {
    return this.fetch('/graph/statistics');
  }

  // Snapshots
  async listSnapshots(): Promise<Snapshot[]> {
    const response: any = await this.fetch('/snapshots');
    // Backend returns { snapshots: [...], count: N }
    return response.snapshots || [];
  }

  async createSnapshot(description: string): Promise<{ snapshot_id: string }> {
    return this.fetch(`/snapshots/create?description=${encodeURIComponent(description)}`, {
      method: 'POST',
    });
  }

  async getSnapshot(snapshotId: string): Promise<SnapshotStatistics> {
    return this.fetch(`/snapshots/${snapshotId}`);
  }

  async deleteSnapshot(snapshotId: string): Promise<void> {
    await this.fetch(`/snapshots/${snapshotId}`, {
      method: 'DELETE',
    });
  }

  async getSnapshotGraph(snapshotId: string): Promise<GraphData> {
    return this.fetch(`/snapshots/${snapshotId}/graph`);
  }

  // Diff
  async compareSnapshots(oldId: string, newId: string): Promise<GraphDiff> {
    return this.fetch(`/snapshots/compare?old_snapshot_id=${oldId}&new_snapshot_id=${newId}`, {
      method: 'POST',
    });
  }

  async getDiffSummary(oldId: string, newId: string): Promise<DiffSummary> {
    return this.fetch(`/snapshots/compare?old_snapshot_id=${oldId}&new_snapshot_id=${newId}`, {
      method: 'POST',
    });
  }

  // Validation
  async validate(incremental?: boolean, includePyright?: boolean): Promise<ValidationReport> {
    const params = new URLSearchParams();
    if (incremental) params.append('incremental', 'true');
    if (includePyright) params.append('pyright', 'true');
    return this.fetch(`/validation?${params.toString()}`, {
      method: 'POST',
    });
  }

  async validateStructural(): Promise<ValidationLawReport> {
    return this.fetch('/validation/structural', {
      method: 'POST',
    });
  }

  async validateReference(): Promise<ValidationLawReport> {
    return this.fetch('/validation/reference', {
      method: 'POST',
    });
  }

  async validateTyping(includePyright?: boolean): Promise<ValidationLawReport> {
    const params = new URLSearchParams();
    if (includePyright) params.append('pyright', 'true');
    const suffix = params.toString() ? `?${params.toString()}` : '';
    return this.fetch(`/validation/typing${suffix}`, {
      method: 'POST',
    });
  }

  async getValidationReport(): Promise<ValidationReport> {
    return this.fetch('/validation/report');
  }

  // Incremental operations
  async markFilesChanged(files: string[]): Promise<{ marked: number }> {
    return this.fetch('/mark-changed', {
      method: 'POST',
      body: JSON.stringify({ files }),
    });
  }

  async propagateChanges(): Promise<{ propagated: number }> {
    return this.fetch('/propagate-changes', {
      method: 'POST',
    });
  }

  async clearChangedFlags(): Promise<{ cleared: number }> {
    return this.fetch('/clear-changed', {
      method: 'POST',
    });
  }

  async getChangedNodes(): Promise<GraphData> {
    return this.fetch('/changed-nodes');
  }

  // Index operations
  async indexFile(filePath: string): Promise<{ indexed: boolean }> {
    return this.fetch('/index', {
      method: 'POST',
      body: JSON.stringify({ file_path: filePath }),
    });
  }

  async indexDirectory(dirPath: string): Promise<{ files_indexed: number }> {
    return this.fetch('/index/directory', {
      method: 'POST',
      body: JSON.stringify({ directory: dirPath }),
    });
  }

  // Git commit operations
  async listCommits(limit?: number): Promise<GitCommit[]> {
    const params = limit ? `?limit=${limit}` : '';
    const response: any = await this.fetch(`/commits${params}`);
    return response.commits || [];
  }

  async getCommit(commitHash: string): Promise<CommitInfo> {
    return this.fetch(`/commits/${commitHash}`);
  }

  async indexCommit(commitHash: string): Promise<{ success: boolean; data: any }> {
    return this.fetch(`/commits/${commitHash}/index`, {
      method: 'POST',
    });
  }

  async getCommitGraph(commitHash: string): Promise<GraphData> {
    return this.fetch(`/commits/${commitHash}/graph`);
  }

  async compareCommits(oldHash: string, newHash: string): Promise<CommitDiff> {
    return this.fetch(`/commits/diff?old=${oldHash}&new=${newHash}`);
  }

  async getFileDiff(oldHash: string, newHash: string, filepath: string): Promise<{
    filepath: string;
    old_hash: string;
    new_hash: string;
    diff: string;
    lines_added: number;
    lines_removed: number;
    is_binary: boolean;
  }> {
    return this.fetch(
      `/commits/diff/file?old=${oldHash}&new=${newHash}&filepath=${encodeURIComponent(filepath)}`
    );
  }

  async listChangedFiles(oldHash: string, newHash: string): Promise<{
    files: Array<{
      filepath: string;
      status: string;
      lines_added: number;
      lines_removed: number;
      is_binary: boolean;
    }>;
    count: number;
  }> {
    return this.fetch(`/commits/diff/files?old=${oldHash}&new=${newHash}`);
  }

  async deleteCommitSnapshot(commitHash: string): Promise<void> {
    await this.fetch(`/commits/${commitHash}/snapshot`, {
      method: 'DELETE',
    });
  }

  // File operations
  async listFiles(directory: string, recursive: boolean = false): Promise<any> {
    const params = recursive ? `&recursive=true` : '';
    return this.fetch(`/files?directory=${encodeURIComponent(directory)}${params}`);
  }

  async getFileGraph(filePath: string): Promise<GraphData> {
    return this.fetch(`/files/graph?file_path=${encodeURIComponent(filePath)}`);
  }

  async getFileHistory(filePath: string, limit?: number): Promise<{
    file_path: string;
    relative_path: string;
    commits: GitCommit[];
    count: number;
  }> {
    const params = limit ? `&limit=${limit}` : '';
    return this.fetch(`/files/history?file_path=${encodeURIComponent(filePath)}${params}`);
  }

  async getFileAtCommit(filePath: string, commitHash: string): Promise<{
    file_path: string;
    commit_hash: string;
    graph: GraphData;
  }> {
    return this.fetch(
      `/files/at-commit?file_path=${encodeURIComponent(filePath)}&commit_hash=${commitHash}`
    );
  }
}

export const api = new ApiClient();
