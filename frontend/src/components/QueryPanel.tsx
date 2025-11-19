import { useState } from 'react';
import { Play, History, Trash2 } from 'lucide-react';
import { useStore } from '../store';
import { api } from '../api/client';

const EXAMPLE_QUERIES = [
  {
    name: 'All Functions',
    query: 'MATCH (f:Function) RETURN f.name, f.signature LIMIT 25',
  },
  {
    name: 'Function Calls',
    query: 'MATCH (f:Function)-[r:CALLS]->(t:Function) RETURN f.name, r.type, t.name LIMIT 25',
  },
  {
    name: 'Classes and Methods',
    query: 'MATCH (c:Class)-[:DEFINES]->(m:Function) RETURN c.name, collect(m.name) as methods',
  },
  {
    name: 'Complex Dependencies',
    query: 'MATCH path = (f:Function)-[:CALLS*2..3]->(t:Function) RETURN path LIMIT 10',
  },
];

export function QueryPanel() {
  const {
    sidebarWidth,
    queryHistory,
    addQueryToHistory,
    clearQueryHistory,
    setGraphData,
    setIsLoading,
    setError,
  } = useStore();

  const [query, setQuery] = useState('');
  const [queryResult, setQueryResult] = useState<any>(null);

  const executeQuery = async () => {
    if (!query.trim()) return;

    setIsLoading(true);
    setQueryResult(null);
    try {
      const result = await api.executeQuery(query);
      addQueryToHistory(query);
      setQueryResult(result);

      // Try to extract graph data if possible
      if (result.rows && result.rows.length > 0) {
        // Check if result contains graph data
        const nodes = [];
        const edges = [];

        for (const row of result.rows) {
          for (const value of Object.values(row)) {
            if (value && typeof value === 'object') {
              // Check if it's a node
              if ('labels' in value && 'properties' in value) {
                nodes.push(value);
              }
              // Check if it's an edge
              if ('source' in value && 'target' in value && 'type' in value) {
                edges.push(value);
              }
            }
          }
        }

        if (nodes.length > 0) {
          setGraphData({ nodes, edges });
        }
      }
    } catch (error) {
      setError((error as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  const loadExample = (exampleQuery: string) => {
    setQuery(exampleQuery);
  };

  const loadFromHistory = (historicalQuery: string) => {
    setQuery(historicalQuery);
  };

  return (
    <div
      className="h-full bg-panel-bg border-r border-border flex flex-col"
      style={{ width: sidebarWidth }}
    >
      {/* Header */}
      <div className="p-3 border-b border-border">
        <span className="font-semibold text-sm uppercase text-text-secondary">
          Cypher Query
        </span>
      </div>

      {/* Query Input */}
      <div className="p-3 border-b border-border">
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Enter Cypher query..."
          className="w-full h-24 px-2 py-1.5 text-xs font-mono bg-graph-bg border border-border rounded focus:outline-none focus:border-accent resize-none"
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
              executeQuery();
            }
          }}
        />
        <div className="flex gap-2 mt-2">
          <button
            onClick={executeQuery}
            disabled={!query.trim()}
            className="flex-1 flex items-center justify-center gap-2 px-3 py-1.5 text-xs font-medium bg-accent text-white rounded hover:bg-accent/80 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Play size={12} />
            Run Query (Ctrl+Enter)
          </button>
        </div>
      </div>

      {/* Example Queries */}
      <div className="p-3 border-b border-border">
        <div className="text-xs font-semibold text-text-secondary mb-2">EXAMPLES</div>
        <div className="space-y-1">
          {EXAMPLE_QUERIES.map((example, index) => (
            <button
              key={index}
              onClick={() => loadExample(example.query)}
              className="w-full text-left px-2 py-1.5 text-xs rounded hover:bg-border/50 transition-colors"
            >
              <div className="font-medium text-text-primary">{example.name}</div>
              <div className="text-text-secondary font-mono truncate">{example.query}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Query History */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-3">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-text-secondary">
              <History size={12} />
              HISTORY
            </div>
            {queryHistory.length > 0 && (
              <button
                onClick={clearQueryHistory}
                className="p-1 hover:bg-border rounded"
                title="Clear history"
              >
                <Trash2 size={12} />
              </button>
            )}
          </div>

          {queryHistory.length === 0 ? (
            <div className="text-xs text-text-secondary text-center py-4">
              No query history
            </div>
          ) : (
            <div className="space-y-1">
              {queryHistory.map((historicalQuery, index) => (
                <button
                  key={index}
                  onClick={() => loadFromHistory(historicalQuery)}
                  className="w-full text-left px-2 py-1.5 text-xs font-mono rounded hover:bg-border/50 transition-colors text-text-secondary truncate"
                  title={historicalQuery}
                >
                  {historicalQuery}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Query Result */}
      {queryResult && (
        <div className="p-3 border-t border-border bg-graph-bg">
          <div className="text-xs font-semibold text-text-secondary mb-2">
            RESULT ({queryResult.rows.length} rows in {queryResult.execution_time_ms}ms)
          </div>
          <div className="max-h-32 overflow-auto text-xs font-mono">
            <pre className="text-text-secondary">{JSON.stringify(queryResult.rows, null, 2)}</pre>
          </div>
        </div>
      )}
    </div>
  );
}
