"""
Utility: formatters for weights, dates, currency, and labels.
"""
from datetime import date, datetime


def fmt_weight(value, decimals: int = 3) -> str:
    """Format a weight value to N decimal places with 'g' suffix."""
    if value is None:
        return "—"
    try:
        return f"{float(value):,.{decimals}f} g"
    except (TypeError, ValueError):
        return "—"


def fmt_weight_plain(value, decimals: int = 3) -> str:
    """Format a weight value without suffix."""
    if value is None:
        return ""
    try:
        return f"{float(value):,.{decimals}f}"
    except (TypeError, ValueError):
        return ""


def fmt_date(value) -> str:
    """Format date to DD-Mon-YY string."""
    if value is None:
        return "—"
    if isinstance(value, (date, datetime)):
        return value.strftime("%d-%b-%y")
    try:
        return str(value)
    except Exception:
        return "—"


def fmt_date_long(value) -> str:
    """Format date to full readable string."""
    if value is None:
        return "—"
    if isinstance(value, (date, datetime)):
        return value.strftime("%d %B %Y")
    return str(value)


def fmt_pcs(value) -> str:
    """Format piece count."""
    if value is None or value == 0:
        return "—"
    return str(int(value))


def fmt_currency(value) -> str:
    """Format as Indian currency."""
    if value is None:
        return "—"
    return f"₹ {float(value):,.2f}"


def fmt_percent(value) -> str:
    """Format as percentage."""
    if value is None:
        return "—"
    return f"{float(value):.2f}%"


def fmt_serial(value) -> str:
    """Format serial number."""
    if value is None:
        return "—"
    return str(int(value))


def safe_float(value, default: float = 0.0) -> float:
    """Safely convert to float."""
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def safe_int(value, default: int = 0) -> int:
    """Safely convert to int."""
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def calc_loss(weight_in: float, weight_out: float) -> float:
    """Compute weight loss."""
    return max(0.0, safe_float(weight_in) - safe_float(weight_out))


def calc_ppwl(weight_loss: float, pcs: int) -> float:
    """Per piece weight loss."""
    if not pcs or pcs == 0:
        return 0.0
    return safe_float(weight_loss) / int(pcs)


def calc_extra_loss(actual_wl: float, allowed_ppwl: float, pcs: int) -> float:
    """Extra loss = actual loss - (allowed_ppwl × pcs)."""
    allowed = safe_float(allowed_ppwl) * safe_int(pcs)
    return safe_float(actual_wl) - allowed


def calc_pay(pcs: int, rate_per_chain: float) -> float:
    """Goldsmith pay = pcs × rate_per_chain."""
    return safe_int(pcs) * safe_float(rate_per_chain)


def calc_gold_box_closing(opening: float, total_in: float, total_out: float) -> float:
    """Gold box closing = opening + in - out."""
    return safe_float(opening) + safe_float(total_in) - safe_float(total_out)


def month_year_str(d=None) -> str:
    """Return month-year string like 'Apr-26'."""
    if d is None:
        d = date.today()
    return d.strftime("%b-%y")
