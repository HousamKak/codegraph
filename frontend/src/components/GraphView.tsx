import { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { useStore } from '../store';
import { EDGE_COLORS, NODE_COLORS } from '../types';

const EDGE_TYPES_TO_SKIP = new Set(['HAS_TYPE', 'RETURNS_TYPE', 'ASSIGNED_TYPE']);

export function GraphView() {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const simulationRef = useRef<any>(null);

  const graphData = useStore((state) => state.graphData);
  const selectedNode = useStore((state) => state.selectedNode);
  const selectedEdge = useStore((state) => state.selectedEdge);
  const setSelectedNode = useStore((state) => state.setSelectedNode);
  const setSelectedEdge = useStore((state) => state.setSelectedEdge);

  useEffect(() => {
    if (!svgRef.current || !containerRef.current || !graphData) return;

    const container = containerRef.current;
    const width = container.clientWidth;
    const height = container.clientHeight;

    // Clear previous content
    d3.select(svgRef.current).selectAll('*').remove();

    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height)
      .style('background', 'linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%)');

    // Add zoom behavior
    const zoom = d3.zoom()
      .scaleExtent([0.1, 10])
      .on('zoom', (event) => {
        graphContainer.attr('transform', event.transform);
      });

    svg.call(zoom as any);

    // Create main container for graph elements
    const graphContainer = svg.append('g').attr('class', 'graph-container');

    // Add arrow marker definitions
    const defs = graphContainer.append('defs');

    Object.entries(EDGE_COLORS).forEach(([type, color]) => {
      defs.append('marker')
        .attr('id', `arrow-${type}`)
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 28)
        .attr('refY', 0)
        .attr('markerWidth', 8)
        .attr('markerHeight', 8)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-5L10,0L0,5')
        .attr('fill', color);
    });

    // Build type information map from type edges
    const nodeTypeInfo = new Map<string, { typeName: string; color: string }>();
    const validNodeIds = new Set(graphData.nodes.map(n => n.id));

    graphData.edges.forEach(edge => {
      if (EDGE_TYPES_TO_SKIP.has(edge.type) && validNodeIds.has(edge.source) && validNodeIds.has(edge.target)) {
        const targetNode = graphData.nodes.find(n => n.id === edge.target);
        if (targetNode) {
          const typeName = targetNode.properties.name || targetNode.id.split(':').pop() || 'Type';
          const color = EDGE_COLORS[edge.type] || '#a855f7';
          nodeTypeInfo.set(edge.source, { typeName, color });
        }
      }
    });

    // Filter edges for visualization (exclude type edges)
    const edges = graphData.edges.filter(
      edge => !EDGE_TYPES_TO_SKIP.has(edge.type) &&
              validNodeIds.has(edge.source) &&
              validNodeIds.has(edge.target)
    );

    // Create node and link data
    const nodes = graphData.nodes.map((node, i) => ({
      ...node,
      x: width / 2 + (Math.random() - 0.5) * 300,
      y: height / 2 + (Math.random() - 0.5) * 300,
    }));

    // Group edges by source-target pair to handle multiple edges
    const edgeGroups = new Map<string, typeof edges>();
    edges.forEach(edge => {
      const key = [edge.source, edge.target].sort().join('|');
      if (!edgeGroups.has(key)) {
        edgeGroups.set(key, []);
      }
      edgeGroups.get(key)!.push(edge);
    });

    // Assign curve offsets to edges between same nodes
    const links = edges.map(edge => {
      const key = [edge.source, edge.target].sort().join('|');
      const group = edgeGroups.get(key)!;
      const index = group.indexOf(edge);
      const total = group.length;

      // Calculate curve offset
      let curveOffset = 0;
      if (total > 1) {
        const spread = 40; // pixels to spread multiple edges
        curveOffset = (index - (total - 1) / 2) * spread;
      }

      return {
        ...edge,
        source: edge.source,
        target: edge.target,
        curveOffset,
      };
    });

    // Create force simulation
    const simulation = d3.forceSimulation(nodes as any)
      .force('link', d3.forceLink(links)
        .id((d: any) => d.id)
        .distance(180)
        .strength(0.5)
      )
      .force('charge', d3.forceManyBody().strength(-1000))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(60).strength(0.7));

    simulationRef.current = simulation;

    // Create link groups (for paths + labels)
    const linkGroup = graphContainer.append('g')
      .attr('class', 'links')
      .selectAll('g')
      .data(links)
      .enter()
      .append('g')
      .attr('class', 'link-group');

    // Add curved paths for links
    const link = linkGroup.append('path')
      .attr('fill', 'none')
      .attr('stroke', d => EDGE_COLORS[d.type] || '#6b7280')
      .attr('stroke-width', d => selectedEdge?.id === d.id ? 3 : 1.5)
      .attr('stroke-opacity', 0.6)
      .attr('marker-end', d => `url(#arrow-${d.type})`)
      .style('cursor', 'pointer')
      .on('click', function(event, d) {
        event.stopPropagation();
        setSelectedEdge(d as any);
        setSelectedNode(null);
      });

    // Add edge labels
    const linkLabel = linkGroup.append('text')
      .text(d => d.type)
      .attr('text-anchor', 'middle')
      .attr('fill', d => EDGE_COLORS[d.type] || '#6b7280')
      .attr('font-size', '10px')
      .attr('font-weight', 'bold')
      .style('pointer-events', 'none')
      .style('text-shadow', '0 0 3px #000, 0 0 3px #000, 0 0 3px #000');

    // Create node groups
    const node = graphContainer.append('g')
      .attr('class', 'nodes')
      .selectAll('g')
      .data(nodes)
      .enter()
      .append('g')
      .attr('class', 'node')
      .style('cursor', 'pointer')
      .call(d3.drag<any, any>()
        .on('start', (event, d: any) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on('drag', (event, d: any) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on('end', (event, d: any) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        })
      )
      .on('click', function(event, d) {
        event.stopPropagation();
        setSelectedNode(d as any);
        setSelectedEdge(null);
      });

    // Add main node circle - colored by node type (Function, Class, etc.)
    node.append('circle')
      .attr('r', 18)
      .attr('fill', d => NODE_COLORS[d.labels[0]] || '#93c5fd')
      .attr('stroke', d => selectedNode?.id === d.id ? '#fbbf24' : '#1a1a2e')
      .attr('stroke-width', d => selectedNode?.id === d.id ? 3 : 2)
      .style('filter', d => selectedNode?.id === d.id ? 'drop-shadow(0 0 8px rgba(251, 191, 36, 0.8))' : 'drop-shadow(0 2px 4px rgba(0,0,0,0.3))');

    // Add outer ring (type indicator) - only if node has type information
    node.each(function(d: any) {
      if (nodeTypeInfo.has(d.id)) {
        const typeInfo = nodeTypeInfo.get(d.id)!;
        d3.select(this)
          .append('circle')
          .attr('r', selectedNode?.id === d.id ? 26 : 22)
          .attr('fill', 'none')
          .attr('stroke', typeInfo.color)
          .attr('stroke-width', 3)
          .style('opacity', 0.8);
      }
    });

    // Add node name labels (inside, can overflow)
    node.append('text')
      .text(d => d.properties.name || d.id.split(':').pop() || '')
      .attr('text-anchor', 'middle')
      .attr('dy', '.35em')
      .attr('fill', '#000')
      .attr('font-size', '11px')
      .attr('font-weight', 'bold')
      .style('pointer-events', 'none')
      .style('text-shadow', '0 0 2px #fff, 0 0 2px #fff');

    // Add type name labels (below) - only for nodes with type information
    node.each(function(d: any) {
      if (nodeTypeInfo.has(d.id)) {
        const typeInfo = nodeTypeInfo.get(d.id)!;
        d3.select(this)
          .append('text')
          .text(typeInfo.typeName)
          .attr('text-anchor', 'middle')
          .attr('dy', '35px')
          .attr('fill', typeInfo.color)
          .attr('font-size', '10px')
          .attr('font-weight', 'bold')
          .style('pointer-events', 'none')
          .style('text-shadow', '0 0 3px #000, 0 0 3px #000');
      }
    });

    // Update positions on simulation tick
    simulation.on('tick', () => {
      // Draw curved paths for edges
      link.attr('d', (d: any) => {
        const dx = d.target.x - d.source.x;
        const dy = d.target.y - d.source.y;
        const dr = Math.sqrt(dx * dx + dy * dy);

        // Calculate perpendicular offset for curve
        const offsetX = -dy * (d.curveOffset || 0) / dr;
        const offsetY = dx * (d.curveOffset || 0) / dr;

        // Control point for quadratic curve
        const midX = (d.source.x + d.target.x) / 2 + offsetX;
        const midY = (d.source.y + d.target.y) / 2 + offsetY;

        return `M${d.source.x},${d.source.y} Q${midX},${midY} ${d.target.x},${d.target.y}`;
      });

      // Position and rotate edge labels to be parallel to edge
      linkLabel.each(function(d: any) {
        const dx = d.target.x - d.source.x;
        const dy = d.target.y - d.source.y;
        const dr = Math.sqrt(dx * dx + dy * dy);

        // Calculate perpendicular offset for curve
        const curveOffsetX = -dy * (d.curveOffset || 0) / dr;
        const curveOffsetY = dx * (d.curveOffset || 0) / dr;

        // Position at midpoint of curve
        const midX = (d.source.x + d.target.x) / 2 + curveOffsetX;
        const midY = (d.source.y + d.target.y) / 2 + curveOffsetY;

        // Calculate angle for rotation
        let angle = Math.atan2(dy, dx) * 180 / Math.PI;

        // Keep text right-side up
        if (angle > 90 || angle < -90) {
          angle += 180;
        }

        d3.select(this)
          .attr('x', midX)
          .attr('y', midY - 3) // Slightly above the line
          .attr('transform', `rotate(${angle}, ${midX}, ${midY})`);
      });

      node.attr('transform', (d: any) => `translate(${d.x},${d.y})`);
    });

    // Cleanup
    return () => {
      simulation.stop();
    };
  }, [graphData, selectedNode, selectedEdge, setSelectedNode, setSelectedEdge]);

  return (
    <div ref={containerRef} className="w-full h-full relative bg-[#0a0a0a]">
      <svg ref={svgRef} className="w-full h-full" />
      {!graphData && (
        <div className="absolute inset-0 flex items-center justify-center text-gray-400 text-sm">
          Load a file to visualize its graph
        </div>
      )}
    </div>
  );
}
