import React, { useEffect, useState } from 'react';
import { parseDiff, Diff, Hunk } from 'react-diff-view';
import { useStore } from '../store';
import { api } from '../api/client';
import 'react-diff-view/style/index.css';

export const TextDiffView: React.FC = () => {
  const compareFrom = useStore((state) => state.compareFrom);
  const compareTo = useStore((state) => state.compareTo);
  const selectedFileForDiff = useStore((state) => state.selectedFileForDiff);
  const selectedFileDiff = useStore((state) => state.selectedFileDiff);
  const setSelectedFileDiff = useStore((state) => state.setSelectedFileDiff);
  const setError = useStore((state) => state.setError);

  const [viewType, setViewType] = useState<'split' | 'unified'>('split');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (compareFrom && compareTo && selectedFileForDiff) {
      fetchFileDiff();
    } else {
      setSelectedFileDiff(null);
    }
  }, [compareFrom, compareTo, selectedFileForDiff]);

  const fetchFileDiff = async () => {
    if (!compareFrom || !compareTo || !selectedFileForDiff) return;

    setIsLoading(true);
    try {
      const diff = await api.getFileDiff(compareFrom, compareTo, selectedFileForDiff);
      setSelectedFileDiff(diff);
    } catch (error) {
      setError(`Failed to load diff: ${(error as Error).message}`);
    } finally {
      setIsLoading(false);
    }
  };

  if (!selectedFileForDiff) {
    return (
      <div className="h-full flex items-center justify-center text-text-secondary bg-white">
        <div className="text-center">
          <p>Select a file from the list to view its diff</p>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center text-text-secondary bg-white">
        <div className="text-center">
          <p>Loading diff...</p>
          <p className="text-xs mt-2 font-mono">{selectedFileForDiff}</p>
        </div>
      </div>
    );
  }

  if (!selectedFileDiff) {
    return (
      <div className="h-full flex items-center justify-center text-text-secondary bg-white">
        <p>No diff data available</p>
      </div>
    );
  }

  if (selectedFileDiff.error) {
    return (
      <div className="h-full flex items-center justify-center text-red-600 bg-white">
        <div className="text-center">
          <p>Error loading diff</p>
          <p className="text-xs mt-2">{selectedFileDiff.error}</p>
        </div>
      </div>
    );
  }

  if (selectedFileDiff.is_binary) {
    return (
      <div className="h-full flex items-center justify-center text-text-secondary bg-white">
        <div className="text-center">
          <p>Binary file - no text diff available</p>
          <p className="text-xs mt-2 font-mono">{selectedFileDiff.filepath}</p>
        </div>
      </div>
    );
  }

  if (!selectedFileDiff.diff || selectedFileDiff.diff.trim() === '') {
    return (
      <div className="h-full flex items-center justify-center text-text-secondary bg-white">
        <div className="text-center">
          <p>No changes in this file</p>
          <p className="text-xs mt-2 font-mono">{selectedFileDiff.filepath}</p>
        </div>
      </div>
    );
  }

  let files: ReturnType<typeof parseDiff> = [];
  try {
    files = parseDiff(selectedFileDiff.diff);
  } catch (error) {
    return (
      <div className="h-full flex items-center justify-center text-red-600 bg-white">
        <div className="text-center">
          <p>Failed to parse diff</p>
          <p className="text-xs mt-2">{(error as Error).message}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-white">
      <div className="border-b border-border p-3 bg-panel-bg flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold font-mono text-text-primary">
            {selectedFileDiff.filepath}
          </h3>
          <div className="flex gap-3 mt-1 text-xs">
            {selectedFileDiff.lines_added > 0 && (
              <span className="text-green-600">+{selectedFileDiff.lines_added}</span>
            )}
            {selectedFileDiff.lines_removed > 0 && (
              <span className="text-red-600">-{selectedFileDiff.lines_removed}</span>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setViewType('split')}
            className={`px-3 py-1 rounded text-sm transition-colors ${
              viewType === 'split'
                ? 'bg-accent text-white'
                : 'bg-white text-text-secondary hover:text-text-primary border border-border'
            }`}
          >
            Split
          </button>
          <button
            onClick={() => setViewType('unified')}
            className={`px-3 py-1 rounded text-sm transition-colors ${
              viewType === 'unified'
                ? 'bg-accent text-white'
                : 'bg-white text-text-secondary hover:text-text-primary border border-border'
            }`}
          >
            Unified
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto bg-white">
        {files.map((file, index) => (
          <Diff key={index} viewType={viewType} diffType={file.type} hunks={file.hunks}>
            {(hunks) =>
              hunks.map((hunk) => <Hunk key={hunk.content} hunk={hunk} />)
            }
          </Diff>
        ))}
      </div>
    </div>
  );
};
