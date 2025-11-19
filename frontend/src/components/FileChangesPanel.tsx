import React, { useEffect } from 'react';
import { useStore } from '../store';
import { api } from '../api/client';
import { File, FileX, FilePlus, FileEdit } from 'lucide-react';

export const FileChangesPanel: React.FC = () => {
  const compareFrom = useStore((state) => state.compareFrom);
  const compareTo = useStore((state) => state.compareTo);
  const changedFiles = useStore((state) => state.changedFiles);
  const selectedFileForDiff = useStore((state) => state.selectedFileForDiff);
  const setChangedFiles = useStore((state) => state.setChangedFiles);
  const setSelectedFileForDiff = useStore((state) => state.setSelectedFileForDiff);
  const setError = useStore((state) => state.setError);

  useEffect(() => {
    if (compareFrom && compareTo) {
      fetchChangedFiles();
    }
  }, [compareFrom, compareTo]);

  const fetchChangedFiles = async () => {
    if (!compareFrom || !compareTo) return;

    try {
      const result = await api.listChangedFiles(compareFrom, compareTo);
      setChangedFiles(result.files);
    } catch (error) {
      setError(`Failed to load changed files: ${(error as Error).message}`);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'added':
        return <FilePlus size={16} className="text-green-500" />;
      case 'deleted':
        return <FileX size={16} className="text-red-500" />;
      case 'modified':
        return <FileEdit size={16} className="text-yellow-500" />;
      default:
        return <File size={16} className="text-gray-500" />;
    }
  };

  if (!compareFrom || !compareTo) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500 p-4 text-center">
        Select two commits to view changed files
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-panel-bg">
      <div className="border-b border-border p-3">
        <h3 className="text-sm font-semibold text-text-primary">
          Changed Files ({changedFiles.length})
        </h3>
      </div>

      <div className="flex-1 overflow-y-auto">
        {changedFiles.length === 0 ? (
          <div className="p-4 text-center text-text-secondary">
            No files changed
          </div>
        ) : (
          <ul className="divide-y divide-border">
            {changedFiles.map((file) => (
              <li
                key={file.filepath}
                className={`p-3 hover:bg-hover cursor-pointer transition-colors ${
                  selectedFileForDiff === file.filepath ? 'bg-accent/10 border-l-2 border-accent' : ''
                }`}
                onClick={() => setSelectedFileForDiff(file.filepath)}
              >
                <div className="flex items-start gap-2">
                  {getStatusIcon(file.status)}
                  <div className="flex-1 min-w-0">
                    <div className="font-mono text-sm truncate text-text-primary" title={file.filepath}>
                      {file.filepath}
                    </div>
                    <div className="flex gap-3 mt-1 text-xs">
                      {file.lines_added > 0 && (
                        <span className="text-green-600">
                          +{file.lines_added}
                        </span>
                      )}
                      {file.lines_removed > 0 && (
                        <span className="text-red-600">
                          -{file.lines_removed}
                        </span>
                      )}
                      {file.is_binary && (
                        <span className="text-gray-500">(binary)</span>
                      )}
                    </div>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};
