"""
Field validation helpers.
"""
from datetime import date


class ValidationError(Exception):
    pass


def require_field(value, field_name: str):
    """Raise ValidationError if value is empty/None."""
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValidationError(f"{field_name} is required.")
    return value


def require_positive(value, field_name: str) -> float:
    """Require a positive numeric value."""
    try:
        v = float(value)
        if v <= 0:
            raise ValidationError(f"{field_name} must be greater than zero.")
        return v
    except (TypeError, ValueError):
        raise ValidationError(f"{field_name} must be a valid number.")


def require_non_negative(value, field_name: str) -> float:
    """Require a non-negative numeric value."""
    try:
        v = float(value)
        if v < 0:
            raise ValidationError(f"{field_name} cannot be negative.")
        return v
    except (TypeError, ValueError):
        raise ValidationError(f"{field_name} must be a valid number.")


def require_positive_int(value, field_name: str) -> int:
    """Require a positive integer."""
    try:
        v = int(value)
        if v <= 0:
            raise ValidationError(f"{field_name} must be greater than zero.")
        return v
    except (TypeError, ValueError):
        raise ValidationError(f"{field_name} must be a valid integer.")


def require_date(value, field_name: str) -> date:
    """Require a valid date."""
    if isinstance(value, date):
        return value
    raise ValidationError(f"{field_name} must be a valid date.")


def validate_weight_out_le_in(weight_in: float, weight_out: float, field_name: str = "Output weight"):
    """Ensure weight_out <= weight_in."""
    if float(weight_out) > float(weight_in):
        raise ValidationError(f"{field_name} cannot exceed input weight.")


def validate_string_length(value: str, field_name: str, max_len: int = 100) -> str:
    """Validate max string length."""
    if len(value) > max_len:
        raise ValidationError(f"{field_name} must be at most {max_len} characters.")
    return value
