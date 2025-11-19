/// <reference lib="webworker" />
import {
  forceSimulation,
  forceLink,
  forceManyBody,
  forceCenter,
  forceCollide,
  SimulationNodeDatum,
} from 'd3-force';

interface LayoutNode extends SimulationNodeDatum {
  id: string;
}

interface LayoutEdge {
  source: string;
  target: string;
}

interface LayoutRequest {
  id?: number;
  nodes: { id: string }[];
  edges: LayoutEdge[];
  center?: { x: number; y: number };
}

const ctx: DedicatedWorkerGlobalScope = self as unknown as DedicatedWorkerGlobalScope;

ctx.onmessage = (event: MessageEvent<LayoutRequest>) => {
  const { nodes, edges, center, id } = event.data;

  if (!nodes?.length) {
    ctx.postMessage({ id, nodes: [] });
    return;
  }

  const width = Math.max(nodes.length * 80, 1600);
  const height = width;
  const cx = center?.x ?? 0;
  const cy = center?.y ?? 0;

  const simNodes: LayoutNode[] = nodes.map((node, index) => ({
    id: node.id,
    x: (index % 2 === 0 ? 1 : -1) * (Math.random() * width * 0.3),
    y: (index % 2 === 0 ? 1 : -1) * (Math.random() * height * 0.3),
    vx: 0,
    vy: 0,
  }));

  const simulation = forceSimulation<LayoutNode>(simNodes)
    .force(
      'link',
      forceLink<LayoutNode, LayoutEdge>(edges)
        .id((d) => d.id)
        .distance(220)
        .strength(0.4)
    )
    .force('charge', forceManyBody().strength(-900))
    .force('center', forceCenter(cx, cy))
    .force('collision', forceCollide().radius(120).strength(0.7))
    .alphaDecay(0.03)
    .velocityDecay(0.25);

  simulation.stop();
  const iterations = Math.min(800, Math.max(300, nodes.length * 3));
  for (let i = 0; i < iterations; i += 1) {
    simulation.tick();
  }

  ctx.postMessage({
    id,
    nodes: simNodes.map((node) => ({
      id: node.id,
      x: node.x ?? 0,
      y: node.y ?? 0,
    })),
  });
};

export {};
