"""Setup script for CodeGraph Backend."""

from setuptools import setup, find_packages
import os

# Read README if it exists
readme_path = os.path.join(os.path.dirname(__file__), "README.md")
long_description = ""
if os.path.exists(readme_path):
    with open(readme_path, "r", encoding="utf-8") as fh:
        long_description = fh.read()

setup(
    name="codegraph-backend",
    version="0.1.0",
    author="CodeGraph Team",
    description="Backend API for CodeGraph - A graph database for Python codebases with conservation laws",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/codegraph",
    packages=find_packages(include=["codegraph", "codegraph.*", "app", "app.*"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "fastapi>=0.104.1",
        "uvicorn[standard]>=0.24.0",
        "pydantic>=2.5.0",
        "pydantic-settings>=2.0.0",
        "python-multipart>=0.0.6",
        "neo4j>=5.14.0",
        "python-dotenv>=1.0.0",
        "click>=8.1.7",
        "rich>=13.7.0",
    ],
    entry_points={
        "console_scripts": [
            "codegraph-api=run:main",  # Run the API server
            "codegraph-cli=codegraph.cli:main",  # CLI tool (optional)
        ],
    },
)
