"""Git-based snapshot manager for automatic versioning from git history."""

import subprocess
import os
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from .parser import PythonParser
from .db import CodeGraphDB

logger = logging.getLogger(__name__)


@dataclass
class CommitInfo:
    """Information about a git commit."""
    hash: str
    short_hash: str
    message: str
    author: str
    date: str
    indexed: bool = False


class GitSnapshotManager:
    """Manages graph snapshots based on git history."""

    def __init__(self, repo_path: str, storage_dir: str, db: Optional[CodeGraphDB] = None):
        """
        Initialize git snapshot manager.

        Args:
            repo_path: Path to git repository
            storage_dir: Directory to store snapshot JSON files
            db: Optional CodeGraphDB instance for current graph
        """
        self.repo_path = repo_path
        self.storage_dir = storage_dir
        self.db = db

        # Create storage directory
        os.makedirs(storage_dir, exist_ok=True)

        # Verify it's a git repo
        if not os.path.exists(os.path.join(repo_path, '.git')):
            raise ValueError(f"{repo_path} is not a git repository")

    def list_commits(self, limit: int = 50, branch: str = "HEAD") -> List[CommitInfo]:
        """
        Get git commit history.

        Args:
            limit: Maximum number of commits to return
            branch: Branch to list commits from

        Returns:
            List of CommitInfo objects
        """
        try:
            result = subprocess.run(
                ['git', 'log', branch, f'--max-count={limit}',
                 '--format=%H|%h|%s|%an|%aI'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )

            commits = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue

                parts = line.split('|', 4)
                if len(parts) >= 5:
                    commit = CommitInfo(
                        hash=parts[0],
                        short_hash=parts[1],
                        message=parts[2],
                        author=parts[3],
                        date=parts[4],
                        indexed=self.is_indexed(parts[0])
                    )
                    commits.append(commit)

            return commits

        except subprocess.CalledProcessError as e:
            logger.error(f"Git log failed: {e.stderr}")
            return []

    def get_commit_info(self, commit_hash: str) -> Optional[CommitInfo]:
        """
        Get information about a specific commit.

        Args:
            commit_hash: Full or short commit hash

        Returns:
            CommitInfo or None if not found
        """
        try:
            result = subprocess.run(
                ['git', 'log', '-1', commit_hash, '--format=%H|%h|%s|%an|%aI'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )

            line = result.stdout.strip()
            if not line:
                return None

            parts = line.split('|', 4)
            if len(parts) >= 5:
                return CommitInfo(
                    hash=parts[0],
                    short_hash=parts[1],
                    message=parts[2],
                    author=parts[3],
                    date=parts[4],
                    indexed=self.is_indexed(parts[0])
                )

            return None

        except subprocess.CalledProcessError:
            return None

    def is_indexed(self, commit_hash: str) -> bool:
        """Check if a commit has been indexed."""
        filepath = os.path.join(self.storage_dir, f"{commit_hash}.json")
        return os.path.exists(filepath)

    def index_commit(self, commit_hash: str, paths: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Index code at a specific commit.

        Args:
            commit_hash: Commit hash to index
            paths: Optional list of paths to index (defaults to all Python files)

        Returns:
            Snapshot data with statistics
        """
        # Get commit info
        commit_info = self.get_commit_info(commit_hash)
        if not commit_info:
            raise ValueError(f"Commit {commit_hash} not found")

        # Get files at commit
        files = self._get_files_at_commit(commit_hash, paths)

        if not files:
            logger.warning(f"No Python files found at commit {commit_hash}")

        # Parse files and accumulate results
        parser = PythonParser()
        all_entities = {}
        all_relationships = []

        for filepath, content in files.items():
            try:
                entities, relationships = parser.parse_source(content, filepath)
                all_entities.update(entities)
                all_relationships.extend(relationships)
            except Exception as e:
                logger.warning(f"Failed to parse {filepath} at {commit_hash}: {e}")
                continue

        # Use accumulated results
        entities = all_entities
        relationships = all_relationships

        # Convert to snapshot format
        nodes = []
        for entity_id, entity in entities.items():
            node = {
                "id": entity.id,
                "labels": [entity.node_type],
                "properties": self._entity_to_properties(entity)
            }
            nodes.append(node)

        edges = []
        for rel in relationships:
            edge = {
                "source": rel.from_id,
                "target": rel.to_id,
                "type": rel.rel_type,
                "properties": rel.properties
            }
            edges.append(edge)

        # Build snapshot
        snapshot = {
            "commit_hash": commit_info.hash,
            "short_hash": commit_info.short_hash,
            "message": commit_info.message,
            "author": commit_info.author,
            "date": commit_info.date,
            "indexed_at": datetime.now().isoformat(),
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes,
            "edges": edges
        }

        # Save to disk
        self._save_snapshot(commit_info.hash, snapshot)

        logger.info(f"Indexed commit {commit_info.short_hash}: {len(nodes)} nodes, {len(edges)} edges")

        return {
            "commit_hash": commit_info.hash,
            "short_hash": commit_info.short_hash,
            "message": commit_info.message,
            "node_count": len(nodes),
            "edge_count": len(edges)
        }

    def _get_files_at_commit(self, commit_hash: str, paths: Optional[List[str]] = None) -> Dict[str, str]:
        """
        Get Python files at a specific commit.

        Args:
            commit_hash: Commit hash
            paths: Optional paths to filter

        Returns:
            Dictionary mapping filepath to content
        """
        # List files at commit
        try:
            result = subprocess.run(
                ['git', 'ls-tree', '-r', '--name-only', commit_hash],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to list files at {commit_hash}: {e}")
            return {}

        files = {}
        for filepath in result.stdout.strip().split('\n'):
            if not filepath:
                continue

            # Filter by extension
            if not filepath.endswith('.py'):
                continue

            # Filter by paths if specified
            if paths:
                if not any(filepath.startswith(p) or filepath == p for p in paths):
                    continue

            # Skip test files and __pycache__
            if '__pycache__' in filepath or 'test_' in filepath or '_test.py' in filepath:
                continue

            # Get file content
            try:
                content_result = subprocess.run(
                    ['git', 'show', f'{commit_hash}:{filepath}'],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
                files[filepath] = content_result.stdout
            except subprocess.CalledProcessError as e:
                logger.warning(f"Failed to get {filepath} at {commit_hash}: {e}")
                continue

        return files

    def _entity_to_properties(self, entity) -> Dict[str, Any]:
        """Convert entity to properties dictionary."""
        props = {
            "id": entity.id,
            "name": entity.name,
            "location": entity.location
        }

        # Add type-specific properties
        for attr in ['qualified_name', 'signature', 'return_type', 'visibility',
                     'is_async', 'docstring', 'type_annotation', 'scope',
                     'position', 'default_value', 'kind', 'is_external',
                     'path', 'package']:
            if hasattr(entity, attr):
                value = getattr(entity, attr)
                if value is not None:
                    props[attr] = value

        return props

    def _save_snapshot(self, commit_hash: str, snapshot: Dict[str, Any]):
        """Save snapshot to disk."""
        filepath = os.path.join(self.storage_dir, f"{commit_hash}.json")
        with open(filepath, 'w') as f:
            json.dump(snapshot, f, indent=2, default=str)
        logger.info(f"Saved snapshot to {filepath}")

    def get_snapshot(self, commit_hash: str, auto_index: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get snapshot for a commit.

        Args:
            commit_hash: Commit hash
            auto_index: If True, index the commit if not already indexed

        Returns:
            Snapshot data or None
        """
        filepath = os.path.join(self.storage_dir, f"{commit_hash}.json")

        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)

        if auto_index:
            self.index_commit(commit_hash)
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    return json.load(f)

        return None

    def get_snapshot_graph(self, commit_hash: str) -> Dict[str, Any]:
        """
        Get graph data for a commit (nodes and edges only).

        Args:
            commit_hash: Commit hash

        Returns:
            Dictionary with nodes and edges
        """
        snapshot = self.get_snapshot(commit_hash)
        if not snapshot:
            return {"nodes": [], "edges": []}

        return {
            "nodes": snapshot.get("nodes", []),
            "edges": snapshot.get("edges", [])
        }

    def compare_commits(self, old_hash: str, new_hash: str) -> Dict[str, Any]:
        """
        Compare two commits and return differences.

        Args:
            old_hash: Old commit hash
            new_hash: New commit hash

        Returns:
            Diff data
        """
        old_snapshot = self.get_snapshot(old_hash)
        new_snapshot = self.get_snapshot(new_hash)

        if not old_snapshot or not new_snapshot:
            raise ValueError("One or both commits not found/indexed")

        # Compare nodes
        old_nodes = {n['id']: n for n in old_snapshot['nodes']}
        new_nodes = {n['id']: n for n in new_snapshot['nodes']}

        old_ids = set(old_nodes.keys())
        new_ids = set(new_nodes.keys())

        nodes_added = [new_nodes[nid] for nid in (new_ids - old_ids)]
        nodes_removed = [old_nodes[nid] for nid in (old_ids - new_ids)]

        # Find modified nodes
        nodes_modified = []
        for nid in (old_ids & new_ids):
            old_props = old_nodes[nid].get('properties', {})
            new_props = new_nodes[nid].get('properties', {})

            if old_props != new_props:
                changes = {}
                all_keys = set(old_props.keys()) | set(new_props.keys())
                for key in all_keys:
                    if key in ['id', 'node_id']:
                        continue
                    old_val = old_props.get(key)
                    new_val = new_props.get(key)
                    if old_val != new_val:
                        changes[key] = {"old": old_val, "new": new_val}

                if changes:
                    nodes_modified.append({
                        "id": nid,
                        "old": old_nodes[nid],
                        "new": new_nodes[nid],
                        "changes": changes
                    })

        # Compare edges
        def edge_sig(e):
            return f"{e['source']}-{e['type']}->{e['target']}"

        old_edges = {edge_sig(e): e for e in old_snapshot['edges']}
        new_edges = {edge_sig(e): e for e in new_snapshot['edges']}

        old_sigs = set(old_edges.keys())
        new_sigs = set(new_edges.keys())

        edges_added = [new_edges[sig] for sig in (new_sigs - old_sigs)]
        edges_removed = [old_edges[sig] for sig in (old_sigs - new_sigs)]

        # Summary
        summary = {
            "nodes_added": len(nodes_added),
            "nodes_removed": len(nodes_removed),
            "nodes_modified": len(nodes_modified),
            "edges_added": len(edges_added),
            "edges_removed": len(edges_removed),
            "edges_modified": 0
        }

        return {
            "old_commit": old_hash,
            "new_commit": new_hash,
            "old_info": {
                "hash": old_snapshot.get('commit_hash'),
                "message": old_snapshot.get('message'),
                "date": old_snapshot.get('date')
            },
            "new_info": {
                "hash": new_snapshot.get('commit_hash'),
                "message": new_snapshot.get('message'),
                "date": new_snapshot.get('date')
            },
            "summary": summary,
            "nodes": {
                "added": nodes_added,
                "removed": nodes_removed,
                "modified": nodes_modified
            },
            "edges": {
                "added": edges_added,
                "removed": edges_removed,
                "modified": []
            }
        }

    def delete_snapshot(self, commit_hash: str) -> bool:
        """
        Delete a snapshot file.

        Args:
            commit_hash: Commit hash

        Returns:
            True if deleted
        """
        filepath = os.path.join(self.storage_dir, f"{commit_hash}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"Deleted snapshot {commit_hash}")
            return True
        return False

    def get_current_commit(self) -> Optional[str]:
        """Get the current HEAD commit hash."""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None

    def get_files_changed_in_commit(self, commit_hash: str) -> List[str]:
        """
        Get list of files changed in a commit.

        Args:
            commit_hash: Commit hash

        Returns:
            List of file paths
        """
        try:
            result = subprocess.run(
                ['git', 'diff-tree', '--no-commit-id', '--name-only', '-r', commit_hash],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return [f for f in result.stdout.strip().split('\n') if f]
        except subprocess.CalledProcessError:
            return []

    def list_indexed_commits(self) -> List[str]:
        """Get list of all indexed commit hashes."""
        indexed = []
        if os.path.exists(self.storage_dir):
            for filename in os.listdir(self.storage_dir):
                if filename.endswith('.json'):
                    indexed.append(filename[:-5])
        return indexed
