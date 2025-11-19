import React, { useState } from 'react';
import { api } from '../api/client';

export const BottomPanel: React.FC = () => {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<Record<string, any>[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);

  const executeQuery = async () => {
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await api.executeQuery(query);
      // Backend returns array of records directly
      setResult(Array.isArray(response) ? response : []);

      // Add to history
      setHistory((prev) => [query, ...prev.filter((q) => q !== query)].slice(0, 50));
      setHistoryIndex(-1);
    } catch (err: any) {
      setError(err.message || 'Query execution failed');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      executeQuery();
    } else if (e.key === 'ArrowUp' && e.ctrlKey) {
      e.preventDefault();
      if (historyIndex < history.length - 1) {
        const newIndex = historyIndex + 1;
        setHistoryIndex(newIndex);
        setQuery(history[newIndex]);
      }
    } else if (e.key === 'ArrowDown' && e.ctrlKey) {
      e.preventDefault();
      if (historyIndex > 0) {
        const newIndex = historyIndex - 1;
        setHistoryIndex(newIndex);
        setQuery(history[newIndex]);
      } else if (historyIndex === 0) {
        setHistoryIndex(-1);
        setQuery('');
      }
    }
  };

  const loadExample = (example: string) => {
    setQuery(example);
  };

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Query Input */}
      <div className="p-3 bg-white border-b border-gray-200">
        <div className="flex items-start gap-2">
          <div className="flex-1">
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Enter Cypher query... (Ctrl+Enter to execute, Ctrl+↑/↓ for history)"
              className="w-full px-3 py-2 border border-gray-300 rounded font-mono text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={3}
            />
          </div>
          <button
            onClick={executeQuery}
            disabled={loading || !query.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Running...' : 'Execute'}
          </button>
        </div>

        {/* Example Queries */}
        <div className="mt-2 flex flex-wrap gap-2">
          <span className="text-xs text-gray-600">Examples:</span>
          <button
            onClick={() => loadExample('MATCH (n) RETURN n LIMIT 100')}
            className="text-xs px-2 py-1 bg-gray-100 hover:bg-gray-200 rounded"
          >
            All Nodes
          </button>
          <button
            onClick={() => loadExample('MATCH (n) WHERE n.changed = true RETURN n')}
            className="text-xs px-2 py-1 bg-gray-100 hover:bg-gray-200 rounded"
          >
            Changed Nodes
          </button>
          <button
            onClick={() => loadExample('MATCH (f:Function)-[r:CALLS]->(g:Function) RETURN f, r, g LIMIT 50')}
            className="text-xs px-2 py-1 bg-gray-100 hover:bg-gray-200 rounded"
          >
            Function Calls
          </button>
          <button
            onClick={() => loadExample('MATCH (c:CallSite)-[r:RESOLVES_TO]->(f:Function) RETURN c, r, f')}
            className="text-xs px-2 py-1 bg-gray-100 hover:bg-gray-200 rounded"
          >
            Resolved Calls
          </button>
          <button
            onClick={() => loadExample('MATCH (c:Class)-[r:INHERITS]->(b:Class) RETURN c, r, b')}
            className="text-xs px-2 py-1 bg-gray-100 hover:bg-gray-200 rounded"
          >
            Inheritance
          </button>
        </div>
      </div>

      {/* Results */}
      <div className="flex-1 overflow-auto p-3">
        {error && (
          <div className="bg-red-50 border border-red-300 rounded p-3 text-red-800">
            <div className="font-semibold mb-1">Error</div>
            <pre className="text-sm whitespace-pre-wrap font-mono">{error}</pre>
          </div>
        )}

        {result && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm text-gray-600">
              <span>
                {result.length} row{result.length !== 1 ? 's' : ''}
              </span>
            </div>

            {result.length > 0 && Object.keys(result[0]).length > 0 ? (
              <div className="bg-white border border-gray-200 rounded overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-100 border-b border-gray-200">
                      <tr>
                        {Object.keys(result[0]).map((col) => (
                          <th
                            key={col}
                            className="px-3 py-2 text-left font-semibold text-gray-700"
                          >
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.map((row, idx) => (
                        <tr
                          key={idx}
                          className="border-b border-gray-100 hover:bg-gray-50"
                        >
                          {Object.keys(result[0]).map((col) => (
                            <td key={col} className="px-3 py-2">
                              <CellValue value={row[col]} />
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : (
              <div className="text-gray-500 text-center py-8">No results</div>
            )}
          </div>
        )}

        {!result && !error && !loading && (
          <div className="text-gray-500 text-center py-8">
            Enter a Cypher query and press Execute or Ctrl+Enter
          </div>
        )}
      </div>
    </div>
  );
};

const CellValue: React.FC<{ value: any }> = ({ value }) => {
  if (value === null || value === undefined) {
    return <span className="text-gray-400 italic">null</span>;
  }

  if (typeof value === 'object') {
    // Check if it's a node
    if (value.id && value.labels && value.properties) {
      return (
        <div className="font-mono text-xs">
          <span className="text-blue-600">{value.labels[0]}</span>
          {value.properties.name && (
            <span className="ml-1 text-gray-800">: {value.properties.name}</span>
          )}
        </div>
      );
    }

    // Check if it's an edge
    if (value.id && value.type && value.from_id && value.to_id) {
      return (
        <div className="font-mono text-xs text-green-600">
          [{value.type}]
        </div>
      );
    }

    // Generic object
    return (
      <details className="cursor-pointer">
        <summary className="text-gray-600">Object</summary>
        <pre className="mt-1 text-xs bg-gray-50 p-2 rounded overflow-x-auto">
          {JSON.stringify(value, null, 2)}
        </pre>
      </details>
    );
  }

  if (typeof value === 'boolean') {
    return <span className="text-purple-600">{value.toString()}</span>;
  }

  if (typeof value === 'number') {
    return <span className="text-orange-600">{value}</span>;
  }

  return <span className="font-mono text-xs text-gray-800">{String(value)}</span>;
};
