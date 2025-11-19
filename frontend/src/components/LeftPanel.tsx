import { useState } from 'react';
import { format } from 'date-fns';
import {
  History,
  ChevronRight,
  ChevronDown,
  GitCommit as GitCommitIcon,
  Loader2,
  Check,
  AlertCircle,
} from 'lucide-react';
import { useStore } from '../store';
import { api, ApiError } from '../api/client';
import type { GitCommit } from '../types';

export function LeftPanel() {
  const {
    commits,
    selectedCommit,
    setSelectedCommit,
    setCompareFrom,
    setCompareTo,
    setViewMode,
    setGraphData,
    setDiffData,
    setCompareFromGraph,
    setCompareToGraph,
    setIsLoading,
    setError,
    leftPanelWidth,
    indexingCommit,
    setIndexingCommit,
    markCommitIndexed,
  } = useStore();

  const [expandedCommits, setExpandedCommits] = useState<Set<string>>(new Set());
  const [compareMode, setCompareMode] = useState(false);
  const [firstSelected, setFirstSelected] = useState<string | null>(null);

  const fetchCommitGraph = async (hash: string) => {
    try {
      // Try to get the graph - it will auto-index if needed
      return await api.getCommitGraph(hash);
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw error;
    }
  };

  const handleCommitClick = async (commit: GitCommit) => {
    if (compareMode) {
      if (!firstSelected) {
        setFirstSelected(commit.hash);
        setCompareFrom(null);
        setCompareTo(null);
        setDiffData(null);
        setCompareFromGraph(null);
        setCompareToGraph(null);
      } else {
        const firstHash = firstSelected;
        const secondHash = commit.hash;
        setIsLoading(true);
        try {
          // Index and fetch both commits
          if (!commits.find(c => c.hash === firstHash)?.indexed) {
            setIndexingCommit(firstHash);
            await api.indexCommit(firstHash);
            markCommitIndexed(firstHash);
          }
          const beforeGraph = await fetchCommitGraph(firstHash);

          if (!commit.indexed) {
            setIndexingCommit(secondHash);
            await api.indexCommit(secondHash);
            markCommitIndexed(secondHash);
          }
          const afterGraph = await fetchCommitGraph(secondHash);
          setIndexingCommit(null);

          const diff = await api.compareCommits(firstHash, secondHash);
          setCompareFrom(firstHash);
          setCompareTo(secondHash);
          setDiffData(diff);
          setCompareFromGraph(beforeGraph);
          setCompareToGraph(afterGraph);
          setViewMode('diff');
        } catch (error) {
          setError((error as Error).message);
        } finally {
          setCompareMode(false);
          setFirstSelected(null);
          setIsLoading(false);
          setIndexingCommit(null);
        }
      }
    } else {
      setSelectedCommit(commit.hash);
      setIsLoading(true);
      try {
        // Index if not already indexed
        if (!commit.indexed) {
          setIndexingCommit(commit.hash);
          await api.indexCommit(commit.hash);
          markCommitIndexed(commit.hash);
          setIndexingCommit(null);
        }
        const graphData = await fetchCommitGraph(commit.hash);
        if (graphData) {
          setGraphData(graphData);
        }
      } catch (error) {
        setError((error as Error).message);
      } finally {
        setIsLoading(false);
        setIndexingCommit(null);
      }
    }
  };

  const toggleExpanded = (hash: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setExpandedCommits((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(hash)) {
        newSet.delete(hash);
      } else {
        newSet.add(hash);
      }
      return newSet;
    });
  };

  return (
    <div
      className="h-full bg-panel-bg border-r border-border flex flex-col"
      style={{ width: leftPanelWidth }}
    >
      {/* Header */}
      <div className="p-3 border-b border-border">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <History size={16} />
            <span className="font-semibold text-sm">Git History</span>
          </div>
          <span className="text-xs text-text-secondary">{commits.length} commits</span>
        </div>
        <button
          onClick={() => {
            setCompareMode(!compareMode);
            setFirstSelected(null);
          }}
          className={`w-full py-1.5 px-3 rounded text-xs font-medium transition-colors ${
            compareMode
              ? 'bg-accent text-white'
              : 'bg-graph-bg text-text-secondary hover:text-text-primary'
          }`}
        >
          {compareMode
            ? firstSelected
              ? 'Select second commit'
              : 'Select first commit'
            : 'Compare Commits'}
        </button>
      </div>

      {/* Commit List */}
      <div className="flex-1 overflow-y-auto">
        {commits.length === 0 ? (
          <div className="p-4 text-center text-text-secondary text-sm">
            No commits found.
            <br />
            Initialize a git repository to track history.
          </div>
        ) : (
          <div className="py-2">
            {commits.map((commit, index) => (
              <CommitItem
                key={commit.hash}
                commit={commit}
                isSelected={selectedCommit === commit.hash}
                isFirstInCompare={firstSelected === commit.hash}
                isExpanded={expandedCommits.has(commit.hash)}
                isFirst={index === 0}
                isLast={index === commits.length - 1}
                isIndexing={indexingCommit === commit.hash}
                onClick={() => handleCommitClick(commit)}
                onToggleExpand={(e) => toggleExpanded(commit.hash, e)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

interface CommitItemProps {
  commit: GitCommit;
  isSelected: boolean;
  isFirstInCompare: boolean;
  isExpanded: boolean;
  isFirst: boolean;
  isLast: boolean;
  isIndexing: boolean;
  onClick: () => void;
  onToggleExpand: (e: React.MouseEvent) => void;
}

function CommitItem({
  commit,
  isSelected,
  isFirstInCompare,
  isExpanded,
  isFirst,
  isLast,
  isIndexing,
  onClick,
  onToggleExpand,
}: CommitItemProps) {
  return (
    <div
      className={`group relative px-3 py-2 cursor-pointer transition-colors ${
        isSelected
          ? 'bg-accent/20 border-l-2 border-accent'
          : isFirstInCompare
          ? 'bg-diff-modified/20 border-l-2 border-diff-modified'
          : 'hover:bg-border/50 border-l-2 border-transparent'
      }`}
      onClick={onClick}
    >
      {/* Timeline connector */}
      <div className="absolute left-6 top-0 bottom-0 w-px bg-border">
        {isFirst && <div className="absolute top-0 left-0 w-full h-2 bg-panel-bg" />}
        {isLast && <div className="absolute bottom-0 left-0 w-full h-2 bg-panel-bg" />}
      </div>

      {/* Commit dot */}
      <div className={`absolute left-5 top-1/2 -translate-y-1/2 w-3 h-3 rounded-full border-2 border-panel-bg z-10 ${
        commit.indexed ? 'bg-diff-added' : 'bg-text-secondary'
      }`} />

      {/* Content */}
      <div className="ml-6 pl-2">
        <div className="flex items-center justify-between">
          <button
            onClick={onToggleExpand}
            className="p-0.5 hover:bg-border rounded"
          >
            {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          </button>
          <div className="flex-1 ml-1">
            <div className="text-xs font-medium truncate flex items-center gap-1">
              {commit.message.split('\n')[0]}
              {isIndexing && <Loader2 size={10} className="animate-spin text-accent" />}
            </div>
            <div className="text-xs text-text-secondary flex items-center gap-2">
              <span>{format(new Date(commit.date), 'MMM d, HH:mm')}</span>
              {commit.indexed ? (
                <Check size={10} className="text-diff-added" />
              ) : (
                <AlertCircle size={10} className="text-text-secondary" />
              )}
            </div>
          </div>
        </div>

        {isExpanded && (
          <div className="mt-2 text-xs space-y-1">
            <div className="flex items-center gap-2 text-text-secondary">
              <GitCommitIcon size={10} />
              <span className="font-mono">{commit.short_hash}</span>
            </div>
            <div className="text-text-secondary">
              by {commit.author}
            </div>
            <div className="flex items-center gap-1">
              {commit.indexed ? (
                <span className="text-diff-added flex items-center gap-1">
                  <Check size={10} />
                  Indexed
                </span>
              ) : (
                <span className="text-text-secondary flex items-center gap-1">
                  <AlertCircle size={10} />
                  Not indexed (click to index)
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
