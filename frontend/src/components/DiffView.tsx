import React, { useEffect, useMemo, useRef, useState } from 'react';
import * as d3 from 'd3';
import { useStore } from '../store';
import type { GraphData, GraphEdge, GraphNode } from '../types';
import { EDGE_COLORS, NODE_COLORS } from '../types';

type ViewMode = 'side-by-side' | 'unified';
type DiffStatus = 'added' | 'removed' | 'modified' | 'unchanged';

const edgeKey = (edge: Pick<GraphEdge, 'source' | 'target' | 'type'>) =>
  `${edge.source}|${edge.type}|${edge.target}`;

const formatNodeLabel = (node: GraphNode) =>
  node.properties.name || node.id.split(':').pop() || node.id;

interface DiffListItem {
  id: string;
  label: string;
  subtitle?: string;
}

export const DiffView: React.FC = () => {
  const [viewMode, setViewMode] = useState<ViewMode>('side-by-side');
  const beforeSvgRef = useRef<SVGSVGElement>(null);
  const afterSvgRef = useRef<SVGSVGElement>(null);
  const unifiedSvgRef = useRef<SVGSVGElement>(null);
  const beforeContainerRef = useRef<HTMLDivElement>(null);
  const afterContainerRef = useRef<HTMLDivElement>(null);
  const unifiedContainerRef = useRef<HTMLDivElement>(null);

  const {
    compareFrom,
    compareTo,
    diffData,
    compareFromGraph,
    compareToGraph,
  } = useStore();

  const diffSets = useMemo(() => ({
    nodes: {
      added: new Set(diffData?.nodes.added.map((n: GraphNode) => n.id) ?? []),
      removed: new Set(diffData?.nodes.removed.map((n: GraphNode) => n.id) ?? []),
      modified: new Set(diffData?.nodes.modified.map((n: any) => n.id) ?? []),
    },
    edges: {
      added: new Set(diffData?.edges.added.map((e: GraphEdge) => edgeKey(e)) ?? []),
      removed: new Set(diffData?.edges.removed.map((e: GraphEdge) => edgeKey(e)) ?? []),
      modified: new Set(
        diffData?.edges.modified.map(
          (edge: any) => edge.signature || edgeKey(edge.new || edge.old)
        ) ?? []
      ),
    },
  }), [diffData]);

  const unifiedGraph = useMemo<GraphData | null>(() => {
    if (!compareFromGraph || !compareToGraph) return null;
    const nodeMap = new Map<string, GraphNode>();
    compareFromGraph.nodes.forEach((node) => nodeMap.set(node.id, node));
    compareToGraph.nodes.forEach((node) => nodeMap.set(node.id, node));

    const edgeMap = new Map<string, GraphEdge>();
    compareFromGraph.edges.forEach((edge) => {
      const key = edgeKey(edge);
      edgeMap.set(key, { ...edge, id: edge.id || key });
    });
    compareToGraph.edges.forEach((edge) => {
      const key = edgeKey(edge);
      edgeMap.set(key, { ...edge, id: edge.id || key });
    });

    return {
      nodes: Array.from(nodeMap.values()),
      edges: Array.from(edgeMap.values()),
    };
  }, [compareFromGraph, compareToGraph]);

  const getNodeStatus = (mode: 'before' | 'after' | 'unified', id: string): DiffStatus => {
    if (mode === 'before') {
      if (diffSets.nodes.removed.has(id)) return 'removed';
      if (diffSets.nodes.modified.has(id)) return 'modified';
      return 'unchanged';
    }
    if (mode === 'after') {
      if (diffSets.nodes.added.has(id)) return 'added';
      if (diffSets.nodes.modified.has(id)) return 'modified';
      return 'unchanged';
    }
    if (diffSets.nodes.added.has(id)) return 'added';
    if (diffSets.nodes.removed.has(id)) return 'removed';
    if (diffSets.nodes.modified.has(id)) return 'modified';
    return 'unchanged';
  };

  const getEdgeStatus = (mode: 'before' | 'after' | 'unified', edge: GraphEdge): DiffStatus => {
    const key = edgeKey(edge);
    if (mode === 'before') {
      if (diffSets.edges.removed.has(key)) return 'removed';
      if (diffSets.edges.modified.has(key)) return 'modified';
      return 'unchanged';
    }
    if (mode === 'after') {
      if (diffSets.edges.added.has(key)) return 'added';
      if (diffSets.edges.modified.has(key)) return 'modified';
      return 'unchanged';
    }
    if (diffSets.edges.added.has(key)) return 'added';
    if (diffSets.edges.removed.has(key)) return 'removed';
    if (diffSets.edges.modified.has(key)) return 'modified';
    return 'unchanged';
  };

  useEffect(() => {
    if (!compareFrom || !compareTo || !diffData) return;
    if (!compareFromGraph || !compareToGraph) return;

    if (viewMode === 'side-by-side') {
      renderGraph(beforeSvgRef, beforeContainerRef, compareFromGraph, 'before');
      renderGraph(afterSvgRef, afterContainerRef, compareToGraph, 'after');
      d3.select(unifiedSvgRef.current).selectAll('*').remove();
    } else if (unifiedGraph) {
      renderGraph(unifiedSvgRef, unifiedContainerRef, unifiedGraph, 'unified');
      d3.select(beforeSvgRef.current).selectAll('*').remove();
      d3.select(afterSvgRef.current).selectAll('*').remove();
    }

    return () => {
      d3.select(beforeSvgRef.current).selectAll('*').remove();
      d3.select(afterSvgRef.current).selectAll('*').remove();
      d3.select(unifiedSvgRef.current).selectAll('*').remove();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [viewMode, compareFrom, compareTo, diffData, compareFromGraph, compareToGraph, unifiedGraph]);

  const renderGraph = (
    svgRef: React.RefObject<SVGSVGElement>,
    containerRef: React.RefObject<HTMLDivElement>,
    data: GraphData,
    mode: 'before' | 'after' | 'unified'
  ) => {
    if (!svgRef.current || !containerRef.current) return;

    const svg = d3.select(svgRef.current);
    const container = containerRef.current;
    const width = container.clientWidth;
    const height = container.clientHeight;

    svg.selectAll('*').remove();
    svg.attr('width', width).attr('height', height);

    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      });

    svg.call(zoom as any);

    const g = svg.append('g').attr('class', 'graph-container');

    const defs = svg.append('defs');
    Object.entries(EDGE_COLORS).forEach(([type, color]) => {
      defs.append('marker')
        .attr('id', `arrow-${type}-${mode}`)
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 25)
        .attr('refY', 0)
        .attr('markerWidth', 8)
        .attr('markerHeight', 8)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-5L10,0L0,5')
        .attr('fill', color);
    });

    const typeEdges = data.edges.filter(
      (edge) => edge.type === 'HAS_TYPE' || edge.type === 'RETURNS_TYPE'
    );
    const nodeTypeMap = new Map<string, { typeName: string; typeColor: string }>();

    typeEdges.forEach((edge) => {
      const typeNode = data.nodes.find((node) => node.id === edge.target);
      if (typeNode) {
        const typeName = typeNode.properties.name || typeNode.id.split(':').pop() || 'Type';
        const typeColor = EDGE_COLORS[edge.type] || '#64b5f6';
        nodeTypeMap.set(edge.source, { typeName, typeColor });
      }
    });

    const nodes = data.nodes.map((node) => ({
      ...node,
      label: formatNodeLabel(node),
      type: node.labels[0] || 'Unknown',
      x: width / 2 + (Math.random() - 0.5) * 100,
      y: height / 2 + (Math.random() - 0.5) * 100,
      typeInfo: nodeTypeMap.get(node.id),
      diffStatus: getNodeStatus(mode, node.id),
    }));

    const nodeIds = new Set(nodes.map((node) => node.id));

    const links = data.edges
      .filter((edge) => {
        if (edge.type === 'HAS_TYPE' || edge.type === 'RETURNS_TYPE') {
          return false;
        }
        return nodeIds.has(edge.source) && nodeIds.has(edge.target);
      })
      .map((edge) => ({
        ...edge,
        id: edge.id || edgeKey(edge),
        label: edge.type,
        diffStatus: getEdgeStatus(mode, edge),
      }));

    const linkCounts = new Map<string, number>();
    links.forEach((link) => {
      const key = `${link.source}-${link.target}`;
      const reverseKey = `${link.target}-${link.source}`;
      const count = (linkCounts.get(key) || 0) + (linkCounts.get(reverseKey) || 0);
      linkCounts.set(key, (linkCounts.get(key) || 0) + 1);
      (link as any).linkIndex = count;
      (link as any).linkCount = -1;
    });

    links.forEach((link) => {
      const key = `${link.source}-${link.target}`;
      const reverseKey = `${link.target}-${link.source}`;
      const totalCount = (linkCounts.get(key) || 0) + (linkCounts.get(reverseKey) || 0);
      (link as any).linkCount = totalCount;
    });

    const simulation = d3.forceSimulation(nodes as any)
      .force('link', d3.forceLink(links as any)
        .id((d: any) => d.id)
        .distance(150))
      .force('charge', d3.forceManyBody().strength(-600))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(40));

    const link = g.append('g')
      .attr('class', 'links')
      .selectAll('g')
      .data(links)
      .enter()
      .append('g')
      .attr('class', 'link-group');

    link.append('path')
      .attr('class', 'link')
      .attr('fill', 'none')
      .attr('stroke', (d: any) => {
        if (d.diffStatus === 'added') return '#10b981';
        if (d.diffStatus === 'removed') return '#ef4444';
        if (d.diffStatus === 'modified') return '#f59e0b';
        return EDGE_COLORS[d.type as keyof typeof EDGE_COLORS] || '#999';
      })
      .attr('stroke-width', (d: any) => (d.diffStatus === 'unchanged' ? 2 : 3))
      .attr('marker-end', (d: any) => `url(#arrow-${d.type}-${mode})`)
      .attr('opacity', (d: any) => (d.diffStatus === 'removed' ? 0.3 : 0.7))
      .style('stroke-dasharray', (d: any) => (d.diffStatus === 'removed' ? '5,5' : 'none'));

    link.append('text')
      .attr('class', 'link-label')
      .attr('text-anchor', 'middle')
      .attr('font-size', '9px')
      .attr('font-weight', '600')
      .attr('fill', (d: any) => {
        if (d.diffStatus === 'added') return '#6ee7b7';
        if (d.diffStatus === 'removed') return '#fca5a5';
        if (d.diffStatus === 'modified') return '#fcd34d';
        return '#d1d5db';
      })
      .attr('pointer-events', 'none')
      .style('text-shadow', '0 1px 2px rgba(0,0,0,0.8)')
      .text((d: any) => d.label);

    const node = g.append('g')
      .attr('class', 'nodes')
      .selectAll('g')
      .data(nodes)
      .enter()
      .append('g')
      .attr('class', 'node')
      .call(d3.drag<any, any>()
        .on('start', (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on('drag', (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on('end', (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        }) as any);

    node.append('circle')
      .attr('r', (d: any) => {
        // Smaller for unresolved nodes
        if (d.type === 'Unresolved') return 14;
        return d.diffStatus === 'unchanged' ? 18 : 22;
      })
      .attr('fill', (d: any) => {
        if (d.diffStatus === 'added') return '#10b981';
        if (d.diffStatus === 'removed') return '#ef4444';
        if (d.diffStatus === 'modified') return '#f59e0b';
        return NODE_COLORS[d.type as keyof typeof NODE_COLORS] || '#95a5a6';
      })
      .attr('stroke', (d: any) => d.typeInfo ? d.typeInfo.typeColor : 'none')
      .attr('stroke-width', (d: any) => (d.typeInfo ? 3 : 0))
      .attr('stroke-dasharray', (d: any) => d.type === 'Unresolved' ? '4,4' : 'none')  // Dashed for unresolved
      .attr('opacity', (d: any) => {
        if (d.diffStatus === 'removed') return 0.5;
        if (d.type === 'Unresolved') return 0.7;  // Slightly transparent for unresolved
        return 1;
      })
      .style('filter', (d: any) => {
        if (d.diffStatus === 'added') return 'drop-shadow(0 0 8px rgba(16, 185, 129, 0.6))';
        if (d.diffStatus === 'removed') return 'drop-shadow(0 0 8px rgba(239, 68, 68, 0.6))';
        if (d.diffStatus === 'modified') return 'drop-shadow(0 0 8px rgba(245, 158, 11, 0.6))';
        return 'drop-shadow(0 2px 4px rgba(0,0,0,0.2))';
      });

    node.append('text')
      .text((d: any) => d.type === 'Unresolved' ? `? ${d.label}` : d.label)
      .attr('text-anchor', 'middle')
      .attr('dy', '.35em')
      .attr('font-size', '10px')
      .attr('font-weight', 'bold')
      .attr('fill', 'white')
      .attr('pointer-events', 'none')
      .style('text-shadow', '0 1px 2px rgba(0,0,0,0.3)');
  };

  if (!compareFrom || !compareTo) {
    return (
      <div className="h-full flex items-center justify-center text-text-secondary">
        Select two commits from the left panel to view their differences.
      </div>
    );
  }

  if (!diffData) {
    return (
      <div className="h-full flex items-center justify-center text-text-secondary">
        Loading commit comparison...
      </div>
    );
  }

  const nodeLists: { title: string; items: DiffListItem[]; variant: DiffStatus }[] = [
    {
      title: 'Nodes Added',
      items: diffData.nodes.added.map((node: GraphNode) => ({
        id: node.id,
        label: formatNodeLabel(node),
        subtitle: node.labels[0],
      })),
      variant: 'added',
    },
    {
      title: 'Nodes Removed',
      items: diffData.nodes.removed.map((node: GraphNode) => ({
        id: node.id,
        label: formatNodeLabel(node),
        subtitle: node.labels[0],
      })),
      variant: 'removed',
    },
    {
      title: 'Nodes Modified',
      items: diffData.nodes.modified.map((node: any) => ({
        id: node.id,
        label: formatNodeLabel(node.new),
        subtitle: node.new.labels[0],
      })),
      variant: 'modified',
    },
  ];

  const edgeLists: { title: string; items: DiffListItem[]; variant: DiffStatus }[] = [
    {
      title: 'Edges Added',
      items: diffData.edges.added.map((edge: GraphEdge) => ({
        id: edgeKey(edge),
        label: edge.type,
        subtitle: `${edge.source} → ${edge.target}`,
      })),
      variant: 'added',
    },
    {
      title: 'Edges Removed',
      items: diffData.edges.removed.map((edge: GraphEdge) => ({
        id: edgeKey(edge),
        label: edge.type,
        subtitle: `${edge.source} → ${edge.target}`,
      })),
      variant: 'removed',
    },
    {
      title: 'Edges Modified',
      items: diffData.edges.modified.map((edge: any) => ({
        id: edge.signature,
        label: edge.old.type,
        subtitle: `${edge.old.source} → ${edge.old.target}`,
      })),
      variant: 'modified',
    },
  ];

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="border-b border-border p-4 flex items-center justify-between bg-panel-bg">
        <div>
          <h2 className="text-lg font-semibold">Commit Diff</h2>
          <p className="text-sm text-text-secondary">
            Comparing <span className="font-mono">{compareFrom?.slice(0, 8)}</span> →{' '}
            <span className="font-mono">{compareTo?.slice(0, 8)}</span>
          </p>
        </div>
        <div className="flex gap-4">
          <SummaryCard label="Nodes Added" value={diffData.summary.nodes_added} variant="added" />
          <SummaryCard label="Nodes Removed" value={diffData.summary.nodes_removed} variant="removed" />
          <SummaryCard label="Nodes Modified" value={diffData.summary.nodes_modified} variant="modified" />
          <SummaryCard label="Edges Added" value={diffData.summary.edges_added} variant="added" />
          <SummaryCard label="Edges Removed" value={diffData.summary.edges_removed} variant="removed" />
          <SummaryCard label="Edges Modified" value={diffData.summary.edges_modified} variant="modified" />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        <div className="grid md:grid-cols-3 gap-4">
          {nodeLists.map((section) => (
            <DiffList key={section.title} {...section} />
          ))}
        </div>

        <div className="grid md:grid-cols-3 gap-4">
          {edgeLists.map((section) => (
            <DiffList key={section.title} {...section} />
          ))}
        </div>

        {compareFromGraph && compareToGraph && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-text-primary">Visual Comparison</h3>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setViewMode('side-by-side')}
                  className={`px-3 py-1 rounded text-sm ${
                    viewMode === 'side-by-side'
                      ? 'bg-accent text-white'
                      : 'bg-panel-bg text-text-secondary hover:text-text-primary'
                  }`}
                >
                  Side by side
                </button>
                <button
                  onClick={() => setViewMode('unified')}
                  className={`px-3 py-1 rounded text-sm ${
                    viewMode === 'unified'
                      ? 'bg-accent text-white'
                      : 'bg-panel-bg text-text-secondary hover:text-text-primary'
                  }`}
                >
                  Unified
                </button>
              </div>
            </div>

            {viewMode === 'side-by-side' ? (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 h-[480px]">
                <div className="bg-graph-panel border border-border rounded-lg relative">
                  <div className="absolute top-2 left-2 text-xs font-semibold bg-white/70 px-2 py-1 rounded">
                    Before ({compareFrom?.slice(0, 8)})
                  </div>
                  <div ref={beforeContainerRef} className="w-full h-full">
                    <svg ref={beforeSvgRef} className="w-full h-full" />
                  </div>
                </div>
                <div className="bg-graph-panel border border-border rounded-lg relative">
                  <div className="absolute top-2 left-2 text-xs font-semibold bg-white/70 px-2 py-1 rounded">
                    After ({compareTo?.slice(0, 8)})
                  </div>
                  <div ref={afterContainerRef} className="w-full h-full">
                    <svg ref={afterSvgRef} className="w-full h-full" />
                  </div>
                </div>
              </div>
            ) : (
              <div className="h-[500px] bg-graph-panel border border-border rounded-lg relative">
                <div className="absolute top-2 left-2 text-xs font-semibold bg-white/70 px-2 py-1 rounded">
                  Unified View
                </div>
                <div ref={unifiedContainerRef} className="w-full h-full">
                  <svg ref={unifiedSvgRef} className="w-full h-full" />
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

const SummaryCard: React.FC<{ label: string; value: number; variant: DiffStatus }> = ({
  label,
  value,
  variant,
}) => {
  const colors: Record<DiffStatus, string> = {
    added: 'text-green-600',
    removed: 'text-red-600',
    modified: 'text-yellow-600',
    unchanged: 'text-text-secondary',
  };

  return (
    <div className="px-3 py-2 bg-white rounded border border-border text-sm">
      <div className="text-text-secondary">{label}</div>
      <div className={`text-xl font-semibold ${colors[variant]}`}>{value}</div>
    </div>
  );
};

const DiffList: React.FC<{ title: string; items: DiffListItem[]; variant: DiffStatus }> = ({
  title,
  items,
  variant,
}) => {
  const colors: Record<DiffStatus, string> = {
    added: 'border-green-200 bg-green-50',
    removed: 'border-red-200 bg-red-50',
    modified: 'border-yellow-200 bg-yellow-50',
    unchanged: 'border-border bg-panel-bg',
  };

  return (
    <div className={`rounded-lg border ${colors[variant]} p-3`}>
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-semibold text-text-primary">{title}</h4>
        <span className="text-xs text-text-secondary">{items.length}</span>
      </div>
      {items.length === 0 ? (
        <div className="text-xs text-text-secondary">No changes</div>
      ) : (
        <ul className="text-xs space-y-1 max-h-40 overflow-auto pr-1">
          {items.slice(0, 8).map((item) => (
            <li key={item.id} className="flex flex-col">
              <span className="font-mono text-text-primary truncate">{item.label}</span>
              {item.subtitle && (
                <span className="text-text-secondary">{item.subtitle}</span>
              )}
            </li>
          ))}
          {items.length > 8 && (
            <li className="text-text-secondary">+{items.length - 8} more…</li>
          )}
        </ul>
      )}
    </div>
  );
};
