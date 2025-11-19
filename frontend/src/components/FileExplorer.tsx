import { useState, useEffect, useMemo, useCallback } from 'react';
import { useStore } from '../store';
import { api } from '../api/client';
import { Folder, FolderOpen, File, FileCode, ChevronRight, ChevronDown, RefreshCw, Layout } from 'lucide-react';
import AutoSizer from 'react-virtualized-auto-sizer';
import { FixedSizeList as List, ListChildComponentProps } from 'react-window';

interface FileTreeNode {
  name: string;
  path: string;
  isDirectory: boolean;
  children?: FileTreeNode[];
  isPython?: boolean;
}

interface VisibleNode {
  node: FileTreeNode;
  depth: number;
}

interface RowData {
  items: VisibleNode[];
  selectedFiles: string[];
  expandedDirectories: Set<string>;
  toggleDirectory: (path: string) => void;
  onFileClick: (node: FileTreeNode) => void;
}

const ROW_HEIGHT = 30;

export function FileExplorer() {
  const {
    rootDirectory,
    setRootDirectory,
    selectedFiles,
    setSelectedFiles,
    setGraphData,
    setIsLoading,
    setError,
    showRightPanel,
    toggleRightPanel,
    expandedDirectories,
    toggleDirectory,
  } = useStore();

  const [fileTree, setFileTree] = useState<FileTreeNode[]>([]);

  const loadDirectoryTree = useCallback(async () => {
    if (!rootDirectory) {
      setFileTree([]);
      return;
    }

    try {
      setIsLoading(true);
      const result = await api.listFiles(rootDirectory, true);

      const convertNode = (item: any): FileTreeNode => {
        const node: FileTreeNode = {
          name: item.name,
          path: item.path,
          isDirectory: item.is_directory,
          isPython: item.is_python,
        };

        if (item.is_directory && item.children) {
          node.children = item.children.map(convertNode);
        }

        return node;
      };

      const rootNode: FileTreeNode = {
        name: rootDirectory.split(/[/\\]/).pop() || rootDirectory,
        path: rootDirectory,
        isDirectory: true,
        children: result.tree.map(convertNode),
      };

      setFileTree([rootNode]);
    } catch (error) {
      console.error('Error loading directory tree:', error);
      setError((error as Error).message);
    } finally {
      setIsLoading(false);
    }
  }, [rootDirectory, setError, setIsLoading]);

  useEffect(() => {
    loadDirectoryTree();
  }, [loadDirectoryTree]);

  const handleSelectFolder = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.webkitdirectory = true;
    input.multiple = true;

    input.onchange = (e: Event) => {
      const target = e.target as HTMLInputElement;
      if (target.files && target.files.length > 0) {
        const firstFile = target.files[0];
        const fullPath = (firstFile as any).path || firstFile.webkitRelativePath;

        if (fullPath) {
          const pathParts = fullPath.split(/[/\\]/);
          pathParts.pop();
          const dirPath = pathParts.join('/');

          if ((firstFile as any).path) {
            const fullDirPath = pathParts.join('/');
            setRootDirectory(fullDirPath);
          } else {
            setRootDirectory(dirPath || fullPath);
          }
        }
      }
    };

    input.click();
  };

  const handleFileClick = useCallback(
    async (node: FileTreeNode) => {
      if (node.isDirectory) {
        toggleDirectory(node.path);
        return;
      }

      if (!node.isPython) {
        setError('Only Python files (.py) support graph visualization');
        return;
      }

      const isSelected = selectedFiles.includes(node.path);

      if (isSelected) {
        setSelectedFiles(selectedFiles.filter((f) => f !== node.path));
      } else {
        setSelectedFiles([...selectedFiles, node.path]);
        setIsLoading(true);
        try {
          const graph = await api.getFileGraph(node.path);
          setGraphData(graph);
        } catch (error) {
          setError((error as Error).message);
        } finally {
          setIsLoading(false);
        }
      }
    },
    [selectedFiles, setError, setGraphData, setIsLoading, setSelectedFiles, toggleDirectory]
  );

  const visibleNodes = useMemo<VisibleNode[]>(() => {
    const result: VisibleNode[] = [];

    const visit = (node: FileTreeNode, depth: number) => {
      result.push({ node, depth });
      if (node.children && expandedDirectories.has(node.path)) {
        node.children.forEach((child) => visit(child, depth + 1));
      }
    };

    fileTree.forEach((node) => visit(node, 0));
    return result;
  }, [expandedDirectories, fileTree]);

  const rowRenderer = useCallback(
    ({ index, style, data }: ListChildComponentProps<RowData>) => {
      const { items, selectedFiles: selected, expandedDirectories: expanded, toggleDirectory: toggleDir, onFileClick } = data;
      const { node, depth } = items[index];
      const isExpanded = expanded.has(node.path);
      const isSelected = selected.includes(node.path);
      const paddingLeft = depth * 16 + 8;

      return (
        <div
          style={style}
          className={`flex items-center text-sm cursor-pointer px-2 ${
            isSelected ? 'bg-blue-600/20 text-blue-100' : 'text-gray-200 hover:bg-white/5'
          }`}
          onClick={() => onFileClick(node)}
        >
          <div style={{ paddingLeft }} className="flex items-center gap-2 w-full">
            {node.isDirectory ? (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  toggleDir(node.path);
                }}
                className="text-gray-400 hover:text-white"
              >
                {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              </button>
            ) : (
              <div className="w-4" />
            )}
            {node.isDirectory ? (
              isExpanded ? (
                <FolderOpen size={16} className="text-amber-400 flex-shrink-0" />
              ) : (
                <Folder size={16} className="text-amber-300 flex-shrink-0" />
              )
            ) : node.isPython || node.name.endsWith('.py') ? (
              <FileCode size={16} className="text-green-400 flex-shrink-0" />
            ) : (
              <File size={16} className="text-gray-400 flex-shrink-0" />
            )}
            <span className="truncate">{node.name}</span>
          </div>
        </div>
      );
    },
    []
  );

  return (
    <div className="flex flex-col h-full bg-[#1f1f1f] border-r border-black/40">
      <div className="p-3 border-b border-black/60">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-gray-200">File Explorer</h2>
          <div className="flex items-center gap-2">
            <button
              onClick={handleSelectFolder}
              className="p-1 rounded bg-blue-600 hover:bg-blue-500 text-white"
              title="Select folder"
            >
              <Layout size={16} />
            </button>
            <button
              onClick={loadDirectoryTree}
              className="p-1 rounded bg-gray-700 hover:bg-gray-600 text-white"
              title="Refresh"
            >
              <RefreshCw size={16} />
            </button>
          </div>
        </div>

        <div className="space-y-2">
          <div className="text-xs text-gray-400 break-all">{rootDirectory || 'No directory selected'}</div>
          <button
            onClick={toggleRightPanel}
            className="w-full text-xs py-1 rounded border border-white/10 text-gray-200 hover:bg-white/5"
          >
            {showRightPanel ? 'Hide Details' : 'Show Details'}
          </button>
        </div>
      </div>

      <div className="flex-1 min-h-0">
        {visibleNodes.length === 0 ? (
          <div className="h-full flex items-center justify-center text-gray-500 text-sm px-4 text-center">
            Select a repository folder to explore files.
          </div>
        ) : (
          <AutoSizer>
            {({ height, width }) => (
              <List
                height={height}
                width={width}
                itemCount={visibleNodes.length}
                itemSize={ROW_HEIGHT}
                itemData={{
                  items: visibleNodes,
                  selectedFiles,
                  expandedDirectories,
                  toggleDirectory,
                  onFileClick: handleFileClick,
                } as RowData}
              >
                {rowRenderer}
              </List>
            )}
          </AutoSizer>
        )}
      </div>
    </div>
  );
}
