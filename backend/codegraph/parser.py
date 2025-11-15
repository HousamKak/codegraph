"""Python AST parser to extract code entities and relationships."""

import ast
import os
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import hashlib
import logging

logger = logging.getLogger(__name__)


@dataclass
class Entity:
    """Base class for code entities."""
    id: str
    name: str
    location: str
    node_type: str


@dataclass
class FunctionEntity(Entity):
    """Represents a function or method."""
    qualified_name: str = ""
    signature: str = ""
    return_type: Optional[str] = None
    visibility: str = "public"
    is_async: bool = False
    docstring: Optional[str] = None
    parameters: List['ParameterEntity'] = field(default_factory=list)


@dataclass
class ClassEntity(Entity):
    """Represents a class."""
    qualified_name: str = ""
    visibility: str = "public"
    docstring: Optional[str] = None
    bases: List[str] = field(default_factory=list)
    methods: List[FunctionEntity] = field(default_factory=list)


@dataclass
class VariableEntity(Entity):
    """Represents a variable."""
    type_annotation: Optional[str] = None
    scope: str = "local"


@dataclass
class ParameterEntity(Entity):
    """Represents a function parameter."""
    type_annotation: Optional[str] = None
    position: int = 0
    default_value: Optional[str] = None
    kind: str = "positional"  # positional, keyword, var_positional, var_keyword


@dataclass
class Relationship:
    """Represents a relationship between entities."""
    from_id: str
    to_id: str
    rel_type: str
    properties: Dict[str, Any] = field(default_factory=dict)


class PythonParser:
    """Parses Python source code and extracts entities and relationships."""

    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.relationships: List[Relationship] = []
        self.current_module: str = ""
        self.current_class: Optional[str] = None
        self.current_function: Optional[str] = None
        self.scope_stack: List[str] = []

    def parse_file(self, file_path: str) -> Tuple[Dict[str, Entity], List[Relationship]]:
        """
        Parse a Python file and extract entities and relationships.

        Args:
            file_path: Path to Python file

        Returns:
            Tuple of (entities dict, relationships list)
        """
        self.entities = {}
        self.relationships = []
        self.current_module = self._get_module_name(file_path)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()

            tree = ast.parse(source, filename=file_path)
            self._visit_module(tree, file_path)

            logger.info(f"Parsed {file_path}: {len(self.entities)} entities, {len(self.relationships)} relationships")
            return self.entities, self.relationships

        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return {}, []

    def parse_directory(self, directory: str) -> Tuple[Dict[str, Entity], List[Relationship]]:
        """
        Parse all Python files in a directory recursively.

        Args:
            directory: Directory path

        Returns:
            Tuple of (entities dict, relationships list)
        """
        all_entities = {}
        all_relationships = []

        for root, dirs, files in os.walk(directory):
            # Skip common directories to ignore
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'venv', '.venv', 'node_modules'}]

            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    entities, relationships = self.parse_file(file_path)
                    all_entities.update(entities)
                    all_relationships.extend(relationships)

        logger.info(f"Parsed directory {directory}: {len(all_entities)} entities, {len(all_relationships)} relationships")
        return all_entities, all_relationships

    def _get_module_name(self, file_path: str) -> str:
        """Extract module name from file path."""
        # Convert file path to module name (e.g., src/foo/bar.py -> src.foo.bar)
        name = file_path.replace(os.sep, '.').replace('.py', '')
        return name

    def _make_id(self, *parts: str) -> str:
        """Generate unique ID from parts."""
        combined = ":".join(str(p) for p in parts)
        return hashlib.md5(combined.encode()).hexdigest()[:16]

    def _get_location(self, node: ast.AST, file_path: str) -> str:
        """Get location string from AST node."""
        if hasattr(node, 'lineno') and hasattr(node, 'col_offset'):
            return f"{file_path}:{node.lineno}:{node.col_offset}"
        return file_path

    def _get_type_annotation(self, annotation: Optional[ast.AST]) -> Optional[str]:
        """Extract type annotation as string."""
        if annotation is None:
            return None
        try:
            return ast.unparse(annotation)
        except Exception:
            return None

    def _is_private(self, name: str) -> bool:
        """Check if name indicates private visibility."""
        return name.startswith('_') and not name.startswith('__')

    def _visit_module(self, tree: ast.Module, file_path: str):
        """Visit module-level nodes."""
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                self._visit_function(node, file_path)
            elif isinstance(node, ast.ClassDef):
                self._visit_class(node, file_path)
            elif isinstance(node, ast.Assign) or isinstance(node, ast.AnnAssign):
                self._visit_assignment(node, file_path, scope="module")
            elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                self._visit_import(node, file_path)

    def _visit_function(self, node: ast.FunctionDef, file_path: str, class_name: Optional[str] = None):
        """Visit function definition."""
        func_name = node.name
        qualified_name = f"{self.current_module}.{class_name}.{func_name}" if class_name else f"{self.current_module}.{func_name}"

        func_id = self._make_id(qualified_name)

        # Extract return type
        return_type = self._get_type_annotation(node.returns)

        # Get docstring
        docstring = ast.get_docstring(node)

        # Build signature
        args_str = self._build_signature(node.args)
        signature = f"{func_name}({args_str})"
        if return_type:
            signature += f" -> {return_type}"

        # Create function entity
        func_entity = FunctionEntity(
            id=func_id,
            name=func_name,
            qualified_name=qualified_name,
            location=self._get_location(node, file_path),
            node_type="Function",
            signature=signature,
            return_type=return_type,
            visibility="private" if self._is_private(func_name) else "public",
            is_async=isinstance(node, ast.AsyncFunctionDef),
            docstring=docstring
        )

        # Parse parameters
        self._visit_parameters(node.args, func_id, file_path)

        self.entities[func_id] = func_entity

        # Visit function body for calls and references
        old_function = self.current_function
        self.current_function = func_id
        for stmt in node.body:
            self._visit_statement(stmt, file_path, func_id)
        self.current_function = old_function

    def _build_signature(self, args: ast.arguments) -> str:
        """Build function signature string from arguments."""
        parts = []

        # Regular args
        for arg in args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {ast.unparse(arg.annotation)}"
            parts.append(arg_str)

        # *args
        if args.vararg:
            vararg_str = f"*{args.vararg.arg}"
            if args.vararg.annotation:
                vararg_str += f": {ast.unparse(args.vararg.annotation)}"
            parts.append(vararg_str)

        # **kwargs
        if args.kwarg:
            kwarg_str = f"**{args.kwarg.arg}"
            if args.kwarg.annotation:
                kwarg_str += f": {ast.unparse(args.kwarg.annotation)}"
            parts.append(kwarg_str)

        return ", ".join(parts)

    def _visit_parameters(self, args: ast.arguments, func_id: str, file_path: str):
        """Visit function parameters."""
        position = 0

        # Regular parameters
        for i, arg in enumerate(args.args):
            param_id = self._make_id(func_id, arg.arg, position)
            default_value = None
            if i >= len(args.args) - len(args.defaults):
                default_idx = i - (len(args.args) - len(args.defaults))
                try:
                    default_value = ast.unparse(args.defaults[default_idx])
                except Exception:
                    default_value = "<complex>"

            param_entity = ParameterEntity(
                id=param_id,
                name=arg.arg,
                location=self._get_location(arg, file_path),
                node_type="Parameter",
                type_annotation=self._get_type_annotation(arg.annotation),
                position=position,
                default_value=default_value,
                kind="positional"
            )
            self.entities[param_id] = param_entity

            # Create HAS_PARAMETER relationship
            self.relationships.append(Relationship(
                from_id=func_id,
                to_id=param_id,
                rel_type="HAS_PARAMETER",
                properties={"position": position}
            ))
            position += 1

        # *args
        if args.vararg:
            param_id = self._make_id(func_id, args.vararg.arg, position)
            param_entity = ParameterEntity(
                id=param_id,
                name=args.vararg.arg,
                location=self._get_location(args.vararg, file_path),
                node_type="Parameter",
                type_annotation=self._get_type_annotation(args.vararg.annotation),
                position=position,
                kind="var_positional"
            )
            self.entities[param_id] = param_entity
            self.relationships.append(Relationship(
                from_id=func_id,
                to_id=param_id,
                rel_type="HAS_PARAMETER",
                properties={"position": position}
            ))
            position += 1

        # **kwargs
        if args.kwarg:
            param_id = self._make_id(func_id, args.kwarg.arg, position)
            param_entity = ParameterEntity(
                id=param_id,
                name=args.kwarg.arg,
                location=self._get_location(args.kwarg, file_path),
                node_type="Parameter",
                type_annotation=self._get_type_annotation(args.kwarg.annotation),
                position=position,
                kind="var_keyword"
            )
            self.entities[param_id] = param_entity
            self.relationships.append(Relationship(
                from_id=func_id,
                to_id=param_id,
                rel_type="HAS_PARAMETER",
                properties={"position": position}
            ))

    def _visit_class(self, node: ast.ClassDef, file_path: str):
        """Visit class definition."""
        class_name = node.name
        qualified_name = f"{self.current_module}.{class_name}"
        class_id = self._make_id(qualified_name)

        # Get bases
        bases = []
        for base in node.bases:
            try:
                bases.append(ast.unparse(base))
            except Exception:
                bases.append("<unknown>")

        # Get docstring
        docstring = ast.get_docstring(node)

        class_entity = ClassEntity(
            id=class_id,
            name=class_name,
            qualified_name=qualified_name,
            location=self._get_location(node, file_path),
            node_type="Class",
            visibility="private" if self._is_private(class_name) else "public",
            docstring=docstring,
            bases=bases
        )

        self.entities[class_id] = class_entity

        # Visit class body
        old_class = self.current_class
        self.current_class = class_id
        for stmt in node.body:
            if isinstance(stmt, ast.FunctionDef) or isinstance(stmt, ast.AsyncFunctionDef):
                self._visit_function(stmt, file_path, class_name)
            elif isinstance(stmt, ast.Assign) or isinstance(stmt, ast.AnnAssign):
                self._visit_assignment(stmt, file_path, scope="class")
        self.current_class = old_class

    def _visit_assignment(self, node: ast.AST, file_path: str, scope: str):
        """Visit assignment statements to track variables."""
        # For now, just track module-level and class-level variables
        if scope in ["module", "class"]:
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                var_name = node.target.id
                var_id = self._make_id(self.current_module, self.current_class or "", var_name)
                var_entity = VariableEntity(
                    id=var_id,
                    name=var_name,
                    location=self._get_location(node, file_path),
                    node_type="Variable",
                    type_annotation=self._get_type_annotation(node.annotation),
                    scope=scope
                )
                self.entities[var_id] = var_entity

    def _visit_statement(self, node: ast.AST, file_path: str, func_id: str):
        """Visit statements within functions to find calls and references."""
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            self._visit_call(node.value, file_path, func_id)
        elif isinstance(node, ast.Assign):
            # Check if RHS has calls
            for value_node in ast.walk(node.value):
                if isinstance(value_node, ast.Call):
                    self._visit_call(value_node, file_path, func_id)
        elif isinstance(node, ast.Return) and node.value:
            for value_node in ast.walk(node.value):
                if isinstance(value_node, ast.Call):
                    self._visit_call(value_node, file_path, func_id)

        # Recursively visit nested statements
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                for stmt in getattr(child, 'body', []):
                    self._visit_statement(stmt, file_path, func_id)
                for stmt in getattr(child, 'orelse', []):
                    self._visit_statement(stmt, file_path, func_id)

    def _visit_call(self, node: ast.Call, file_path: str, caller_id: str):
        """Visit function call to create CALLS relationship."""
        # Try to extract callee name
        callee_name = None
        if isinstance(node.func, ast.Name):
            callee_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            callee_name = ast.unparse(node.func)

        if callee_name:
            # For now, create a placeholder relationship
            # We'll resolve the actual target later
            arg_count = len(node.args) + len(node.keywords)
            self.relationships.append(Relationship(
                from_id=caller_id,
                to_id=f"unresolved:{callee_name}",  # Will be resolved later
                rel_type="CALLS",
                properties={
                    "callee_name": callee_name,
                    "arg_count": arg_count,
                    "location": self._get_location(node, file_path)
                }
            ))

    def _visit_import(self, node: ast.AST, file_path: str):
        """Visit import statements."""
        # TODO: Track imports for cross-module references
        pass
