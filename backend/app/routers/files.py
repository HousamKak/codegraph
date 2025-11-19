"""File-based endpoints for viewing graph and history per file."""

import os
import subprocess
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
import logging

from codegraph import PythonParser, GraphBuilder
from ..database import get_db
from ..models import GraphResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["Files"])


@router.get("")
async def list_files(
    directory: str = Query(..., description="Directory to list files from"),
    recursive: bool = Query(False, description="Recursively list all files and folders")
):
    """
    List files in a directory. If recursive=true, returns full tree structure.
    """
    if not os.path.exists(directory):
        raise HTTPException(status_code=404, detail=f"Directory not found: {directory}")

    if not os.path.isdir(directory):
        raise HTTPException(status_code=400, detail=f"Not a directory: {directory}")

    if recursive:
        # Return full directory tree
        def build_tree(path: str) -> dict:
            items = []
            try:
                entries = os.listdir(path)
            except (PermissionError, OSError):
                return items

            for entry in sorted(entries):
                # Skip hidden files and common ignore patterns
                if entry.startswith('.') or entry in {'__pycache__', 'venv', '.venv', 'node_modules', '.mypy_cache', 'dist', 'build'}:
                    continue

                try:
                    full_path = os.path.join(path, entry)

                    # Skip if path doesn't exist or is inaccessible
                    if not os.path.exists(full_path):
                        continue

                    rel_path = os.path.relpath(full_path, directory)

                    if os.path.isdir(full_path):
                        items.append({
                            "name": entry,
                            "path": full_path,
                            "relative_path": rel_path,
                            "is_directory": True,
                            "children": build_tree(full_path)
                        })
                    else:
                        items.append({
                            "name": entry,
                            "path": full_path,
                            "relative_path": rel_path,
                            "is_directory": False,
                            "is_python": entry.endswith('.py'),
                            "size": os.path.getsize(full_path)
                        })
                except (OSError, ValueError) as e:
                    # Skip files that cause errors (e.g., special files, permission issues, path issues)
                    logger.debug(f"Skipping {entry}: {e}")
                    continue

            return items

        tree = build_tree(directory)
        return {
            "directory": directory,
            "tree": tree,
            "recursive": True
        }
    else:
        # Return flat list of Python files only
        files = []
        for root, dirs, filenames in os.walk(directory):
            # Skip common directories
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'venv', '.venv', 'node_modules', '.mypy_cache'}]

            for filename in filenames:
                if filename.endswith('.py'):
                    filepath = os.path.join(root, filename)
                    rel_path = os.path.relpath(filepath, directory)
                    files.append({
                        "path": filepath,
                        "relative_path": rel_path,
                        "name": filename,
                        "size": os.path.getsize(filepath)
                    })

        return {
            "directory": directory,
            "files": sorted(files, key=lambda f: f["relative_path"]),
            "count": len(files)
        }


@router.get("/graph")
async def get_file_graph(file_path: str = Query(..., description="Path to Python file")):
    """
    Get graph data for a specific file.

    Parses the file and returns nodes and edges.
    """
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    if not file_path.endswith('.py'):
        raise HTTPException(status_code=400, detail="Only Python files are supported")

    try:
        parser = PythonParser()
        entities, relationships = parser.parse_file(file_path)

        # Convert to graph format
        nodes = []
        for entity_id, entity in entities.items():
            node = {
                "id": entity.id,
                "labels": [entity.node_type],
                "properties": {
                    "name": entity.name,
                    "location": entity.location,
                }
            }
            # Add optional properties
            for attr in ['qualified_name', 'signature', 'return_type', 'type_annotation',
                        'docstring', 'visibility', 'is_async']:
                if hasattr(entity, attr):
                    value = getattr(entity, attr)
                    if value is not None:
                        node["properties"][attr] = value
            nodes.append(node)

        edges = []
        for rel in relationships:
            edges.append({
                "source": rel.from_id,
                "target": rel.to_id,
                "type": rel.rel_type,
                "properties": rel.properties
            })

        return GraphResponse(nodes=nodes, edges=edges)

    except Exception as e:
        logger.error(f"Failed to parse file {file_path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_file_history(
    file_path: str = Query(..., description="Path to file"),
    limit: int = Query(20, description="Maximum number of commits")
):
    """
    Get git history for a specific file.
    """
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    # Find git repo root
    search_path = os.path.dirname(os.path.abspath(file_path))
    repo_root = None
    while search_path:
        if os.path.exists(os.path.join(search_path, '.git')):
            repo_root = search_path
            break
        parent = os.path.dirname(search_path)
        if parent == search_path:
            break
        search_path = parent

    if not repo_root:
        raise HTTPException(status_code=400, detail="File is not in a git repository")

    try:
        # Get relative path from repo root
        rel_path = os.path.relpath(file_path, repo_root)

        # Get git log for this file
        result = subprocess.run(
            ['git', 'log', f'-{limit}', '--pretty=format:%H|%h|%s|%an|%aI', '--follow', '--', rel_path],
            cwd=repo_root,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Git error: {result.stderr}")

        commits = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            parts = line.split('|')
            if len(parts) >= 5:
                commits.append({
                    "hash": parts[0],
                    "short_hash": parts[1],
                    "message": parts[2],
                    "author": parts[3],
                    "date": parts[4]
                })

        return {
            "file_path": file_path,
            "relative_path": rel_path,
            "commits": commits,
            "count": len(commits)
        }

    except subprocess.SubprocessError as e:
        logger.error(f"Git command failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/at-commit")
async def get_file_at_commit(
    file_path: str = Query(..., description="Path to file"),
    commit_hash: str = Query(..., description="Git commit hash")
):
    """
    Get file content and graph at a specific commit.
    """
    if not os.path.exists(file_path):
        # File might exist in git history even if deleted
        pass

    # Find git repo root
    search_path = os.path.dirname(os.path.abspath(file_path))
    repo_root = None
    while search_path:
        if os.path.exists(os.path.join(search_path, '.git')):
            repo_root = search_path
            break
        parent = os.path.dirname(search_path)
        if parent == search_path:
            break
        search_path = parent

    if not repo_root:
        raise HTTPException(status_code=400, detail="File is not in a git repository")

    try:
        rel_path = os.path.relpath(file_path, repo_root)

        # Get file content at commit
        result = subprocess.run(
            ['git', 'show', f'{commit_hash}:{rel_path}'],
            cwd=repo_root,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise HTTPException(status_code=404, detail=f"File not found at commit {commit_hash}")

        content = result.stdout

        # Parse the content
        parser = PythonParser()
        entities, relationships = parser.parse_source(content, file_path)

        # Convert to graph format
        nodes = []
        for entity_id, entity in entities.items():
            node = {
                "id": entity.id,
                "labels": [entity.node_type],
                "properties": {
                    "name": entity.name,
                    "location": entity.location,
                }
            }
            for attr in ['qualified_name', 'signature', 'return_type', 'type_annotation',
                        'docstring', 'visibility', 'is_async']:
                if hasattr(entity, attr):
                    value = getattr(entity, attr)
                    if value is not None:
                        node["properties"][attr] = value
            nodes.append(node)

        edges = []
        for rel in relationships:
            edges.append({
                "source": rel.from_id,
                "target": rel.to_id,
                "type": rel.rel_type,
                "properties": rel.properties
            })

        return {
            "file_path": file_path,
            "commit_hash": commit_hash,
            "graph": GraphResponse(nodes=nodes, edges=edges)
        }

    except subprocess.SubprocessError as e:
        logger.error(f"Git command failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
