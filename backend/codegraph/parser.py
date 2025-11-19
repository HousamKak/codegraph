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
    is_generator: bool = False
    is_staticmethod: bool = False
    is_classmethod: bool = False
    is_property: bool = False
    docstring: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    parameters: List['ParameterEntity'] = field(default_factory=list)


@dataclass
class ModuleEntity(Entity):
    """Represents a Python module."""
    qualified_name: str = ""
    path: str = ""
    package: Optional[str] = None
    docstring: Optional[str] = None
    is_external: bool = False


@dataclass
class ClassEntity(Entity):
    """Represents a class."""
    qualified_name: str = ""
    visibility: str = "public"
    docstring: Optional[str] = None
    bases: List[str] = field(default_factory=list)
    methods: List[FunctionEntity] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)


@dataclass
class VariableEntity(Entity):
    """Represents a variable."""
    type_annotation: Optional[str] = None
    scope: str = "local"
    inferred_types: List[str] = field(default_factory=list)


@dataclass
class ParameterEntity(Entity):
    """Represents a function parameter."""
    type_annotation: Optional[str] = None
    position: int = 0
    default_value: Optional[str] = None
    kind: str = "positional"  # positional, keyword, var_positional, var_keyword


@dataclass
class CallSiteEntity(Entity):
    """Represents a specific call site (location where a function is called)."""
    caller_id: str = ""
    arg_count: int = 0
    has_args: bool = False  # *args
    has_kwargs: bool = False  # **kwargs
    lineno: int = 0
    col_offset: int = 0
    arg_types: List[str] = field(default_factory=list)


@dataclass
class TypeEntity(Entity):
    """Represents a type in the codebase."""
    module: str = "builtins"  # Module where type is defined
    kind: str = "class"  # class, generic, union, callable, literal
    base_types: List[str] = field(default_factory=list)  # For tracking subtype hierarchy


@dataclass
class DecoratorEntity(Entity):
    """Represents a decorator usage."""
    target_id: str = ""
    target_type: str = ""


@dataclass
class UnresolvedReferenceEntity(Entity):
    """Represents an unresolved identifier usage."""
    reference_kind: str = ""
    source_id: Optional[str] = None


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
        self.current_module_id: Optional[str] = None
        self.current_class: Optional[str] = None
        self.current_function: Optional[str] = None
        self.scope_stack: List[str] = []
        self.type_registry: Dict[str, str] = {}  # Maps type names to type IDs
        self.variable_lookup: Dict[Tuple[str, str, str], str] = {}
        self.name_index: Dict[str, List[str]] = {}
        self.builtin_types: Dict[str, str] = {}

    def parse_source(self, source: str, file_path: str) -> Tuple[Dict[str, Entity], List[Relationship]]:
        """
        Parse Python source code from a string.

        Args:
            source: Python source code
            file_path: Virtual file path for the source

        Returns:
            Tuple of (entities dict, relationships list)
        """
        self.entities = {}
        self.relationships = []
        self.current_module = self._get_module_name(file_path)
        self.current_module_id = None
        self.current_class = None
        self.current_function = None
        self.variable_lookup = {}
        self.name_index = {}
        self.type_registry = {}
        self._initialize_builtin_types()

        try:
            tree = ast.parse(source, filename=file_path)

            # Create Module entity
            module_id = self._make_id(self.current_module)
            module_docstring = ast.get_docstring(tree)

            module_entity = ModuleEntity(
                id=module_id,
                name=os.path.basename(file_path).replace('.py', ''),
                qualified_name=self.current_module,
                path=file_path,
                location=file_path,
                node_type="Module",
                package=self.current_module.rsplit('.', 1)[0] if '.' in self.current_module else None,
                docstring=module_docstring
            )
            self.entities[module_id] = module_entity
            self.current_module_id = module_id
            self._index_entity_name(module_entity)

            # Parse module contents
            self._visit_module(tree, file_path, module_id)

            # Create type relationships after parsing all entities
            self._create_type_relationships()

            logger.info(f"Parsed source for {file_path}: {len(self.entities)} entities, {len(self.relationships)} relationships")
            return self.entities, self.relationships

        except Exception as e:
            logger.error(f"Failed to parse source for {file_path}: {e}")
            return {}, []

    def parse_file(self, file_path: str) -> Tuple[Dict[str, Entity], List[Relationship]]:
        """
        Parse a Python file and extract entities and relationships.

        Args:
            file_path: Path to Python file

        Returns:
            Tuple of (entities dict, relationships list)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            return self.parse_source(source, file_path)
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")
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

    def _index_entity_name(self, entity: Entity):
        """Add entity simple name to lookup index for reference resolution."""
        if not entity.name:
            return
        entries = self.name_index.setdefault(entity.name, [])
        if entity.id not in entries:
            entries.append(entity.id)

    def _register_variable(self, var_id: str, name: str, scope_owner: Optional[str], scope_type: str):
        """Register variable for lookup in references."""
        owner = scope_owner or ""
        key = (scope_type, owner, name)
        self.variable_lookup[key] = var_id

    def _resolve_variable(self, name: str, func_id: Optional[str]) -> Optional[str]:
        """Resolve a variable name using function/class/module scope ordering."""
        if func_id:
            key = ("function", func_id, name)
            if key in self.variable_lookup:
                return self.variable_lookup[key]
        if self.current_class:
            key = ("class", self.current_class, name)
            if key in self.variable_lookup:
                return self.variable_lookup[key]
        if self.current_module_id:
            key = ("module", self.current_module_id, name)
            if key in self.variable_lookup:
                return self.variable_lookup[key]
        return None

    def _resolve_named_entity(self, name: str) -> Optional[str]:
        """Resolve a name to any indexed entity (function/class/module/type)."""
        candidates = self.name_index.get(name, [])
        if not candidates:
            return None

        # Prefer entities in the current module
        for candidate in candidates:
            entity = self.entities.get(candidate)
            if isinstance(entity, (FunctionEntity, ClassEntity)) and entity.qualified_name.startswith(self.current_module):
                return candidate

        # Fall back to first match
        return candidates[0]

    def _resolve_parameter(self, name: str, func_id: Optional[str]) -> Optional[str]:
        """
        Resolve a name to a parameter entity in the current function.

        Args:
            name: Parameter name
            func_id: Current function ID

        Returns:
            Parameter entity ID if found, None otherwise
        """
        if not func_id:
            return None

        # Check relationships to find parameters of this function
        for rel in self.relationships:
            if rel.from_id == func_id and rel.rel_type == "HAS_PARAMETER":
                param_entity = self.entities.get(rel.to_id)
                if isinstance(param_entity, ParameterEntity) and param_entity.name == name:
                    return rel.to_id

        return None

    def _infer_expression_type(self, node: Optional[ast.AST], func_id: Optional[str]) -> Optional[str]:
        """Infer a simple type string from an expression node."""
        if node is None:
            return None

        if isinstance(node, ast.Constant):
            value = node.value
            if value is None:
                return "None"
            return type(value).__name__

        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            element_types = []
            for elt in getattr(node, "elts", []):
                inferred = self._infer_expression_type(elt, func_id)
                if inferred:
                    element_types.append(inferred)
            element_types = [t for t in element_types if t]
            if element_types:
                unique = sorted(set(element_types))
                base = type(node).__name__
                if len(unique) == 1:
                    return f"{base}[{unique[0]}]"
            return type(node).__name__

        if isinstance(node, ast.Dict):
            key_types = []
            value_types = []
            for key in node.keys:
                key_types.append(self._infer_expression_type(key, func_id))
            for value in node.values:
                value_types.append(self._infer_expression_type(value, func_id))
            key_types = [t for t in key_types if t]
            value_types = [t for t in value_types if t]
            if key_types and value_types and len(set(key_types)) == 1 and len(set(value_types)) == 1:
                return f"Dict[{key_types[0]}, {value_types[0]}]"
            return "Dict"

        if isinstance(node, ast.UnaryOp):
            return self._infer_expression_type(node.operand, func_id)

        if isinstance(node, ast.BinOp):
            left_type = self._infer_expression_type(node.left, func_id)
            right_type = self._infer_expression_type(node.right, func_id)
            if left_type == right_type:
                return left_type
            numeric = {"int", "float", "complex"}
            if left_type in numeric and right_type in numeric:
                if "float" in (left_type, right_type):
                    return "float"
                return left_type or right_type
            return left_type or right_type

        if isinstance(node, ast.Name):
            # First try to resolve as a variable
            var_id = self._resolve_variable(node.id, func_id)
            if var_id:
                var_entity = self.entities.get(var_id)
                if isinstance(var_entity, VariableEntity):
                    if var_entity.type_annotation:
                        return var_entity.type_annotation
                    if var_entity.inferred_types:
                        return var_entity.inferred_types[-1]

            # Try to resolve as a parameter
            param_id = self._resolve_parameter(node.id, func_id)
            if param_id:
                param_entity = self.entities.get(param_id)
                if isinstance(param_entity, ParameterEntity) and param_entity.type_annotation:
                    return param_entity.type_annotation

            # Try to resolve as a named entity (class, function, etc.)
            target_id = self._resolve_named_entity(node.id)
            target = self.entities.get(target_id) if target_id else None
            if isinstance(target, ClassEntity):
                return target.name
            if isinstance(target, FunctionEntity):
                return "Callable"
            return None

        if isinstance(node, ast.Attribute):
            # Attempt to resolve attribute owner type, fallback to attribute name
            owner_type = self._infer_expression_type(node.value, func_id)
            if owner_type:
                return f"{owner_type}.{node.attr}"
            return None

        if isinstance(node, ast.Call):
            func_name = None
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr

            builtin_returns = {
                "int": "int",
                "float": "float",
                "str": "str",
                "bool": "bool",
                "list": "List",
                "dict": "Dict",
                "set": "Set",
                "tuple": "Tuple"
            }
            if func_name in builtin_returns:
                return builtin_returns[func_name]

            resolved_id = self._resolve_named_entity(func_name) if func_name else None
            if resolved_id:
                target = self.entities.get(resolved_id)
                if isinstance(target, ClassEntity):
                    return target.name
                if isinstance(target, FunctionEntity) and target.return_type:
                    return target.return_type

            return None

        if isinstance(node, ast.Compare):
            # Comparisons return bool
            return "bool"

        return None

    def _record_unresolved_reference(self, name: str, func_id: Optional[str],
                                     file_path: str, node: ast.AST, reference_kind: str):
        """Create unresolved reference entity so it can be validated later."""
        location = self._get_location(node, file_path)
        owner = func_id or self.current_class or self.current_module_id or file_path
        unresolved_id = self._make_id(owner or "", name, location, reference_kind, "unresolved")

        if unresolved_id not in self.entities:
            unresolved_entity = UnresolvedReferenceEntity(
                id=unresolved_id,
                name=name,
                location=location,
                node_type="Unresolved",
                reference_kind=reference_kind,
                source_id=owner
            )
            self.entities[unresolved_id] = unresolved_entity

        source_id = func_id or owner
        if source_id:
            self.relationships.append(Relationship(
                from_id=source_id,
                to_id=unresolved_id,
                rel_type="UNRESOLVED_REFERENCE",
                properties={"location": location, "reference_kind": reference_kind}
            ))

    def _record_reference(self, from_id: str, to_id: str, access_type: str, location: str):
        """Record REFERENCES relationship with metadata."""
        self.relationships.append(Relationship(
            from_id=from_id,
            to_id=to_id,
            rel_type="REFERENCES",
            properties={
                "access_type": access_type,
                "location": location
            }
        ))

    def _get_or_create_local_variable(self, name: str, func_id: str, file_path: str, node: ast.AST, type_annotation: Optional[ast.AST] = None) -> str:
        """Create or reuse a function-scoped variable entity."""
        var_id = self._make_id(func_id, name, "local")
        if var_id not in self.entities:
            var_entity = VariableEntity(
                id=var_id,
                name=name,
                location=self._get_location(node, file_path),
                node_type="Variable",
                type_annotation=self._get_type_annotation(type_annotation),
                scope="function"
            )
            self.entities[var_id] = var_entity
            self._index_entity_name(var_entity)
        self._register_variable(var_id, name, func_id, "function")
        return var_id

    def _record_variable_assignment(self, func_id: Optional[str], var_id: str,
                                    location: str, value_type: Optional[str] = None):
        """Record assignment/write relationships and capture inferred types."""
        if func_id:
            self.relationships.append(Relationship(
                from_id=func_id,
                to_id=var_id,
                rel_type="ASSIGNS_TO",
                properties={"location": location}
            ))
            # Removed duplicate REFERENCES edge - ASSIGNS_TO is sufficient

        if value_type:
            var_entity = self.entities.get(var_id)
            if isinstance(var_entity, VariableEntity):
                if value_type not in var_entity.inferred_types:
                    var_entity.inferred_types.append(value_type)

    def _record_variable_read(self, func_id: str, var_id: str, location: str):
        """Record read access to a variable."""
        self.relationships.append(Relationship(
            from_id=func_id,
            to_id=var_id,
            rel_type="READS_FROM",
            properties={"location": location}
        ))
        # Removed duplicate REFERENCES edge - READS_FROM is sufficient

    def _handle_assignment_target(self, target: ast.AST, file_path: str, func_id: Optional[str],
                                  type_annotation: Optional[ast.AST] = None, value_type: Optional[str] = None):
        """Handle assignment targets recursively to capture variable writes."""
        if isinstance(target, ast.Name):
            var_id = self._get_or_create_local_variable(target.id, func_id, file_path, target, type_annotation)
            location = self._get_location(target, file_path)
            self._record_variable_assignment(func_id, var_id, location, value_type)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self._handle_assignment_target(elt, file_path, func_id, None, value_type)

    def _record_loads_from_node(self, node: ast.AST, file_path: str, func_id: str):
        """Traverse AST node to capture read references."""
        if node is None:
            return
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                self._handle_name_load(child, file_path, func_id)

    def _handle_name_load(self, name_node: ast.Name, file_path: str, func_id: str):
        """Handle a single name read."""
        location = self._get_location(name_node, file_path)

        # Try to resolve as a variable
        var_id = self._resolve_variable(name_node.id, func_id)
        if var_id:
            self._record_variable_read(func_id, var_id, location)
            return

        # Try to resolve as a parameter
        param_id = self._resolve_parameter(name_node.id, func_id)
        if param_id:
            self._record_reference(func_id, param_id, "read", location)
            return

        # Try to resolve as a named entity (class, function, etc.)
        target_id = self._resolve_named_entity(name_node.id)
        if target_id:
            self._record_reference(func_id, target_id, "read", location)
            return

        # Check if it's a built-in (don't create unresolved reference for these)
        if name_node.id in self.builtin_types or name_node.id in {
            'len', 'print', 'range', 'enumerate', 'zip', 'map', 'filter',
            'sum', 'max', 'min', 'abs', 'round', 'sorted', 'reversed',
            'any', 'all', 'isinstance', 'issubclass', 'hasattr', 'getattr', 'setattr',
            'open', 'input', 'type', 'id', 'hex', 'oct', 'bin', 'chr', 'ord',
            'True', 'False', 'None', 'Exception', 'ValueError', 'TypeError',
            'KeyError', 'AttributeError', 'IndexError', 'RuntimeError'
        }:
            # Don't create unresolved reference for built-ins
            return

        # Only create unresolved reference if we couldn't resolve it
        self._record_unresolved_reference(name_node.id, func_id, file_path, name_node, "read")

    def _create_decorator_entity(self, decorator_node: ast.AST, decorator_name: str,
                                 file_path: str, target_id: str, target_type: str):
        """Create decorator nodes so usage is represented in the graph."""
        location = self._get_location(decorator_node, file_path)
        decorator_id = self._make_id(target_id, decorator_name, "decorator", location)
        if decorator_id not in self.entities:
            decorator_entity = DecoratorEntity(
                id=decorator_id,
                name=decorator_name,
                location=location,
                node_type="Decorator",
                target_id=target_id,
                target_type=target_type
            )
            self.entities[decorator_id] = decorator_entity
            self._index_entity_name(decorator_entity)

        self.relationships.append(Relationship(
            from_id=target_id,
            to_id=decorator_id,
            rel_type="HAS_DECORATOR"
        ))
        self.relationships.append(Relationship(
            from_id=decorator_id,
            to_id=target_id,
            rel_type="DECORATES"
        ))

        resolved_target = self._resolve_named_entity(decorator_name)
        if resolved_target:
            self._record_reference(decorator_id, resolved_target, "call", location)

    def _ensure_import_target(self, qualified_name: str, file_path: str, lineno: int) -> str:
        """Ensure imported modules/classes exist as placeholder nodes."""
        target_id = self._make_id(qualified_name)
        if target_id not in self.entities:
            module_entity = ModuleEntity(
                id=target_id,
                name=qualified_name.split('.')[-1],
                qualified_name=qualified_name,
                path=qualified_name.replace('.', '/'),
                location=f"{file_path}:{lineno}:0",
                node_type="Module",
                is_external=True
            )
            self.entities[target_id] = module_entity
            self._index_entity_name(module_entity)
        return target_id

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

    def _contains_yield(self, node: ast.FunctionDef) -> bool:
        """Check if function contains yield statement (is a generator)."""
        for child in ast.walk(node):
            if isinstance(child, (ast.Yield, ast.YieldFrom)):
                return True
        return False

    def _visit_module(self, tree: ast.Module, file_path: str, module_id: str):
        """Visit module-level nodes."""
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                self._visit_function(node, file_path)
                # Create DECLARES relationship
                func_name = node.name
                func_qualified_name = f"{self.current_module}.{func_name}"
                func_id = self._make_id(func_qualified_name)
                self.relationships.append(Relationship(
                    from_id=module_id,
                    to_id=func_id,
                    rel_type="DECLARES"
                ))
            elif isinstance(node, ast.ClassDef):
                self._visit_class(node, file_path)
                # Create DECLARES relationship
                class_name = node.name
                class_qualified_name = f"{self.current_module}.{class_name}"
                class_id = self._make_id(class_qualified_name)
                self.relationships.append(Relationship(
                    from_id=module_id,
                    to_id=class_id,
                    rel_type="DECLARES"
                ))
            elif isinstance(node, ast.Assign) or isinstance(node, ast.AnnAssign):
                self._visit_assignment(node, file_path, scope="module")
            elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                self._visit_import(node, file_path, module_id)

    def _visit_function(self, node: ast.FunctionDef, file_path: str, class_name: Optional[str] = None):
        """Visit function definition."""
        func_name = node.name
        qualified_name = f"{self.current_module}.{class_name}.{func_name}" if class_name else f"{self.current_module}.{func_name}"

        func_id = self._make_id(qualified_name)

        # Extract decorators
        decorators = []
        is_staticmethod = False
        is_classmethod = False
        is_property = False

        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                dec_name = decorator.id
                decorators.append(dec_name)
                if dec_name == 'staticmethod':
                    is_staticmethod = True
                elif dec_name == 'classmethod':
                    is_classmethod = True
                elif dec_name == 'property':
                    is_property = True
                self._create_decorator_entity(decorator, dec_name, file_path, func_id, "Function")
            elif isinstance(decorator, ast.Attribute):
                dec_name = ast.unparse(decorator)
                decorators.append(dec_name)
                self._create_decorator_entity(decorator, dec_name, file_path, func_id, "Function")

        # Extract return type
        return_type = self._get_type_annotation(node.returns)

        # Get docstring
        docstring = ast.get_docstring(node)

        # Detect if function is a generator (contains yield)
        is_generator = self._contains_yield(node)

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
            is_generator=is_generator,
            docstring=docstring,
            is_staticmethod=is_staticmethod,
            is_classmethod=is_classmethod,
            is_property=is_property,
            decorators=decorators
        )

        # Parse parameters
        self._visit_parameters(node.args, func_id, file_path)

        self.entities[func_id] = func_entity
        self._index_entity_name(func_entity)

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

        decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                dec_name = decorator.id
            else:
                dec_name = ast.unparse(decorator)
            decorators.append(dec_name)
            self._create_decorator_entity(decorator, dec_name, file_path, class_id, "Class")

        class_entity = ClassEntity(
            id=class_id,
            name=class_name,
            qualified_name=qualified_name,
            location=self._get_location(node, file_path),
            node_type="Class",
            visibility="private" if self._is_private(class_name) else "public",
            docstring=docstring,
            bases=bases,
            decorators=decorators
        )

        self.entities[class_id] = class_entity
        self._index_entity_name(class_entity)

        # Create INHERITS relationships for base classes
        for base_name in bases:
            if base_name and base_name != "<unknown>":
                # Try to resolve the base class
                # Simple case: base is in same module
                base_qualified_name = f"{self.current_module}.{base_name}"
                base_id = self._make_id(base_qualified_name)

                self.relationships.append(Relationship(
                    from_id=class_id,
                    to_id=base_id,
                    rel_type="INHERITS",
                    properties={"base_name": base_name}
                ))

        # Visit class body
        old_class = self.current_class
        self.current_class = class_id
        for stmt in node.body:
            if isinstance(stmt, ast.FunctionDef) or isinstance(stmt, ast.AsyncFunctionDef):
                # Visit the method
                self._visit_function(stmt, file_path, class_name)

                # Create DECLARES relationship between class and method
                method_name = stmt.name
                method_qualified_name = f"{self.current_module}.{class_name}.{method_name}"
                method_id = self._make_id(method_qualified_name)

                self.relationships.append(Relationship(
                    from_id=class_id,
                    to_id=method_id,
                    rel_type="DECLARES"
                ))
            elif isinstance(stmt, ast.Assign) or isinstance(stmt, ast.AnnAssign):
                self._visit_assignment(stmt, file_path, scope="class")
        self.current_class = old_class

    def _visit_assignment(self, node: ast.AST, file_path: str, scope: str):
        """Visit assignment statements to track variables."""
        # For now, just track module-level and class-level variables
        if scope in ["module", "class"]:
            owner_id = self.current_class if scope == "class" else self.current_module_id

            def _create_scope_variable(var_node: ast.Name, annotation: Optional[ast.AST] = None,
                                       value_type: Optional[str] = None):
                var_name = var_node.id
                var_id = self._make_id(self.current_module, owner_id or "", scope, var_name)
                created = False
                if var_id not in self.entities:
                    var_entity = VariableEntity(
                        id=var_id,
                        name=var_name,
                        location=self._get_location(var_node, file_path),
                        node_type="Variable",
                        type_annotation=self._get_type_annotation(annotation),
                        scope=scope
                    )
                    self.entities[var_id] = var_entity
                    self._index_entity_name(var_entity)
                    created = True
                self._register_variable(var_id, var_name, owner_id, scope)
                if value_type:
                    var_entity = self.entities.get(var_id)
                    if isinstance(var_entity, VariableEntity) and value_type not in var_entity.inferred_types:
                        var_entity.inferred_types.append(value_type)

            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                value_type = self._infer_expression_type(node.value, None) if node.value else None
                _create_scope_variable(node.target, node.annotation, value_type)
            elif isinstance(node, ast.Assign):
                value_type = self._infer_expression_type(node.value, None)
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        _create_scope_variable(target, None, value_type)

    def _visit_statement(self, node: ast.AST, file_path: str, func_id: str):
        """Visit statements within functions to find calls and references."""
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            self._visit_call(node.value, file_path, func_id)
            self._record_loads_from_node(node.value, file_path, func_id)
        elif isinstance(node, ast.Assign):
            value_type = self._infer_expression_type(node.value, func_id)
            for value_node in ast.walk(node.value):
                if isinstance(value_node, ast.Call):
                    self._visit_call(value_node, file_path, func_id)
            for target in node.targets:
                self._handle_assignment_target(target, file_path, func_id, None, value_type)
            self._record_loads_from_node(node.value, file_path, func_id)
        elif isinstance(node, ast.AnnAssign):
            value_type = self._infer_expression_type(node.value, func_id) if node.value else None
            if isinstance(node.target, ast.Name):
                self._handle_assignment_target(node.target, file_path, func_id, node.annotation, value_type)
            if node.value:
                for value_node in ast.walk(node.value):
                    if isinstance(value_node, ast.Call):
                        self._visit_call(value_node, file_path, func_id)
                self._record_loads_from_node(node.value, file_path, func_id)
        elif isinstance(node, ast.AugAssign):
            value_type = self._infer_expression_type(node.value, func_id)
            self._handle_assignment_target(node.target, file_path, func_id, None, value_type)
            self._record_loads_from_node(node.value, file_path, func_id)
        elif isinstance(node, ast.Return) and node.value:
            for value_node in ast.walk(node.value):
                if isinstance(value_node, ast.Call):
                    self._visit_call(value_node, file_path, func_id)
            self._record_loads_from_node(node.value, file_path, func_id)
        elif isinstance(node, ast.If):
            self._record_loads_from_node(node.test, file_path, func_id)
        elif isinstance(node, ast.While):
            self._record_loads_from_node(node.test, file_path, func_id)
        elif isinstance(node, ast.Assert):
            self._record_loads_from_node(node.test, file_path, func_id)
            self._record_loads_from_node(node.msg, file_path, func_id)
        elif isinstance(node, ast.For):
            # Infer type of the iterable
            iter_type = self._infer_expression_type(node.iter, func_id)

            # Try to infer element type from the iterable
            element_type = None
            element_types = []

            # Handle tuple unpacking in for loops (e.g., for name, values in data.items())
            if isinstance(node.target, ast.Tuple):
                # Check if iterating over dict.items() or similar
                if isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Attribute):
                    method_name = node.iter.func.attr
                    if method_name == 'items':
                        # Get the type of the dict being iterated
                        dict_obj = node.iter.func.value
                        dict_type = self._infer_expression_type(dict_obj, func_id)
                        if dict_type and '[' in dict_type and dict_type.endswith(']'):
                            # Extract key and value types from Dict[K, V] or dict[K, V]
                            # Use slicing to remove exactly one closing bracket
                            types_str = dict_type.split('[', 1)[1][:-1]
                            # Simple split on comma (doesn't handle nested generics perfectly)
                            parts = [p.strip() for p in types_str.split(',', 1)]
                            if len(parts) == 2:
                                element_types = parts

                # If we have element types for tuple unpacking, assign them
                if element_types and len(element_types) == len(node.target.elts):
                    for target_elt, elt_type in zip(node.target.elts, element_types):
                        self._handle_assignment_target(target_elt, file_path, func_id, None, elt_type)
                else:
                    # Fall back to generic tuple handling
                    self._handle_assignment_target(node.target, file_path, func_id, None, iter_type)
            else:
                # Single variable (not tuple unpacking)
                if iter_type and "[" in iter_type and iter_type.endswith("]"):
                    element_type = iter_type.split("[", 1)[1].rstrip("]")
                self._handle_assignment_target(node.target, file_path, func_id, None, element_type or iter_type)

            self._record_loads_from_node(node.iter, file_path, func_id)
        elif isinstance(node, ast.With):
            for item in node.items:
                result_type = self._infer_expression_type(item.context_expr, func_id)
                if item.optional_vars:
                    self._handle_assignment_target(item.optional_vars, file_path, func_id, None, result_type)
                self._record_loads_from_node(item.context_expr, file_path, func_id)

        # Recursively visit nested statements
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                for stmt in getattr(child, 'body', []):
                    self._visit_statement(stmt, file_path, func_id)
                for stmt in getattr(child, 'orelse', []):
                    self._visit_statement(stmt, file_path, func_id)

    def _visit_call(self, node: ast.Call, file_path: str, caller_id: str):
        """Visit function call to create CallSite node and relationships."""
        # Try to extract callee name
        callee_name = None
        if isinstance(node.func, ast.Name):
            callee_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            callee_name = ast.unparse(node.func)

        if callee_name:
            # Count arguments and detect *args/**kwargs
            arg_count = len(node.args)
            has_args = any(isinstance(arg, ast.Starred) for arg in node.args)
            has_kwargs = len(node.keywords) > 0
            arg_types = []
            for arg in node.args:
                inferred = self._infer_expression_type(arg, caller_id)
                arg_types.append(inferred or "")

            # Create CallSite entity
            location = self._get_location(node, file_path)
            callsite_id = self._make_id(caller_id, callee_name, str(node.lineno), str(node.col_offset))

            callsite_entity = CallSiteEntity(
                id=callsite_id,
                name=f"call_{callee_name}@{node.lineno}",
                location=location,
                node_type="CallSite",
                caller_id=caller_id,
                arg_count=arg_count,
                has_args=has_args,
                has_kwargs=has_kwargs,
                lineno=node.lineno,
                col_offset=node.col_offset,
                arg_types=arg_types
            )
            self.entities[callsite_id] = callsite_entity

            # Create relationships: Function -> CallSite -> Function
            # Caller HAS_CALLSITE CallSite
            self.relationships.append(Relationship(
                from_id=caller_id,
                to_id=callsite_id,
                rel_type="HAS_CALLSITE"
            ))

            # CallSite with CALLS_UNRESOLVED - will be resolved to RESOLVES_TO by builder
            self.relationships.append(Relationship(
                from_id=callsite_id,
                to_id=f"unresolved:{callee_name}",
                rel_type="CALLS_UNRESOLVED",
                properties={
                    "callee_name": callee_name,
                    "resolution_status": "pending"
                }
            ))

    def _visit_import(self, node: ast.AST, file_path: str, module_id: str):
        """Visit import statements."""
        if isinstance(node, ast.Import):
            # import x, y, z
            for alias in node.names:
                imported_module = alias.name
                target_id = self._ensure_import_target(imported_module, file_path, getattr(node, 'lineno', 0))
                self.relationships.append(Relationship(
                    from_id=module_id,
                    to_id=target_id,
                    rel_type="IMPORTS",
                    properties={
                        "import_name": imported_module,
                        "alias": alias.asname if alias.asname else None
                    }
                ))

        elif isinstance(node, ast.ImportFrom):
            # from x import y, z
            base_module = node.module if node.module else ""
            for alias in node.names:
                imported_name = alias.name
                if imported_name == "*":
                    qualified = base_module
                else:
                    qualified = f"{base_module}.{imported_name}" if base_module else imported_name

                target_id = self._ensure_import_target(qualified, file_path, getattr(node, 'lineno', 0))

                self.relationships.append(Relationship(
                    from_id=module_id,
                    to_id=target_id,
                    rel_type="IMPORTS",
                    properties={
                        "from_module": base_module,
                        "import_name": imported_name,
                        "alias": alias.asname if alias.asname else None
                    }
                ))

    def _initialize_builtin_types(self):
        """Reset builtin type cache for each parse."""
        self.builtin_types = {
            "str": "builtin",
            "int": "builtin",
            "float": "builtin",
            "bool": "builtin",
            "list": "builtin",
            "dict": "builtin",
            "set": "builtin",
            "tuple": "builtin",
            "bytes": "builtin",
            "bytearray": "builtin",
            "complex": "builtin",
            "range": "builtin",
            "None": "builtin",
            "NoneType": "builtin",
        }

    def _get_or_create_type(self, type_str: str, context_module: str = "builtins") -> str:
        """
        Get or create a Type entity from a type annotation string.

        Args:
            type_str: Type annotation string (e.g., "str", "List[int]", "Optional[MyClass]")
            context_module: Module context for resolving custom types

        Returns:
            Type entity ID
        """
        if not type_str:
            return ""

        # Clean up type string
        type_str = type_str.strip()

        # Check if it's already in registry
        if type_str in self.type_registry:
            return self.type_registry[type_str]

        # Parse generic types (e.g., List[int], Dict[str, int])
        if "[" in type_str:
            # Extract base type (e.g., "List" from "List[int]")
            base_type = type_str.split("[")[0].strip()

            # Create generic type entity
            type_id = self._make_id(context_module, type_str)
            type_entity = TypeEntity(
                id=type_id,
                name=type_str,
                location=context_module,
                node_type="Type",
                module=context_module,
                kind="generic"
            )
            self.entities[type_id] = type_entity
            self.type_registry[type_str] = type_id

            # Link to base type if it exists
            if base_type in self.type_registry:
                base_id = self.type_registry[base_type]
                self.relationships.append(Relationship(
                    from_id=type_id,
                    to_id=base_id,
                    rel_type="IS_SUBTYPE_OF"
                ))

            return type_id

        # Handle Union types (e.g., "Union[int, str]", "int | str")
        if "Union[" in type_str or "|" in type_str:
            type_id = self._make_id(context_module, type_str)
            type_entity = TypeEntity(
                id=type_id,
                name=type_str,
                location=context_module,
                node_type="Type",
                module=context_module,
                kind="union"
            )
            self.entities[type_id] = type_entity
            self.type_registry[type_str] = type_id
            return type_id

        # Handle Optional (shorthand for Union[T, None])
        if "Optional[" in type_str:
            type_id = self._make_id(context_module, type_str)
            type_entity = TypeEntity(
                id=type_id,
                name=type_str,
                location=context_module,
                node_type="Type",
                module=context_module,
                kind="union"
            )
            self.entities[type_id] = type_entity
            self.type_registry[type_str] = type_id
            return type_id

        # Builtin or custom class type
        module_name = "builtins" if type_str in self.builtin_types else context_module
        type_id = self._make_id(module_name, type_str)
        type_entity = TypeEntity(
            id=type_id,
            name=type_str,
            location=module_name,
            node_type="Type",
            module=module_name,
            kind="builtin" if module_name == "builtins" else "class"
        )
        self.entities[type_id] = type_entity
        self.type_registry[type_str] = type_id

        return type_id

    def _create_type_relationships(self):
        """Create HAS_TYPE and RETURNS_TYPE relationships after parsing."""
        # Link functions to return types
        for entity_id, entity in list(self.entities.items()):
            if isinstance(entity, FunctionEntity) and entity.return_type:
                return_type_id = self._get_or_create_type(
                    entity.return_type,
                    self.current_module
                )
                if return_type_id:
                    self.relationships.append(Relationship(
                        from_id=entity_id,
                        to_id=return_type_id,
                        rel_type="RETURNS_TYPE"
                    ))

            # Link parameters to types
            if isinstance(entity, ParameterEntity) and entity.type_annotation:
                param_type_id = self._get_or_create_type(
                    entity.type_annotation,
                    self.current_module
                )
                if param_type_id:
                    self.relationships.append(Relationship(
                        from_id=entity_id,
                        to_id=param_type_id,
                        rel_type="HAS_TYPE"
                    ))

            # Link variables to types
            if isinstance(entity, VariableEntity) and entity.type_annotation:
                var_type_id = self._get_or_create_type(
                    entity.type_annotation,
                    self.current_module
                )
                if var_type_id:
                    self.relationships.append(Relationship(
                        from_id=entity_id,
                        to_id=var_type_id,
                        rel_type="HAS_TYPE"
                    ))
            if isinstance(entity, VariableEntity) and entity.inferred_types:
                seen_inferred: set[str] = set()
                for inferred in entity.inferred_types:
                    if not inferred or inferred in seen_inferred:
                        continue
                    seen_inferred.add(inferred)
                    inferred_id = self._get_or_create_type(
                        inferred,
                        self.current_module
                    )
                    if inferred_id:
                        self.relationships.append(Relationship(
                            from_id=entity_id,
                            to_id=inferred_id,
                            rel_type="ASSIGNED_TYPE"
                        ))

            # Link classes to their type representations
            # Each class IS a type
            if isinstance(entity, ClassEntity):
                # The class itself becomes a Type
                type_id = self._make_id(self.current_module, entity.name + "_type")
                type_entity = TypeEntity(
                    id=type_id,
                    name=entity.name,
                    location=entity.location,
                    node_type="Type",
                    module=self.current_module,
                    kind="class",
                    base_types=entity.bases
                )
                self.entities[type_id] = type_entity
                self.type_registry[entity.name] = type_id

                # Create IS_SUBTYPE_OF relationships for base classes
                for base_name in entity.bases:
                    if base_name and base_name != "<unknown>":
                        base_type_id = self._get_or_create_type(base_name, self.current_module)
                        if base_type_id:
                            self.relationships.append(Relationship(
                                from_id=type_id,
                                to_id=base_type_id,
                                rel_type="IS_SUBTYPE_OF"
                            ))
