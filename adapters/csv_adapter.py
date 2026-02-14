"""
CSV Report Adapter
Parses metrics from CSV files (common for exported test results, dashboards)
"""

from typing import List, Dict, Any
from core.models import UniversalReport, ReportType, Metric


def parse_csv_report(rows: List[Dict[str, str]]) -> UniversalReport:
    """Parse CSV data and extract metrics"""
    metrics = {}
    
    if not rows:
        return UniversalReport(report_type=ReportType.UNKNOWN, metrics=metrics)
    
    # Strategy 1: If first row has numeric values, treat as key-value pairs
    if len(rows) == 1:
        metrics = _extract_key_value_metrics(rows[0])
    
    # Strategy 2: Column-based metrics (common format)
    else:
        metrics = _extract_column_metrics(rows)
    
    # Detect report type
    report_type = _detect_report_type(rows)
    
    report = UniversalReport(
        report_type=report_type,
        metrics=metrics,
        metadata=_extract_metadata(rows)
    )
    
    return report


def _extract_key_value_metrics(row: Dict[str, str]) -> Dict[str, Metric]:
    """Extract metrics from single row (key-value format)"""
    metrics = {}
    
    for key, value in row.items():
        key_clean = key.lower().strip()
        
        # Try to convert to number
        try:
            # Handle both int and float
            if "." in str(value):
                numeric_val = float(value)
            else:
                numeric_val = float(int(value))
            
            metric = Metric(name=key_clean, value=numeric_val, unit="")
            metrics[key_clean] = metric
        except (ValueError, TypeError):
            # Non-numeric value, skip
            pass
    
    return metrics


def _extract_column_metrics(rows: List[Dict[str, str]]) -> Dict[str, Metric]:
    """Extract metrics from multiple rows (column-based format)"""
    metrics = {}
    headers = list(rows[0].keys()) if rows else []
    
    # Look for common patterns
    name_col = None
    value_col = None
    
    # Try to find name/metric column and value column
    for h in headers:
        h_lower = h.lower()
        if any(x in h_lower for x in ["metric", "name", "label", "test", "endpoint"]):
            name_col = h
        elif any(x in h_lower for x in ["value", "result", "avg", "count", "total", "amount"]):
            value_col = h
    
    # If found both, use them
    if name_col and value_col:
        for row in rows:
            name = row.get(name_col, "").lower().replace(" ", "_")
            value_str = row.get(value_col, "")
            
            if name and value_str:
                try:
                    numeric_val = float(value_str.replace(",", ""))
                    metric = Metric(name=name, value=numeric_val, unit="")
                    metrics[name] = metric
                except ValueError:
                    pass
    
    # Otherwise, aggregate numeric columns
    if not metrics:
        numeric_cols = {}
        for row in rows:
            for key, value in row.items():
                try:
                    numeric_val = float(value.replace(",", ""))
                    if key not in numeric_cols:
                        numeric_cols[key] = []
                    numeric_cols[key].append(numeric_val)
                except (ValueError, AttributeError):
                    pass
        
        # Create aggregated metrics
        for col, values in numeric_cols.items():
            if values:
                col_clean = col.lower().replace(" ", "_")
                avg_val = sum(values) / len(values)
                metric = Metric(name=col_clean, value=avg_val, unit="")
                metrics[col_clean] = metric
    
    return metrics


def _detect_report_type(rows: List[Dict[str, str]]) -> ReportType:
    """Detect report type from CSV structure"""
    if not rows:
        return ReportType.UNKNOWN
    
    # Check column names
    headers = list(rows[0].keys())
    headers_lower = {h.lower() for h in headers}
    
    # K6 indicators
    if any(k in headers_lower for k in ["http_req_duration", "http_reqs", "vus", "requests"]):
        return ReportType.K6
    
    # Locust indicators
    if any(k in headers_lower for k in ["response_time", "num_requests", "num_failures"]):
        return ReportType.LOCUST
    
    # JMeter indicators
    if any(k in headers_lower for k in ["label", "samples", "average", "min", "max", "error_rate"]):
        return ReportType.JMETER
    
    # Generic performance
    if any(k in headers_lower for k in ["test", "metric", "avg", "latency", "throughput"]):
        return ReportType.ANALYTICS
    
    return ReportType.UNKNOWN


def _extract_metadata(rows: List[Dict[str, str]]) -> dict:
    """Extract metadata from CSV"""
    metadata = {}
    
    if not rows:
        return metadata
    
    first_row = rows[0]
    metadata_keys = ["test_name", "test_id", "environment", "timestamp", "date",
                    "duration", "version", "build", "branch"]
    
    for key in metadata_keys:
        for col_name in first_row:
            if col_name.lower() == key.lower():
                metadata[key] = first_row[col_name]
                break
    
    # Count rows as potential test count
    metadata["row_count"] = len(rows)
    
    return metadata


def _detect_csv_report(data: Any) -> bool:
    """Detect if data is a report-like CSV"""
    if not isinstance(data, list) or not data:
        return False
    
    # Check first row is dict
    if not isinstance(data[0], dict):
        return False
    
    # Check if has numeric values
    has_numeric = any(
        isinstance(v, (int, float)) or (isinstance(v, str) and v.replace(".", "").replace(",", "").isdigit())
        for row in data[:1]  # Check first row only
        for v in row.values()
    )
    
    return has_numeric
