import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { WilsonCPU } from '../lib/wilson/wilson';
import { useStore } from '../store';
import type { GraphEdge, GraphNode } from '../types';
import { EDGE_COLORS, NODE_COLORS } from '../types';

const EDGE_TYPES_TO_SKIP = new Set(['HAS_TYPE', 'RETURNS_TYPE', 'ASSIGNED_TYPE']);
const NODE_RADIUS_PX = 18;
const EDGE_HIT_WIDTH_PX = 12;
const ARROW_SIZE = 8;

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
  const isDraggingRef = useRef(false);

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

  const nodeTypeInfo = useMemo(() => {
    const map = new Map<
      string,
      {
        name: string;
        color: string;
      }
    >();

    if (!graphData) {
      return map;
    }

    const nodeLookup = new Map<string, GraphNode>();
    graphData.nodes.forEach((node) => nodeLookup.set(node.id, node));

    graphData.edges.forEach((edge) => {
      if (!EDGE_TYPES_TO_SKIP.has(edge.type)) return;
      const targetType = nodeLookup.get(edge.target);
      if (!targetType) return;
      const typeName = targetType.properties.name || targetType.id.split(':').pop() || 'Type';
      const color = EDGE_COLORS[edge.type] || '#a855f7';
      map.set(edge.source, { name: typeName, color });
    });

    return map;
  }, [graphData]);

  // DEFINE CALLBACKS FIRST before using them in effects

  const drawScene = useCallback(() => {
    const wilson = wilsonRef.current;
    const canvas = canvasRef.current;

    if (!wilson || !graphData) {
      const ctx = wilson?.ctx ?? canvas?.getContext('2d');
      if (ctx) {
        ctx.clearRect(0, 0, wilson?.canvasWidth ?? viewport.width, wilson?.canvasHeight ?? viewport.height);
      }
      return;
    }

    // Initialize positions if empty
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

    // Dark gradient background
    const gradient = ctx.createLinearGradient(0, 0, 0, wilson.canvasHeight);
    gradient.addColorStop(0, '#0a0a0a');
    gradient.addColorStop(1, '#1a1a2e');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, wilson.canvasWidth, wilson.canvasHeight);

    const convert = (nodeId: string): [number, number] | null => {
      const position = nodePositionsRef.current.get(nodeId);
      if (!position) return null;
      const [row, col] = wilson.interpolateWorldToCanvas([position.x, position.y]);
      return [col, row];
    };

    // Helper function to draw arrow
    const drawArrow = (sx: number, sy: number, tx: number, ty: number, color: string) => {
      const dx = tx - sx;
      const dy = ty - sy;
      const angle = Math.atan2(dy, dx);
      const length = Math.sqrt(dx * dx + dy * dy);

      // Shorten the line to stop at node edge
      const shortenedLength = length - NODE_RADIUS_PX - 4;
      const endX = sx + Math.cos(angle) * shortenedLength;
      const endY = sy + Math.sin(angle) * shortenedLength;

      // Draw arrowhead
      const arrowX = endX;
      const arrowY = endY;

      ctx.beginPath();
      ctx.moveTo(arrowX, arrowY);
      ctx.lineTo(
        arrowX - ARROW_SIZE * Math.cos(angle - Math.PI / 6),
        arrowY - ARROW_SIZE * Math.sin(angle - Math.PI / 6)
      );
      ctx.lineTo(
        arrowX - ARROW_SIZE * Math.cos(angle + Math.PI / 6),
        arrowY - ARROW_SIZE * Math.sin(angle + Math.PI / 6)
      );
      ctx.closePath();
      ctx.fillStyle = color;
      ctx.fill();
    };

    // Draw edges with arrows
    renderableEdges.forEach((edge) => {
      const sourcePoint = convert(edge.source);
      const targetPoint = convert(edge.target);
      if (!sourcePoint || !targetPoint) return;

      const [sx, sy] = sourcePoint;
      const [tx, ty] = targetPoint;
      const isSelected = selectedEdge?.id === edge.id;
      const edgeColor = EDGE_COLORS[edge.type] || '#6b7280';

      // Draw edge line with gradient
      const edgeGradient = ctx.createLinearGradient(sx, sy, tx, ty);
      edgeGradient.addColorStop(0, edgeColor + '40');
      edgeGradient.addColorStop(1, edgeColor);

      ctx.beginPath();
      ctx.moveTo(sx, sy);
      ctx.lineTo(tx, ty);
      ctx.strokeStyle = isSelected ? edgeColor : edgeGradient;
      ctx.lineWidth = isSelected ? 3 : 1.5;
      ctx.globalAlpha = isSelected ? 0.9 : 0.5;
      ctx.stroke();
      ctx.globalAlpha = 1;

      // Edge label aligned to edge
      const label = edge.type;
      if (label) {
        const midX = (sx + tx) / 2;
        const midY = (sy + ty) / 2;
        let angle = Math.atan2(ty - sy, tx - sx);
        if (angle > Math.PI / 2 || angle < -Math.PI / 2) {
          angle += Math.PI;
        }
        ctx.save();
        ctx.translate(midX, midY);
        ctx.rotate(angle);
        ctx.font = 'bold 11px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
        const metrics = ctx.measureText(label);
        const labelWidth = metrics.width + 10;
        const labelHeight = 18;
        ctx.fillStyle = 'rgba(8, 8, 15, 0.85)';
        ctx.fillRect(-labelWidth / 2, -labelHeight / 2, labelWidth, labelHeight);
        ctx.fillStyle = '#e5e7eb';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(label, 0, 0);
        ctx.restore();
      }

      // Draw arrow
      if (!isSelected) {
        ctx.globalAlpha = 0.7;
      }
      drawArrow(sx, sy, tx, ty, edgeColor);
      ctx.globalAlpha = 1;
    });

    // Draw nodes with shadows and labels
    graphData.nodes.forEach((node) => {
      const point = convert(node.id);
      if (!point) return;
      const [x, y] = point;
      const isSelected = selectedNode?.id === node.id;
      const baseColor = NODE_COLORS[node.labels[0]] || '#93c5fd';
      const label = node.properties.name || node.id.split(':').pop() || '';
      const typeMeta = nodeTypeInfo.get(node.id);

      // Shadow
      if (isSelected) {
        ctx.shadowColor = baseColor;
        ctx.shadowBlur = 20;
        ctx.shadowOffsetX = 0;
        ctx.shadowOffsetY = 0;
      } else {
        ctx.shadowColor = 'rgba(0, 0, 0, 0.5)';
        ctx.shadowBlur = 10;
        ctx.shadowOffsetX = 0;
        ctx.shadowOffsetY = 4;
      }

      // Outer glow ring
      if (isSelected) {
        ctx.beginPath();
        ctx.arc(x, y, NODE_RADIUS_PX + 6, 0, Math.PI * 2);
        ctx.fillStyle = baseColor + '40';
        ctx.fill();
      }

      // Node background
      ctx.beginPath();
      ctx.arc(x, y, NODE_RADIUS_PX, 0, Math.PI * 2);

      // Gradient fill
      const nodeGradient = ctx.createRadialGradient(x - 4, y - 4, 0, x, y, NODE_RADIUS_PX);
      nodeGradient.addColorStop(0, baseColor);
      nodeGradient.addColorStop(1, baseColor + 'cc');
      ctx.fillStyle = nodeGradient;
      ctx.fill();

      // Border
      ctx.lineWidth = isSelected ? 3 : 2;
      ctx.strokeStyle = isSelected ? '#fbbf24' : baseColor + 'dd';
      ctx.stroke();

      // Type ring
      if (typeMeta) {
        ctx.beginPath();
        ctx.lineWidth = 4;
        ctx.strokeStyle = typeMeta.color;
        ctx.arc(x, y, NODE_RADIUS_PX + 6, 0, Math.PI * 2);
        ctx.stroke();
      }

      ctx.shadowColor = 'transparent';
      ctx.shadowBlur = 0;
      ctx.shadowOffsetX = 0;
      ctx.shadowOffsetY = 0;

      // Draw node label inside circle
      if (label) {
        ctx.font = 'bold 11px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = '#0f172a';
        ctx.fillText(label, x, y);
      }

      // Draw type text below node
      if (typeMeta) {
        ctx.font = 'bold 10px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = typeMeta.color;
        ctx.fillText(typeMeta.name, x, y + NODE_RADIUS_PX + 14);
      }
    });

    ctx.restore();
  }, [graphData, renderableEdges, selectedEdge, selectedNode, viewport.height, viewport.width, nodeTypeInfo]);

  const scheduleDraw = useCallback(() => {
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }
    animationRef.current = requestAnimationFrame(() => {
      drawScene();
    });
  }, [drawScene]);

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

  // NOW USE EFFECTS

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
          zoomFriction: 0.1,
          onPanAndZoom: () => scheduleDraw(),
          callbacks: {
            mousedown: () => {
              isDraggingRef.current = true;
            },
            mouseup: () => {
              isDraggingRef.current = false;
            },
            mouseleave: () => {
              isDraggingRef.current = false;
            },
            touchstart: () => {
              isDraggingRef.current = true;
            },
            touchend: () => {
              isDraggingRef.current = false;
            },
            wheel: () => scheduleDraw(),
          },
        },
      });
    } else {
      wilsonRef.current.resizeCanvas({ width: viewport.width });
    }

    scheduleDraw();
  }, [viewport.width, viewport.height, scheduleDraw]);

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
  }, [scheduleDraw, updateWorldFromPositions]);

  // Trigger layout when graph changes
  useEffect(() => {
    if (!graphData || !workerRef.current) {
      nodePositionsRef.current.clear();
      scheduleDraw();
      return;
    }

    layoutRequestIdRef.current += 1;

    // Create a Set of valid node IDs to filter edges
    const validNodeIds = new Set(graphData.nodes.map((node) => node.id));

    // Only include edges where both source and target nodes exist
    const validEdges = renderableEdges.filter(
      (edge) => validNodeIds.has(edge.source) && validNodeIds.has(edge.target)
    );

    const payload = {
      id: layoutRequestIdRef.current,
      nodes: graphData.nodes.map((node) => ({ id: node.id })),
      edges: validEdges.map((edge) => ({ source: edge.source, target: edge.target })),
    };
    workerRef.current.postMessage(payload);
  }, [graphData, renderableEdges, scheduleDraw]);

  // Redraw when selection changes
  useEffect(() => {
    scheduleDraw();
  }, [selectedNode, selectedEdge, scheduleDraw]);

  // Pointer events for node/edge selection (Wilson handles pan/zoom)
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    // Use click instead of pointerup to avoid interfering with Wilson's pan/zoom
    const handleClick = (event: MouseEvent) => {
      // Only handle if not dragging (Wilson sets this during pan)
      if (isDraggingRef.current) return;
      handlePointerUp(event as unknown as PointerEvent);
    };

    canvas.addEventListener('click', handleClick);

    return () => {
      canvas.removeEventListener('click', handleClick);
    };
  }, [handlePointerUp]);

  // Cleanup animation frame
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
  const A = x - x1;
  const B = y - y1;
  const C = x2 - x1;
  const D = y2 - y1;

  const dot = A * C + B * D;
  const lenSq = C * C + D * D;
  let param = -1;

  if (lenSq !== 0) param = dot / lenSq;

  let xx, yy;

  if (param < 0) {
    xx = x1;
    yy = y1;
  } else if (param > 1) {
    xx = x2;
    yy = y2;
  } else {
    xx = x1 + param * C;
    yy = y1 + param * D;
  }

  const dx = x - xx;
  const dy = y - yy;
  return Math.sqrt(dx * dx + dy * dy);
}
