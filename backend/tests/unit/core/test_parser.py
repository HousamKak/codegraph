"""Unit tests for PythonParser."""

import pytest
from pathlib import Path
from codegraph.parser import (
    PythonParser,
    FunctionEntity,
    ClassEntity,
    ModuleEntity,
    VariableEntity,
    CallSiteEntity,
    ParameterEntity,
    Relationship
)


@pytest.mark.unit
class TestPythonParserBasics:
    """Basic parsing tests for Python parser."""

    def test_parse_empty_file(self, parser, temp_file):
        """Test parsing an empty file."""
        temp_file.write_text("")
        entities, relationships = parser.parse_file(str(temp_file))

        # Should still create a module entity
        assert len(entities) == 1
        module_entities = [e for e in entities.values() if e.node_type == "Module"]
        assert len(module_entities) == 1

    def test_parse_simple_function(self, parser, temp_file):
        """Test parsing a simple function."""
        code = '''
def hello():
    """Say hello."""
    print("Hello, World!")
'''
        temp_file.write_text(code)
        entities, relationships = parser.parse_file(str(temp_file))

        functions = [e for e in entities.values() if e.node_type == "Function"]
        assert len(functions) == 1

        func = functions[0]
        assert func.name == "hello"
        assert func.docstring == "Say hello."

    def test_parse_function_with_parameters(self, parser, temp_file):
        """Test parsing a function with parameters."""
        code = '''
def greet(name, age):
    """Greet a person."""
    return f"Hello {name}, you are {age}"
'''
        temp_file.write_text(code)
        entities, relationships = parser.parse_file(str(temp_file))

        functions = [e for e in entities.values() if e.node_type == "Function"]
        assert len(functions) == 1

        func = functions[0]
        assert func.name == "greet"
        assert len(func.parameters) == 2
        assert func.parameters[0].name == "name"
        assert func.parameters[1].name == "age"

    def test_parse_function_with_type_annotations(self, parser, temp_file):
        """Test parsing a function with type annotations."""
        code = '''
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b
'''
        temp_file.write_text(code)
        entities, relationships = parser.parse_file(str(temp_file))

        functions = [e for e in entities.values() if e.node_type == "Function"]
        assert len(functions) == 1

        func = functions[0]
        assert func.name == "add"
        assert func.return_type is not None
        assert len(func.parameters) == 2
        assert func.parameters[0].type_annotation is not None
        assert func.parameters[1].type_annotation is not None

    def test_parse_async_function(self, parser, temp_file):
        """Test parsing async function."""
        code = '''
async def fetch_data():
    """Fetch data asynchronously."""
    return await some_async_call()
'''
        temp_file.write_text(code)
        entities, relationships = parser.parse_file(str(temp_file))

        functions = [e for e in entities.values() if e.node_type == "Function"]
        assert len(functions) == 1
        assert functions[0].is_async is True

    def test_parse_function_with_decorators(self, parser, temp_file):
        """Test parsing function with decorators."""
        code = '''
@property
@classmethod
def get_value(cls):
    """Get value."""
    return cls.value
'''
        temp_file.write_text(code)
        entities, relationships = parser.parse_file(str(temp_file))

        functions = [e for e in entities.values() if e.node_type == "Function"]
        assert len(functions) == 1
        assert len(functions[0].decorators) >= 1


@pytest.mark.unit
class TestClassParsing:
    """Tests for class parsing."""

    def test_parse_simple_class(self, parser, temp_file):
        """Test parsing a simple class."""
        code = '''
class MyClass:
    """A simple class."""
    pass
'''
        temp_file.write_text(code)
        entities, relationships = parser.parse_file(str(temp_file))

        classes = [e for e in entities.values() if e.node_type == "Class"]
        assert len(classes) == 1
        assert classes[0].name == "MyClass"
        assert classes[0].docstring == "A simple class."

    def test_parse_class_with_inheritance(self, parser, temp_file):
        """Test parsing class with inheritance."""
        code = '''
class BaseClass:
    """Base class."""
    pass

class DerivedClass(BaseClass):
    """Derived class."""
    pass
'''
        temp_file.write_text(code)
        entities, relationships = parser.parse_file(str(temp_file))

        classes = [e for e in entities.values() if e.node_type == "Class"]
        assert len(classes) == 2

        derived = [c for c in classes if c.name == "DerivedClass"][0]
        assert len(derived.bases) >= 1

    def test_parse_class_with_methods(self, parser, temp_file):
        """Test parsing class with methods."""
        code = '''
class Calculator:
    """Calculator class."""

    def add(self, a, b):
        """Add two numbers."""
        return a + b

    def subtract(self, a, b):
        """Subtract two numbers."""
        return a - b
'''
        temp_file.write_text(code)
        entities, relationships = parser.parse_file(str(temp_file))

        functions = [e for e in entities.values() if e.node_type == "Function"]
        assert len(functions) >= 2

        method_names = [f.name for f in functions]
        assert "add" in method_names
        assert "subtract" in method_names


@pytest.mark.unit
class TestImportParsing:
    """Tests for import statement parsing."""

    def test_parse_simple_import(self, parser, temp_file):
        """Test parsing simple import."""
        code = '''
import os
import sys
'''
        temp_file.write_text(code)
        entities, relationships = parser.parse_file(str(temp_file))

        # Should have Import relationships
        import_rels = [r for r in relationships if r.rel_type == "IMPORTS"]
        assert len(import_rels) >= 1

    def test_parse_from_import(self, parser, temp_file):
        """Test parsing from import."""
        code = '''
from typing import List, Dict
from pathlib import Path
'''
        temp_file.write_text(code)
        entities, relationships = parser.parse_file(str(temp_file))

        import_rels = [r for r in relationships if r.rel_type == "IMPORTS"]
        assert len(import_rels) >= 1

    def test_parse_import_with_alias(self, parser, temp_file):
        """Test parsing import with alias."""
        code = '''
import numpy as np
from typing import List as ListType
'''
        temp_file.write_text(code)
        entities, relationships = parser.parse_file(str(temp_file))

        # Should parse successfully
        assert len(entities) >= 1


@pytest.mark.unit
class TestRelationshipExtraction:
    """Tests for relationship extraction."""

    def test_extract_function_calls(self, parser, temp_file):
        """Test extracting function call relationships."""
        code = '''
def helper():
    """Helper function."""
    return 42

def main():
    """Main function."""
    result = helper()
    return result
'''
        temp_file.write_text(code)
        entities, relationships = parser.parse_file(str(temp_file))

        # Should have HAS_CALLSITE and RESOLVES_TO relationships
        has_callsite_rels = [r for r in relationships if r.rel_type == "HAS_CALLSITE"]
        assert len(has_callsite_rels) >= 1

    def test_extract_class_instantiation(self, parser, temp_file):
        """Test extracting class instantiation."""
        code = '''
class MyClass:
    """A class."""
    pass

def create_instance():
    """Create an instance."""
    obj = MyClass()
    return obj
'''
        temp_file.write_text(code)
        entities, relationships = parser.parse_file(str(temp_file))

        # Should have callsite for class instantiation
        callsites = [e for e in entities.values() if e.node_type == "CallSite"]
        assert len(callsites) >= 1

    def test_extract_inheritance_relationships(self, parser, temp_file):
        """Test extracting inheritance relationships."""
        code = '''
class Base:
    """Base class."""
    pass

class Derived(Base):
    """Derived class."""
    pass
'''
        temp_file.write_text(code)
        entities, relationships = parser.parse_file(str(temp_file))

        # Should have INHERITS relationship
        inherits_rels = [r for r in relationships if r.rel_type == "INHERITS"]
        assert len(inherits_rels) >= 1


@pytest.mark.unit
class TestTypeExtraction:
    """Tests for type extraction."""

    def test_extract_parameter_types(self, parser, temp_file):
        """Test extracting parameter types."""
        code = '''
def process(data: list, count: int) -> str:
    """Process data."""
    return str(len(data) * count)
'''
        temp_file.write_text(code)
        entities, relationships = parser.parse_file(str(temp_file))

        functions = [e for e in entities.values() if e.node_type == "Function"]
        assert len(functions) == 1

        func = functions[0]
        assert len(func.parameters) == 2
        assert all(p.type_annotation is not None for p in func.parameters)

    def test_extract_return_types(self, parser, temp_file):
        """Test extracting return types."""
        code = '''
def get_number() -> int:
    """Get a number."""
    return 42
'''
        temp_file.write_text(code)
        entities, relationships = parser.parse_file(str(temp_file))

        functions = [e for e in entities.values() if e.node_type == "Function"]
        assert len(functions) == 1
        assert functions[0].return_type is not None

    def test_extract_optional_types(self, parser, temp_file):
        """Test extracting Optional types."""
        code = '''
from typing import Optional

def maybe_value(flag: bool) -> Optional[int]:
    """Return optional value."""
    return 42 if flag else None
'''
        temp_file.write_text(code)
        entities, relationships = parser.parse_file(str(temp_file))

        functions = [e for e in entities.values() if e.node_type == "Function"]
        assert len(functions) == 1
        assert functions[0].return_type is not None


@pytest.mark.unit
class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_parse_syntax_error_file(self, parser, temp_file):
        """Test parsing file with syntax errors."""
        code = '''
def broken_function(
    # Missing closing parenthesis
    return 42
'''
        temp_file.write_text(code)
        entities, relationships = parser.parse_file(str(temp_file))

        # Should handle gracefully and return empty or minimal results
        assert isinstance(entities, dict)
        assert isinstance(relationships, list)

    def test_parse_deeply_nested_code(self, parser, temp_file):
        """Test parsing deeply nested code."""
        code = '''
class A:
    """Class A."""
    class B:
        """Class B."""
        class C:
            """Class C."""
            def method(self):
                """Nested method."""
                def inner():
                    """Inner function."""
                    pass
                return inner
'''
        temp_file.write_text(code)
        entities, relationships = parser.parse_file(str(temp_file))

        # Should parse all nested structures
        classes = [e for e in entities.values() if e.node_type == "Class"]
        assert len(classes) >= 1

        functions = [e for e in entities.values() if e.node_type == "Function"]
        assert len(functions) >= 1

    def test_line_number_tracking(self, parser, temp_file):
        """Test that line numbers are tracked correctly."""
        code = '''
def first():
    """First function."""
    pass

def second():
    """Second function."""
    pass
'''
        temp_file.write_text(code)
        entities, relationships = parser.parse_file(str(temp_file))

        functions = [e for e in entities.values() if e.node_type == "Function"]
        assert len(functions) == 2

        # All entities should have location
        for func in functions:
            assert func.location is not None


@pytest.mark.unit
class TestParseSource:
    """Tests for parse_source method."""

    def test_parse_source_string(self, parser):
        """Test parsing source code from string."""
        code = '''
def example():
    """Example function."""
    return "test"
'''
        entities, relationships = parser.parse_source(code, "/virtual/test.py")

        assert len(entities) >= 1
        functions = [e for e in entities.values() if e.node_type == "Function"]
        assert len(functions) == 1
        assert functions[0].name == "example"


@pytest.mark.unit
class TestComplexScenarios:
    """Tests for complex real-world scenarios."""

    def test_parse_complex_module(self, parser, sample_complex_code, temp_file):
        """Test parsing complex module with multiple patterns."""
        temp_file.write_text(sample_complex_code)
        entities, relationships = parser.parse_file(str(temp_file))

        # Should have module, class, methods, and main function
        modules = [e for e in entities.values() if e.node_type == "Module"]
        classes = [e for e in entities.values() if e.node_type == "Class"]
        functions = [e for e in entities.values() if e.node_type == "Function"]

        assert len(modules) >= 1
        assert len(classes) >= 1
        assert len(functions) >= 3  # load_data, process, _transform, main

    def test_parse_with_imports_and_types(self, parser, sample_import_code, temp_file):
        """Test parsing code with imports and type annotations."""
        temp_file.write_text(sample_import_code)
        entities, relationships = parser.parse_file(str(temp_file))

        # Should have imports and typed function
        import_rels = [r for r in relationships if r.rel_type == "IMPORTS"]
        functions = [e for e in entities.values() if e.node_type == "Function"]

        assert len(import_rels) >= 1
        assert len(functions) >= 1

    def test_callsite_metadata(self, parser, temp_file):
        """Test that CallSite entities have proper metadata."""
        code = '''
def add(a, b):
    """Add numbers."""
    return a + b

def main():
    """Main."""
    result = add(5, 3)
    return result
'''
        temp_file.write_text(code)
        entities, relationships = parser.parse_file(str(temp_file))

        callsites = [e for e in entities.values() if e.node_type == "CallSite"]
        assert len(callsites) >= 1

        # Check callsite has required properties
        callsite = callsites[0]
        assert hasattr(callsite, 'arg_count')
        assert hasattr(callsite, 'location')
        assert callsite.arg_count >= 0

    def test_declares_relationships(self, parser, temp_file):
        """Test that DECLARES relationships are created."""
        code = '''
class MyClass:
    """A class."""

    def method(self):
        """A method."""
        pass

def function():
    """A function."""
    pass
'''
        temp_file.write_text(code)
        entities, relationships = parser.parse_file(str(temp_file))

        # Should have DECLARES relationships
        declares_rels = [r for r in relationships if r.rel_type == "DECLARES"]
        assert len(declares_rels) >= 1


@pytest.mark.unit
class TestParseDirectory:
    """Tests for directory parsing."""

    def test_parse_directory(self, parser, temp_dir):
        """Test parsing a directory of Python files."""
        # Create multiple test files
        (temp_dir / "file1.py").write_text("def func1(): pass")
        (temp_dir / "file2.py").write_text("def func2(): pass")
        (temp_dir / "subdir").mkdir()
        (temp_dir / "subdir" / "file3.py").write_text("def func3(): pass")

        entities, relationships = parser.parse_directory(str(temp_dir))

        # Should parse all files
        functions = [e for e in entities.values() if e.node_type == "Function"]
        assert len(functions) >= 3

    def test_parse_directory_skips_venv(self, parser, temp_dir):
        """Test that parsing skips venv directories."""
        # Create venv directory
        venv_dir = temp_dir / "venv"
        venv_dir.mkdir()
        (venv_dir / "test.py").write_text("def should_skip(): pass")

        # Create normal file
        (temp_dir / "normal.py").write_text("def normal_func(): pass")

        entities, relationships = parser.parse_directory(str(temp_dir))

        # Should only parse normal file
        functions = [e for e in entities.values() if e.node_type == "Function"]
        function_names = [f.name for f in functions]
        assert "normal_func" in function_names
        assert "should_skip" not in function_names
