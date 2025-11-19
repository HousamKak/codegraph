import { useEffect, useRef, useCallback } from 'react';
import cytoscape from 'cytoscape';
import dagre from 'cytoscape-dagre';
import { useStore } from '../store';
import { NODE_COLORS, EDGE_COLORS } from '../types';

// Register dagre layout
cytoscape.use(dagre);

export function GraphView() {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);

  const { graphData, setSelectedElement, diffData, diffHighlightMode, viewMode } = useStore();

  // Initialize Cytoscape
  useEffect(() => {
    if (!containerRef.current) return;

    cyRef.current = cytoscape({
      container: containerRef.current,
      style: [
        // Node styles
        {
          selector: 'node',
          style: {
            'background-color': '#666',
            label: 'data(label)',
            color: '#fff',
            'text-valign': 'center',
            'text-halign': 'center',
            'font-size': '10px',
            'text-outline-color': '#000',
            'text-outline-width': 1,
            width: 40,
            height: 40,
          },
        },
        // Node type colors
        ...Object.entries(NODE_COLORS).map(([type, color]) => ({
          selector: `node[type="${type}"]`,
          style: {
            'background-color': color,
          },
        })),
        // Edge styles
        {
          selector: 'edge',
          style: {
            width: 2,
            'line-color': '#666',
            'target-arrow-color': '#666',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'font-size': '8px',
            color: '#888',
          },
        },
        // Edge type colors
        ...Object.entries(EDGE_COLORS).map(([type, color]) => ({
          selector: `edge[type="${type}"]`,
          style: {
            'line-color': color,
            'target-arrow-color': color,
          },
        })),
        // Selected styles
        {
          selector: ':selected',
          style: {
            'border-width': 3,
            'border-color': '#fff',
          },
        },
        // Diff highlighting
        {
          selector: '.diff-added',
          style: {
            'border-width': 4,
            'border-color': '#2ea043',
            'background-opacity': 1,
          },
        },
        {
          selector: '.diff-removed',
          style: {
            'border-width': 4,
            'border-color': '#f85149',
            'background-opacity': 0.5,
          },
        },
        {
          selector: '.diff-modified',
          style: {
            'border-width': 4,
            'border-color': '#d29922',
          },
        },
        {
          selector: '.faded',
          style: {
            opacity: 0.2,
          },
        },
      ],
      layout: {
        name: 'dagre',
        rankDir: 'TB',
        nodeSep: 50,
        rankSep: 100,
      },
      minZoom: 0.1,
      maxZoom: 3,
      wheelSensitivity: 0.3,
    });

    // Click handlers
    cyRef.current.on('tap', 'node', (event) => {
      const node = event.target;
      setSelectedElement({
        type: 'node',
        id: node.id(),
        data: {
          id: node.id(),
          labels: [node.data('type')],
          properties: node.data(),
        },
      });
    });

    cyRef.current.on('tap', 'edge', (event) => {
      const edge = event.target;
      setSelectedElement({
        type: 'edge',
        id: edge.id(),
        data: {
          id: edge.id(),
          source: edge.source().id(),
          target: edge.target().id(),
          type: edge.data('type'),
          properties: edge.data(),
        },
      });
    });

    cyRef.current.on('tap', (event) => {
      if (event.target === cyRef.current) {
        setSelectedElement(null);
      }
    });

    return () => {
      cyRef.current?.destroy();
    };
  }, [setSelectedElement]);

  // Update graph data
  useEffect(() => {
    if (!cyRef.current || !graphData) return;

    const cy = cyRef.current;

    // Clear existing elements
    cy.elements().remove();

    // Add nodes
    const nodes = graphData.nodes.map((node) => ({
      group: 'nodes' as const,
      data: {
        id: node.id,
        label: node.properties.name || node.id.split(':').pop(),
        type: node.labels[0],
        ...node.properties,
      },
    }));

    // Add edges
    const edges = graphData.edges.map((edge, index) => ({
      group: 'edges' as const,
      data: {
        id: edge.id || `edge-${index}`,
        source: edge.source,
        target: edge.target,
        type: edge.type,
        ...edge.properties,
      },
    }));

    cy.add([...nodes, ...edges]);

    // Apply layout
    cy.layout({
      name: 'dagre',
      rankDir: 'TB',
      nodeSep: 50,
      rankSep: 100,
      animate: true,
      animationDuration: 500,
    }).run();

    // Fit to viewport
    cy.fit(undefined, 50);
  }, [graphData]);

  // Apply diff highlighting
  useEffect(() => {
    if (!cyRef.current || !diffData || viewMode !== 'graph') return;

    const cy = cyRef.current;

    // Reset all classes
    cy.elements().removeClass('diff-added diff-removed diff-modified faded');

    if (diffHighlightMode === 'none') return;

    // Create sets for quick lookup
    const addedNodeIds = new Set(diffData.nodes.added.map((n) => n.id));
    const removedNodeIds = new Set(diffData.nodes.removed.map((n) => n.id));
    const modifiedNodeIds = new Set(diffData.nodes.modified.map((n) => n.id));

    // Apply highlighting
    cy.nodes().forEach((node) => {
      const id = node.id();
      if (addedNodeIds.has(id) && (diffHighlightMode === 'all' || diffHighlightMode === 'added')) {
        node.addClass('diff-added');
      } else if (
        removedNodeIds.has(id) &&
        (diffHighlightMode === 'all' || diffHighlightMode === 'removed')
      ) {
        node.addClass('diff-removed');
      } else if (
        modifiedNodeIds.has(id) &&
        (diffHighlightMode === 'all' || diffHighlightMode === 'modified')
      ) {
        node.addClass('diff-modified');
      } else if (diffHighlightMode !== 'all') {
        node.addClass('faded');
      }
    });
  }, [diffData, diffHighlightMode, viewMode]);

  // Toolbar actions
  const handleZoomIn = useCallback(() => {
    cyRef.current?.zoom(cyRef.current.zoom() * 1.2);
  }, []);

  const handleZoomOut = useCallback(() => {
    cyRef.current?.zoom(cyRef.current.zoom() / 1.2);
  }, []);

  const handleFit = useCallback(() => {
    cyRef.current?.fit(undefined, 50);
  }, []);

  const handleRelayout = useCallback(() => {
    cyRef.current
      ?.layout({
        name: 'dagre',
        rankDir: 'TB',
        nodeSep: 50,
        rankSep: 100,
        animate: true,
        animationDuration: 500,
      })
      .run();
  }, []);

  return (
    <div className="relative h-full w-full bg-graph-bg">
      {/* Toolbar */}
      <div className="absolute top-3 left-3 z-10 flex gap-1 bg-panel-bg rounded border border-border p-1">
        <button
          onClick={handleZoomIn}
          className="p-1.5 hover:bg-border rounded text-xs"
          title="Zoom In"
        >
          +
        </button>
        <button
          onClick={handleZoomOut}
          className="p-1.5 hover:bg-border rounded text-xs"
          title="Zoom Out"
        >
          -
        </button>
        <button
          onClick={handleFit}
          className="p-1.5 hover:bg-border rounded text-xs"
          title="Fit to View"
        >
          ⊡
        </button>
        <button
          onClick={handleRelayout}
          className="p-1.5 hover:bg-border rounded text-xs"
          title="Re-layout"
        >
          ↻
        </button>
      </div>

      {/* Stats */}
      {graphData && (
        <div className="absolute top-3 right-3 z-10 bg-panel-bg rounded border border-border px-3 py-1.5 text-xs text-text-secondary">
          {graphData.nodes.length} nodes • {graphData.edges.length} edges
        </div>
      )}

      {/* Cytoscape container */}
      <div ref={containerRef} className="h-full w-full" />

      {/* Empty state */}
      {!graphData && (
        <div className="absolute inset-0 flex items-center justify-center text-text-secondary">
          <div className="text-center">
            <div className="text-4xl mb-4">📊</div>
            <div>No graph data loaded</div>
            <div className="text-sm mt-2">Load a snapshot or run a query</div>
          </div>
        </div>
      )}
    </div>
  );
}
