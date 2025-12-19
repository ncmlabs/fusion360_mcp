"""Custom exception hierarchy for Fusion 360 MCP.

All errors are designed to be actionable - they tell the AI how to fix the problem.
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field


@dataclass
class ErrorContext:
    """Structured context for errors."""
    requested_id: Optional[str] = None
    available_entities: Optional[List[str]] = None
    valid_range: Optional[Dict[str, float]] = None
    current_value: Optional[Any] = None
    affected_entities: Optional[List[str]] = None
    additional_info: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        result = {}
        if self.requested_id is not None:
            result["requested_id"] = self.requested_id
        if self.available_entities is not None:
            result["available_entities"] = self.available_entities
        if self.valid_range is not None:
            result["valid_range"] = self.valid_range
        if self.current_value is not None:
            result["current_value"] = self.current_value
        if self.affected_entities is not None:
            result["affected_entities"] = self.affected_entities
        if self.additional_info is not None:
            result.update(self.additional_info)
        return result


@dataclass
class ErrorDetail:
    """Detailed error information."""
    type: str
    message: str
    suggestion: str
    context: Optional[ErrorContext] = None
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "type": self.type,
            "message": self.message,
            "suggestion": self.suggestion,
        }
        if self.context:
            ctx = self.context.to_dict()
            if ctx:
                result["context"] = ctx
        if self.correlation_id:
            result["correlation_id"] = self.correlation_id
        return result


@dataclass
class ErrorResponse:
    """Structured error response format."""
    success: bool = False
    error: Optional[ErrorDetail] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {"success": self.success}
        if self.error:
            result["error"] = self.error.to_dict()
        return result


class FusionMCPError(Exception):
    """Base exception for all Fusion MCP errors."""

    error_type: str = "FusionMCPError"
    default_suggestion: str = "Check the operation parameters and try again."

    def __init__(
        self,
        message: str,
        context: Optional[ErrorContext] = None,
        suggestion: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.context = context or ErrorContext()
        self.suggestion = suggestion or self.default_suggestion
        self.correlation_id = correlation_id

    def to_response(self) -> ErrorResponse:
        """Convert exception to structured error response."""
        return ErrorResponse(
            success=False,
            error=ErrorDetail(
                type=self.error_type,
                message=self.message,
                context=self.context,
                suggestion=self.suggestion,
                correlation_id=self.correlation_id,
            )
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return self.to_response().to_dict()


class EntityNotFoundError(FusionMCPError):
    """Raised when a referenced entity does not exist."""

    error_type = "EntityNotFound"
    default_suggestion = "Use get_bodies() or get_sketches() to see available entities."

    def __init__(
        self,
        entity_type: str,
        entity_id: str,
        available_entities: Optional[List[str]] = None,
        **kwargs,
    ):
        message = f"{entity_type} '{entity_id}' does not exist"
        context = ErrorContext(
            requested_id=entity_id,
            available_entities=available_entities or [],
        )
        super().__init__(message, context=context, **kwargs)


class InvalidParameterError(FusionMCPError):
    """Raised when a parameter value is invalid."""

    error_type = "InvalidParameter"
    default_suggestion = "Adjust the parameter value to be within the valid range."

    def __init__(
        self,
        parameter_name: str,
        value: Any,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        valid_values: Optional[List[Any]] = None,
        reason: Optional[str] = None,
        **kwargs,
    ):
        if reason:
            message = f"Invalid value for '{parameter_name}': {reason}"
        elif valid_values:
            message = f"Invalid value '{value}' for '{parameter_name}'. Valid values: {valid_values}"
        elif min_value is not None and max_value is not None:
            message = f"Value {value} for '{parameter_name}' must be between {min_value} and {max_value}"
        elif min_value is not None:
            message = f"Value {value} for '{parameter_name}' must be >= {min_value}"
        elif max_value is not None:
            message = f"Value {value} for '{parameter_name}' must be <= {max_value}"
        else:
            message = f"Invalid value '{value}' for parameter '{parameter_name}'"

        context = ErrorContext(
            current_value=value,
            valid_range={"min": min_value, "max": max_value} if min_value is not None or max_value is not None else None,
        )
        if valid_values:
            context.additional_info = {"valid_values": valid_values}

        super().__init__(message, context=context, **kwargs)


class GeometryError(FusionMCPError):
    """Raised when a geometry operation fails or would create invalid geometry."""

    error_type = "GeometryError"
    default_suggestion = "Check the geometry inputs. Ensure profiles are closed and don't self-intersect."

    def __init__(
        self,
        operation: str,
        reason: str,
        affected_entities: Optional[List[str]] = None,
        **kwargs,
    ):
        message = f"Geometry error during {operation}: {reason}"
        context = ErrorContext(affected_entities=affected_entities)
        super().__init__(message, context=context, **kwargs)


class ConstraintError(FusionMCPError):
    """Raised when sketch constraint operations fail."""

    error_type = "ConstraintError"
    default_suggestion = "Check constraint compatibility. Use get_sketches() to see current constraint state."

    def __init__(
        self,
        sketch_id: str,
        issue: str,
        under_constrained: Optional[List[str]] = None,
        over_constrained: Optional[List[str]] = None,
        **kwargs,
    ):
        message = f"Constraint error in sketch '{sketch_id}': {issue}"
        context = ErrorContext(
            requested_id=sketch_id,
            additional_info={
                "under_constrained": under_constrained or [],
                "over_constrained": over_constrained or [],
            }
        )
        super().__init__(message, context=context, **kwargs)


class FeatureError(FusionMCPError):
    """Raised when feature creation or modification fails."""

    error_type = "FeatureError"
    default_suggestion = "Check feature inputs. Ensure referenced geometry exists and is valid."

    def __init__(
        self,
        feature_type: str,
        reason: str,
        fusion_error: Optional[str] = None,
        affected_entities: Optional[List[str]] = None,
        **kwargs,
    ):
        message = f"Failed to create/modify {feature_type}: {reason}"
        context = ErrorContext(
            affected_entities=affected_entities,
            additional_info={"fusion_error": fusion_error} if fusion_error else None,
        )
        super().__init__(message, context=context, **kwargs)


class SelectionError(FusionMCPError):
    """Raised when entity selection is invalid for an operation."""

    error_type = "SelectionError"
    default_suggestion = "Ensure the selected entity type matches what the operation requires."

    def __init__(
        self,
        operation: str,
        expected_types: List[str],
        actual_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        **kwargs,
    ):
        if actual_type:
            message = f"Invalid selection for {operation}: expected {expected_types}, got {actual_type}"
        else:
            message = f"Invalid selection for {operation}: expected one of {expected_types}"

        context = ErrorContext(
            requested_id=entity_id,
            additional_info={
                "expected_types": expected_types,
                "actual_type": actual_type,
            }
        )
        super().__init__(message, context=context, **kwargs)


class ConnectionError(FusionMCPError):
    """Raised when connection to Fusion 360 add-in fails."""

    error_type = "ConnectionError"
    default_suggestion = "Ensure Fusion 360 is running with the MCP add-in loaded. Check the port configuration."

    def __init__(
        self,
        host: str,
        port: int,
        reason: Optional[str] = None,
        **kwargs,
    ):
        message = f"Cannot connect to Fusion 360 at {host}:{port}"
        if reason:
            message += f": {reason}"

        context = ErrorContext(
            additional_info={"host": host, "port": port}
        )
        super().__init__(message, context=context, **kwargs)


class TimeoutError(FusionMCPError):
    """Raised when an operation times out."""

    error_type = "TimeoutError"
    default_suggestion = "The operation took too long. Try simplifying the operation or increasing the timeout."

    def __init__(
        self,
        operation: str,
        timeout_seconds: float,
        **kwargs,
    ):
        message = f"Operation '{operation}' timed out after {timeout_seconds} seconds"
        context = ErrorContext(
            additional_info={"timeout": timeout_seconds}
        )
        super().__init__(message, context=context, **kwargs)


class DesignStateError(FusionMCPError):
    """Raised when the design is in an invalid state for the operation."""

    error_type = "DesignStateError"
    default_suggestion = "Use get_design_state() to check the current design state before proceeding."

    def __init__(
        self,
        issue: str,
        current_state: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        message = f"Design state error: {issue}"
        context = ErrorContext(additional_info=current_state)
        super().__init__(message, context=context, **kwargs)
