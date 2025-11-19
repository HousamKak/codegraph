import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { WilsonCPU } from '../lib/wilson/wilson';
import { useStore } from '../store';
import type { GraphEdge, GraphNode } from '../types';
import { EDGE_COLORS, NODE_COLORS } from '../types';

const EDGE_TYPES_TO_SKIP = new Set(['HAS_TYPE', 'RETURNS_TYPE', 'ASSIGNED_TYPE']);
const NODE_RADIUS_PX = 10;
const EDGE_HIT_WIDTH_PX = 12;

interface PositionedNode {
  id: string;
  x: number;
  y: number;
}

const createLayoutWorker = () =>
  new Worker(new URL('../workers/layoutWorker.ts', import.meta.url), { type: 'module' });

export function GraphView() {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wilsonRef = useRef<WilsonCPU | null>(null);
  const workerRef = useRef<Worker | null>(null);
  const layoutRequestIdRef = useRef(0);
  const nodePositionsRef = useRef<Map<string, PositionedNode>>(new Map());
  const animationRef = useRef<number | null>(null);

  const graphData = useStore((state) => state.graphData);
  const selectedNode = useStore((state) => state.selectedNode);
  const selectedEdge = useStore((state) => state.selectedEdge);
  const setSelectedNode = useStore((state) => state.setSelectedNode);
  const setSelectedEdge = useStore((state) => state.setSelectedEdge);

  const [viewport, setViewport] = useState({ width: 0, height: 0 });

  const renderableEdges = useMemo(() => {
    if (!graphData) return [] as GraphEdge[];
    return graphData.edges.filter((edge) => !EDGE_TYPES_TO_SKIP.has(edge.type));
  }, [graphData]);

  // Observe container for responsive sizing
  useLayoutEffect(() => {
    if (!containerRef.current) return;

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry?.contentRect) {
        setViewport({
          width: Math.max(200, entry.contentRect.width),
          height: Math.max(200, entry.contentRect.height),
        });
      }
    });

    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // Initialize Wilson canvas
  useEffect(() => {
    if (!canvasRef.current || viewport.width === 0 || viewport.height === 0) return;

    if (!wilsonRef.current) {
      wilsonRef.current = new WilsonCPU(canvasRef.current, {
        canvasWidth: viewport.width,
        worldWidth: 2000,
        worldCenterX: 0,
        worldCenterY: 0,
        interactionOptions: {
          useForPanAndZoom: true,
          inertia: true,
          panFriction: 0.08,
          zoomFriction: 0.08,
        },
      });
    } else {
      wilsonRef.current.resizeCanvas({ width: viewport.width });
    }

    scheduleDraw();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [viewport.width, viewport.height]);

  // Initialize layout worker
  useEffect(() => {
    const worker = createLayoutWorker();
    workerRef.current = worker;

    worker.onmessage = (event) => {
      const { id, nodes } = event.data as { id: number; nodes: PositionedNode[] };
      if (id !== layoutRequestIdRef.current) return;
      nodePositionsRef.current = new Map(nodes.map((node) => [node.id, node]));
      updateWorldFromPositions(nodes);
      scheduleDraw();
    };

    return () => {
      worker.terminate();
      workerRef.current = null;
    };
  }, []);

  // Trigger layout when graph changes
  useEffect(() => {
    if (!graphData || !workerRef.current) {
      nodePositionsRef.current.clear();
      scheduleDraw();
      return;
    }

    layoutRequestIdRef.current += 1;
    const payload = {
      id: layoutRequestIdRef.current,
      nodes: graphData.nodes.map((node) => ({ id: node.id })),
      edges: renderableEdges.map((edge) => ({ source: edge.source, target: edge.target })),
    };
    workerRef.current.postMessage(payload);
  }, [graphData, renderableEdges]);

  // Redraw when selection changes
  useEffect(() => {
    scheduleDraw();
  }, [selectedNode, selectedEdge]);

  const scheduleDraw = useCallback(() => {
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }
    animationRef.current = requestAnimationFrame(() => {
      drawScene();
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const updateWorldFromPositions = useCallback((positions: PositionedNode[]) => {
    if (!wilsonRef.current || positions.length === 0) return;

    let minX = Infinity;
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;

    positions.forEach((node) => {
      if (node.x < minX) minX = node.x;
      if (node.x > maxX) maxX = node.x;
      if (node.y < minY) minY = node.y;
      if (node.y > maxY) maxY = node.y;
    });

    const padding = 400;
    const width = (maxX - minX || 1) + padding;
    const height = (maxY - minY || 1) + padding;
    const centerX = (maxX + minX) / 2;
    const centerY = (maxY + minY) / 2;

    wilsonRef.current.resizeWorld({
      width,
      height,
      centerX,
      centerY,
      showResetButton: false,
    });
  }, []);

  const drawScene = useCallback(() => {
    const wilson = wilsonRef.current;
    if (!wilson || !graphData) {
      const ctx = wilson?.ctx ?? canvasRef.current?.getContext('2d');
      ctx?.clearRect(0, 0, wilson?.canvasWidth ?? viewport.width, wilson?.canvasHeight ?? viewport.height);
      return;
    }

    if (nodePositionsRef.current.size === 0 && graphData.nodes.length) {
      const temp = new Map<string, PositionedNode>();
      const radius = Math.max(graphData.nodes.length * 4, 200);
      graphData.nodes.forEach((node, index) => {
        const angle = (index / graphData.nodes.length) * Math.PI * 2;
        temp.set(node.id, {
          id: node.id,
          x: Math.cos(angle) * radius,
          y: Math.sin(angle) * radius,
        });
      });
      nodePositionsRef.current = temp;
    }

    const ctx = wilson.ctx;
    ctx.save();
    ctx.clearRect(0, 0, wilson.canvasWidth, wilson.canvasHeight);
    ctx.fillStyle = '#121212';
    ctx.fillRect(0, 0, wilson.canvasWidth, wilson.canvasHeight);

    const convert = (nodeId: string): [number, number] | null => {
      const position = nodePositionsRef.current.get(nodeId);
      if (!position) return null;
      const [row, col] = wilson.interpolateWorldToCanvas([position.x, position.y]);
      return [col, row];
    };

    // Draw edges first
    renderableEdges.forEach((edge) => {
      const sourcePoint = convert(edge.source);
      const targetPoint = convert(edge.target);
      if (!sourcePoint || !targetPoint) return;

      const [sx, sy] = sourcePoint;
      const [tx, ty] = targetPoint;

      ctx.beginPath();
      ctx.moveTo(sx, sy);
      ctx.lineTo(tx, ty);
      ctx.strokeStyle = EDGE_COLORS[edge.type] || '#6b7280';
      ctx.lineWidth = selectedEdge && selectedEdge.id === edge.id ? 4 : 2;
      ctx.globalAlpha = 0.65;
      ctx.stroke();
      ctx.globalAlpha = 1;
    });

    // Draw nodes
    graphData.nodes.forEach((node) => {
      const point = convert(node.id);
      if (!point) return;
      const [x, y] = point;
      const isSelected = selectedNode?.id === node.id;
      const baseColor = NODE_COLORS[node.labels[0]] || '#93c5fd';

      ctx.beginPath();
      ctx.arc(x, y, NODE_RADIUS_PX + (isSelected ? 4 : 2), 0, Math.PI * 2);
      ctx.fillStyle = '#0f172a';
      ctx.fill();

      ctx.beginPath();
      ctx.arc(x, y, NODE_RADIUS_PX, 0, Math.PI * 2);
      ctx.fillStyle = baseColor;
      ctx.fill();
      ctx.lineWidth = isSelected ? 3 : 1.5;
      ctx.strokeStyle = isSelected ? '#f97316' : '#111827';
      ctx.stroke();
    });

    ctx.restore();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graphData, renderableEdges, selectedEdge, selectedNode, viewport.height, viewport.width]);

  const handlePointerUp = useCallback(
    (event: PointerEvent) => {
      if (!graphData || !wilsonRef.current) return;

      const wilson = wilsonRef.current;
      const canvas = canvasRef.current;
      if (!canvas) return;

      const rect = canvas.getBoundingClientRect();
      const canvasX = (event.clientX - rect.left) * (wilson.canvasWidth / rect.width);
      const canvasY = (event.clientY - rect.top) * (wilson.canvasHeight / rect.height);
      const [worldX, worldY] = wilson.interpolateCanvasToWorld([canvasY, canvasX]);

      const nodeThreshold = (wilson.worldWidth / wilson.canvasWidth) * (NODE_RADIUS_PX + 6);
      let closestNode: GraphNode | null = null;
      let minNodeDistance = Infinity;

      graphData.nodes.forEach((node) => {
        const position = nodePositionsRef.current.get(node.id);
        if (!position) return;
        const distance = Math.hypot(worldX - position.x, worldY - position.y);
        if (distance < nodeThreshold && distance < minNodeDistance) {
          closestNode = node;
          minNodeDistance = distance;
        }
      });

      if (closestNode) {
        setSelectedNode(closestNode);
        setSelectedEdge(null);
        scheduleDraw();
        return;
      }

      const edgeThreshold = (wilson.worldWidth / wilson.canvasWidth) * EDGE_HIT_WIDTH_PX;
      let closestEdge: GraphEdge | null = null;
      let minEdgeDistance = Infinity;

      renderableEdges.forEach((edge) => {
        const source = nodePositionsRef.current.get(edge.source);
        const target = nodePositionsRef.current.get(edge.target);
        if (!source || !target) return;
        const distance = distanceToSegment(worldX, worldY, source.x, source.y, target.x, target.y);
        if (distance < edgeThreshold && distance < minEdgeDistance) {
          closestEdge = edge;
          minEdgeDistance = distance;
        }
      });

      if (closestEdge) {
        setSelectedEdge(closestEdge);
        setSelectedNode(null);
        scheduleDraw();
        return;
      }

      setSelectedEdge(null);
      setSelectedNode(null);
      scheduleDraw();
    },
    [graphData, renderableEdges, scheduleDraw, setSelectedEdge, setSelectedNode]
  );

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const preventDefault = (event: Event) => event.preventDefault();
    canvas.addEventListener('pointerup', handlePointerUp);
    canvas.addEventListener('pointerdown', preventDefault);

    return () => {
      canvas.removeEventListener('pointerup', handlePointerUp);
      canvas.removeEventListener('pointerdown', preventDefault);
    };
  }, [handlePointerUp]);

  useEffect(() => {
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, []);

  return (
    <div ref={containerRef} className="w-full h-full relative">
      <canvas ref={canvasRef} className="w-full h-full" />
      {!graphData && (
        <div className="absolute inset-0 flex items-center justify-center text-gray-500 text-sm">
          Load a file to visualize its graph
        </div>
      )}
    </div>
  );
}

function distanceToSegment(x: number, y: number, x1: number, y1: number, x2: number, y2: number) {
  const dx = x2 - x1;
  const dy = y2 - y1;
  if (dx === 0 && dy === 0) {
    return Math.hypot(x - x1, y - y1);
  }

  const t = ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy);
  if (t < 0) return Math.hypot(x - x1, y - y1);
  if (t > 1) return Math.hypot(x - x2, y - y2);
  const projX = x1 + t * dx;
  const projY = y1 + t * dy;
  return Math.hypot(x - projX, y - projY);
}
