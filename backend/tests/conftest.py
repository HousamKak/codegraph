"""Shared pytest configuration and fixtures."""

import pytest
import os
import tempfile
from pathlib import Path
from typing import Generator

from codegraph import CodeGraphDB, PythonParser, GraphBuilder


@pytest.fixture(scope="session")
def neo4j_test_db() -> Generator[CodeGraphDB, None, None]:
    """Provides a Neo4j test database instance for the entire test session."""
    db = CodeGraphDB(
        uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        user=os.getenv("NEO4J_USER", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "password")
    )
    yield db
    db.close()


@pytest.fixture(scope="function")
def clean_db(neo4j_test_db: CodeGraphDB) -> Generator[CodeGraphDB, None, None]:
    """Provides a clean database for each test function."""
    # Clear all data
    neo4j_test_db.clear_database()
    # Initialize schema
    neo4j_test_db.initialize_schema()
    yield neo4j_test_db
    # Cleanup after test
    neo4j_test_db.clear_database()


@pytest.fixture
def parser() -> PythonParser:
    """Provides a Python parser instance."""
    return PythonParser()


@pytest.fixture
def builder(clean_db: CodeGraphDB) -> GraphBuilder:
    """Provides a graph builder with clean database."""
    return GraphBuilder(clean_db)


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Provides a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_file(temp_dir: Path) -> Path:
    """Provides a temporary file path."""
    return temp_dir / "test_file.py"


@pytest.fixture
def sample_python_code() -> str:
    """Returns sample Python code for testing."""
    return '''
"""Sample module for testing."""

def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

def multiply(x: int, y: int) -> int:
    """Multiply two numbers."""
    return x * y

class Calculator:
    """A simple calculator class."""

    def __init__(self):
        self.result = 0

    def calculate(self, a: int, b: int) -> int:
        """Calculate sum using add function."""
        return add(a, b)
'''


@pytest.fixture
def sample_class_code() -> str:
    """Returns sample Python class code."""
    return '''
class BaseClass:
    """A base class."""
    pass

class DerivedClass(BaseClass):
    """A derived class."""

    def method_one(self) -> None:
        """First method."""
        pass

    def method_two(self, value: int) -> str:
        """Second method."""
        return str(value)
'''


@pytest.fixture
def sample_import_code() -> str:
    """Returns sample code with imports."""
    return '''
import os
import sys
from typing import List, Optional
from pathlib import Path

def process_files(paths: List[Path]) -> Optional[str]:
    """Process a list of file paths."""
    if not paths:
        return None
    return str(paths[0])
'''


@pytest.fixture
def sample_complex_code() -> str:
    """Returns complex Python code with multiple patterns."""
    return '''
"""Complex module with various patterns."""

from typing import List, Dict, Optional
import json

class DataProcessor:
    """Process data with multiple methods."""

    def __init__(self, config: Dict):
        self.config = config

    def load_data(self, filename: str) -> Optional[Dict]:
        """Load data from file."""
        try:
            with open(filename) as f:
                return json.load(f)
        except FileNotFoundError:
            return None

    def process(self, data: List[Dict]) -> List[Dict]:
        """Process list of data items."""
        return [self._transform(item) for item in data]

    def _transform(self, item: Dict) -> Dict:
        """Transform a single item."""
        return {**item, "processed": True}

def main():
    """Main entry point."""
    processor = DataProcessor({"mode": "strict"})
    data = processor.load_data("data.json")
    if data:
        results = processor.process([data])
        print(results)

if __name__ == "__main__":
    main()
'''


@pytest.fixture
def write_temp_file(temp_file: Path):
    """Factory fixture to write content to temp file."""
    def _write(content: str) -> Path:
        temp_file.write_text(content)
        return temp_file
    return _write
