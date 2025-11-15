"""Snapshot manager for graph state versioning."""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import hashlib
from .db import CodeGraphDB


@dataclass
class GraphSnapshot:
    """Represents a snapshot of the graph state."""
    snapshot_id: str
    timestamp: datetime
    description: str
    node_count: int
    edge_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NodeDiff:
    """Represents a difference in nodes between snapshots."""
    added: List[Dict[str, Any]] = field(default_factory=list)
    removed: List[Dict[str, Any]] = field(default_factory=list)
    modified: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class EdgeDiff:
    """Represents a difference in edges between snapshots."""
    added: List[Dict[str, Any]] = field(default_factory=list)
    removed: List[Dict[str, Any]] = field(default_factory=list)
    modified: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class GraphDiff:
    """Complete difference between two snapshots."""
    old_snapshot_id: str
    new_snapshot_id: str
    nodes: NodeDiff
    edges: EdgeDiff
    summary: Dict[str, int] = field(default_factory=dict)


class SnapshotManager:
    """Manages graph snapshots for version control and comparison."""

    def __init__(self, db: CodeGraphDB):
        """
        Initialize snapshot manager.

        Args:
            db: CodeGraphDB instance
        """
        self.db = db
        self._snapshots: Dict[str, Dict[str, Any]] = {}

    def create_snapshot(self, description: str = "") -> str:
        """
        Create a snapshot of the current graph state.

        Args:
            description: Optional description of the snapshot

        Returns:
            Snapshot ID
        """
        # Generate snapshot ID
        timestamp = datetime.now()
        snapshot_id = hashlib.md5(
            f"{timestamp.isoformat()}_{description}".encode()
        ).hexdigest()[:16]

        # Export all nodes
        nodes_query = "MATCH (n) RETURN n, labels(n) as labels, id(n) as node_id"
        nodes = self.db.execute_query(nodes_query)

        # Export all relationships
        edges_query = """
        MATCH (a)-[r]->(b)
        RETURN a.id as source, b.id as target, type(r) as rel_type, properties(r) as props
        """
        edges = self.db.execute_query(edges_query)

        # Store snapshot
        snapshot_data = {
            "snapshot_id": snapshot_id,
            "timestamp": timestamp.isoformat(),
            "description": description,
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges)
        }

        self._snapshots[snapshot_id] = snapshot_data

        return snapshot_id

    def get_snapshot(self, snapshot_id: str) -> Optional[GraphSnapshot]:
        """
        Get snapshot metadata as GraphSnapshot object.

        Args:
            snapshot_id: Snapshot ID

        Returns:
            GraphSnapshot or None if not found
        """
        if snapshot_id not in self._snapshots:
            return None

        data = self._snapshots[snapshot_id]
        return GraphSnapshot(
            snapshot_id=data["snapshot_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            description=data["description"],
            node_count=data["node_count"],
            edge_count=data["edge_count"]
        )

    def get_snapshot_data(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """
        Get snapshot as raw dictionary (for API responses).

        Args:
            snapshot_id: Snapshot ID

        Returns:
            Dictionary with snapshot data or None if not found
        """
        return self._snapshots.get(snapshot_id)

    def list_snapshots(self) -> List[GraphSnapshot]:
        """
        List all snapshots.

        Returns:
            List of snapshots
        """
        return [self.get_snapshot(sid) for sid in self._snapshots.keys()]

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """
        Delete a snapshot.

        Args:
            snapshot_id: Snapshot ID

        Returns:
            True if deleted, False if not found
        """
        if snapshot_id in self._snapshots:
            del self._snapshots[snapshot_id]
            return True
        return False

    def compare_snapshots(self, old_snapshot_id: str, new_snapshot_id: str) -> GraphDiff:
        """
        Compare two snapshots and return differences.

        Args:
            old_snapshot_id: Old snapshot ID
            new_snapshot_id: New snapshot ID

        Returns:
            GraphDiff object with all differences
        """
        if old_snapshot_id not in self._snapshots:
            raise ValueError(f"Snapshot {old_snapshot_id} not found")
        if new_snapshot_id not in self._snapshots:
            raise ValueError(f"Snapshot {new_snapshot_id} not found")

        old_data = self._snapshots[old_snapshot_id]
        new_data = self._snapshots[new_snapshot_id]

        # Compare nodes
        node_diff = self._compare_nodes(old_data["nodes"], new_data["nodes"])

        # Compare edges
        edge_diff = self._compare_edges(old_data["edges"], new_data["edges"])

        # Create summary
        summary = {
            "nodes_added": len(node_diff.added),
            "nodes_removed": len(node_diff.removed),
            "nodes_modified": len(node_diff.modified),
            "edges_added": len(edge_diff.added),
            "edges_removed": len(edge_diff.removed),
            "edges_modified": len(edge_diff.modified)
        }

        return GraphDiff(
            old_snapshot_id=old_snapshot_id,
            new_snapshot_id=new_snapshot_id,
            nodes=node_diff,
            edges=edge_diff,
            summary=summary
        )

    def _compare_nodes(self, old_nodes: List[Dict], new_nodes: List[Dict]) -> NodeDiff:
        """Compare nodes between snapshots."""
        # Create lookup by node ID
        old_map = {self._get_node_id(n): n for n in old_nodes}
        new_map = {self._get_node_id(n): n for n in new_nodes}

        old_ids = set(old_map.keys())
        new_ids = set(new_map.keys())

        # Find differences
        added_ids = new_ids - old_ids
        removed_ids = old_ids - new_ids
        common_ids = old_ids & new_ids

        added = [new_map[nid] for nid in added_ids]
        removed = [old_map[nid] for nid in removed_ids]

        # Find modified nodes
        modified = []
        for nid in common_ids:
            old_node = old_map[nid]
            new_node = new_map[nid]

            if self._nodes_differ(old_node, new_node):
                modified.append({
                    "id": nid,
                    "old": old_node,
                    "new": new_node,
                    "changes": self._get_node_changes(old_node, new_node)
                })

        return NodeDiff(added=added, removed=removed, modified=modified)

    def _compare_edges(self, old_edges: List[Dict], new_edges: List[Dict]) -> EdgeDiff:
        """Compare edges between snapshots."""
        # Create edge signatures
        def edge_sig(e):
            return f"{e['source']}-{e['rel_type']}->{e['target']}"

        old_map = {edge_sig(e): e for e in old_edges}
        new_map = {edge_sig(e): e for e in new_edges}

        old_sigs = set(old_map.keys())
        new_sigs = set(new_map.keys())

        # Find differences
        added_sigs = new_sigs - old_sigs
        removed_sigs = old_sigs - new_sigs
        common_sigs = old_sigs & new_sigs

        added = [new_map[sig] for sig in added_sigs]
        removed = [old_map[sig] for sig in removed_sigs]

        # Find modified edges (same endpoints, different properties)
        modified = []
        for sig in common_sigs:
            old_edge = old_map[sig]
            new_edge = new_map[sig]

            if old_edge.get('props') != new_edge.get('props'):
                modified.append({
                    "signature": sig,
                    "old": old_edge,
                    "new": new_edge
                })

        return EdgeDiff(added=added, removed=removed, modified=modified)

    def _get_node_id(self, node: Dict) -> str:
        """Extract node ID from node data."""
        if 'n' in node and isinstance(node['n'], dict):
            return node['n'].get('id', '')
        return node.get('id', '')

    def _nodes_differ(self, old_node: Dict, new_node: Dict) -> bool:
        """Check if two nodes are different."""
        old_props = old_node.get('n', {}) if 'n' in old_node else old_node
        new_props = new_node.get('n', {}) if 'n' in new_node else new_node

        # Compare relevant properties (ignore internal IDs)
        ignore_keys = {'node_id', 'id'}
        old_keys = set(old_props.keys()) - ignore_keys
        new_keys = set(new_props.keys()) - ignore_keys

        if old_keys != new_keys:
            return True

        for key in old_keys:
            if old_props.get(key) != new_props.get(key):
                return True

        return False

    def _get_node_changes(self, old_node: Dict, new_node: Dict) -> Dict[str, Any]:
        """Get specific changes between two nodes."""
        old_props = old_node.get('n', {}) if 'n' in old_node else old_node
        new_props = new_node.get('n', {}) if 'n' in new_node else new_node

        changes = {}
        all_keys = set(old_props.keys()) | set(new_props.keys())
        ignore_keys = {'node_id', 'id'}

        for key in all_keys - ignore_keys:
            old_val = old_props.get(key)
            new_val = new_props.get(key)

            if old_val != new_val:
                changes[key] = {
                    "old": old_val,
                    "new": new_val
                }

        return changes

    def get_snapshot_data(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full snapshot data including nodes and edges.

        Args:
            snapshot_id: Snapshot ID

        Returns:
            Snapshot data or None
        """
        return self._snapshots.get(snapshot_id)

    def restore_snapshot(self, snapshot_id: str) -> bool:
        """
        Restore graph to a previous snapshot state.

        Warning: This clears the current graph and restores from snapshot.

        Args:
            snapshot_id: Snapshot ID to restore

        Returns:
            True if successful
        """
        if snapshot_id not in self._snapshots:
            return False

        snapshot_data = self._snapshots[snapshot_id]

        # Clear current graph
        self.db.clear_database()

        # Restore nodes
        for node_data in snapshot_data["nodes"]:
            node = node_data.get('n', node_data)
            labels = node_data.get('labels', ['Unknown'])
            label = labels[0] if labels else 'Unknown'

            # Create node with properties
            props = {k: v for k, v in node.items() if k != 'node_id'}
            if props:
                query = f"CREATE (n:{label} $props)"
                self.db.execute_query(query, {"props": props})

        # Restore edges
        for edge_data in snapshot_data["edges"]:
            source = edge_data['source']
            target = edge_data['target']
            rel_type = edge_data['rel_type']
            props = edge_data.get('props', {})

            query = f"""
            MATCH (a {{id: $source}}), (b {{id: $target}})
            CREATE (a)-[r:{rel_type}]->(b)
            SET r = $props
            """
            self.db.execute_query(query, {
                "source": source,
                "target": target,
                "props": props
            })

        return True
