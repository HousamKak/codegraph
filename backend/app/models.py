"""Pydantic models for API requests and responses."""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum


class NodeType(str, Enum):
    """Graph node types."""
    FUNCTION = "Function"
    CLASS = "Class"
    VARIABLE = "Variable"
    PARAMETER = "Parameter"
    MODULE = "Module"
    TYPE = "Type"


class ChangeType(str, Enum):
    """Types of code changes."""
    MODIFY = "modify"
    DELETE = "delete"
    RENAME = "rename"


class ViolationSeverity(str, Enum):
    """Violation severity levels."""
    ERROR = "error"
    WARNING = "warning"


# Request Models

class IndexRequest(BaseModel):
    """Request to index a codebase."""
    path: str = Field(..., description="Path to Python file or directory")
    clear: bool = Field(False, description="Clear database before indexing")


class SearchRequest(BaseModel):
    """Request to search for entities."""
    pattern: str = Field(..., description="Search pattern")
    entity_type: Optional[NodeType] = Field(None, description="Filter by entity type")


class ImpactAnalysisRequest(BaseModel):
    """Request for impact analysis."""
    entity_id: str = Field(..., description="Entity ID to analyze")
    change_type: ChangeType = Field(ChangeType.MODIFY, description="Type of change")


class CypherQueryRequest(BaseModel):
    """Request to execute a Cypher query."""
    query: str = Field(..., description="Cypher query string")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Query parameters")


class ValidateChangeRequest(BaseModel):
    """Request to validate a proposed change."""
    entity_id: str = Field(..., description="Entity ID to change")
    change_type: ChangeType = Field(..., description="Type of change")
    new_properties: Optional[Dict[str, Any]] = Field(None, description="New properties")


# Response Models

class NodeResponse(BaseModel):
    """Graph node response."""
    id: str
    labels: List[str]
    properties: Dict[str, Any]


class EdgeResponse(BaseModel):
    """Graph edge response."""
    source: str
    target: str
    type: str
    properties: Dict[str, Any] = {}


class GraphResponse(BaseModel):
    """Complete graph response for visualization."""
    nodes: List[NodeResponse]
    edges: List[EdgeResponse]


class FunctionResponse(BaseModel):
    """Function details response."""
    id: str
    name: str
    qualified_name: str
    signature: str
    return_type: Optional[str] = None
    visibility: str
    is_async: bool
    location: str
    docstring: Optional[str] = None


class ParameterResponse(BaseModel):
    """Parameter details response."""
    id: str
    name: str
    type_annotation: Optional[str] = None
    position: int
    kind: str
    default_value: Optional[str] = None


class FunctionSignatureResponse(BaseModel):
    """Function signature with parameters."""
    function: FunctionResponse
    parameters: List[ParameterResponse]


class CallerResponse(BaseModel):
    """Function caller information."""
    caller: FunctionResponse
    arg_count: Optional[int] = None
    location: Optional[str] = None


class CalleeResponse(BaseModel):
    """Function callee information."""
    callee: FunctionResponse
    arg_count: Optional[int] = None
    location: Optional[str] = None


class DependencyResponse(BaseModel):
    """Function dependency information."""
    function: FunctionResponse
    distance: int


class DependenciesResponse(BaseModel):
    """Complete dependency information."""
    inbound: List[DependencyResponse]
    outbound: List[DependencyResponse]


class ImpactAnalysisResponse(BaseModel):
    """Impact analysis results."""
    entity_id: str
    change_type: str
    affected_callers: List[Dict[str, Any]]
    affected_references: List[Dict[str, Any]]
    cascading_changes: List[Dict[str, Any]]


class ViolationResponse(BaseModel):
    """Conservation law violation."""
    violation_type: str
    severity: ViolationSeverity
    entity_id: str
    message: str
    details: Dict[str, Any]
    suggested_fix: Optional[str] = None


class ValidationReportResponse(BaseModel):
    """Validation report."""
    total_violations: int
    errors: int
    warnings: int
    by_type: Dict[str, int]
    summary: Dict[str, int]
    violations: List[ViolationResponse]


class StatisticsResponse(BaseModel):
    """Database statistics."""
    stats: Dict[str, int]


class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    details: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    database_connected: bool
    neo4j_uri: str
