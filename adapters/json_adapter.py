"""
JSON Report Adapter
Parses metrics from JSON files (common for API responses, exported dashboards)
"""

from typing import Any, Dict
from core.models import UniversalReport, ReportType, Metric


def parse_json_report(data: Any) -> UniversalReport:
    """Parse JSON data and extract metrics (handles both dict and list structures)"""
    metrics = {}
    
    # If data is a list, try to find a dict with metrics or aggregate the list
    if isinstance(data, list):
        if len(data) > 0 and isinstance(data[0], dict):
            # If it's a list of dicts, try to aggregate metrics
            _extract_from_list_of_dicts(data, metrics)
        else:
            # List of primitives, try to extract numeric values
            _extract_from_simple_list(data, metrics)
    elif isinstance(data, dict):
        # Dictionary format - use all strategies
        # Strategy 1: Look for common metric keys at top level
        _extract_top_level_metrics(data, metrics)
        
        # Strategy 2: Look for nested metric objects
        _extract_nested_metrics(data, metrics)
        
        # Strategy 3: Look for arrays of metrics
        _extract_array_metrics(data, metrics)
    
    # Detect report type
    report_type = _detect_report_type(data)
    
    report = UniversalReport(
        report_type=report_type,
        metrics=metrics,
        metadata=_extract_metadata(data)
    )
    
    return report


def _extract_from_list_of_dicts(data: list, metrics: Dict[str, Metric]):
    """Extract metrics from a list of dictionaries"""
    # Look for common metric keys across all dicts
    common_keys = [
        "total_requests", "total_tests", "failed_requests", "failed_tests",
        "passed", "failed", "skipped", "errors", "warnings",
        "avg", "average", "mean", "median", "min", "max",
        "p50", "p90", "p95", "p99", "percentile_90", "percentile_95",
        "latency", "response_time", "throughput", "requests_per_second",
        "cpu", "memory", "disk", "network", "success_rate", "failure_rate",
        "uptime", "downtime", "duration", "elapsed_time"
    ]
    
    # Aggregate numeric values from list
    for item in data:
        if isinstance(item, dict):
            for key, val in item.items():
                if isinstance(val, (int, float)):
                    key_lower = key.lower().replace(" ", "_")
                    if key_lower not in metrics:
                        metric = Metric(name=key_lower, value=float(val), unit="")
                        metrics[key_lower] = metric


def _extract_from_simple_list(data: list, metrics: Dict[str, Metric]):
    """Extract metrics from a simple list of values"""
    for i, val in enumerate(data):
        if isinstance(val, (int, float)):
            key = f"value_{i}"
            metric = Metric(name=key, value=float(val), unit="")
            metrics[key] = metric


def _extract_top_level_metrics(data: Dict[str, Any], metrics: Dict[str, Metric]):
    """Extract numeric metrics from top-level keys"""
    common_keys = [
        "total_requests", "total_tests", "failed_requests", "failed_tests",
        "passed", "failed", "skipped", "errors", "warnings",
        "avg", "average", "mean", "median", "min", "max",
        "p50", "p90", "p95", "p99", "percentile_90", "percentile_95",
        "latency", "response_time", "throughput", "requests_per_second",
        "cpu", "memory", "disk", "network", "success_rate", "failure_rate",
        "uptime", "downtime", "duration", "elapsed_time"
    ]
    
    for key in common_keys:
        if key in data:
            val = data[key]
            if isinstance(val, (int, float)):
                metric = Metric(name=key, value=float(val), unit="")
                metrics[key] = metric


def _extract_nested_metrics(data: Dict[str, Any], metrics: Dict[str, Metric]):
    """Recursively extract metrics from nested objects"""
    if not isinstance(data, dict):
        return
    
    for key, value in data.items():
        if isinstance(value, (int, float)) and not key.startswith("_"):
            name = key.lower().replace(" ", "_")
            if name not in metrics:
                metric = Metric(name=name, value=float(value), unit="")
                metrics[name] = metric
        
        elif isinstance(value, dict) and len(value) < 10:  # Avoid huge objects
            # Check if this dict contains metrics
            has_metrics = any(isinstance(v, (int, float)) for v in value.values())
            if has_metrics:
                _extract_nested_metrics(value, metrics)


def _extract_array_metrics(data: Dict[str, Any], metrics: Dict[str, Metric]):
    """Extract metrics from arrays/lists"""
    if not isinstance(data, dict):
        return
    
    for key, value in data.items():
        if isinstance(value, list) and len(value) > 0:
            # Check if it's a list of dicts with metric-like structure
            first = value[0]
            if isinstance(first, dict):
                # Look for common metric fields in list items
                metric_fields = ["value", "metric", "amount", "count", "data"]
                for field in metric_fields:
                    if field in first and isinstance(first[field], (int, float)):
                        # Aggregate values
                        total = sum(item.get(field, 0) for item in value if isinstance(item, dict))
                        avg = total / len(value)
                        name = f"{key}_{field}_total"
                        if name not in metrics:
                            metrics[name] = Metric(name=name, value=float(total), unit="")
                        name_avg = f"{key}_{field}_avg"
                        if name_avg not in metrics:
                            metrics[name_avg] = Metric(name=name_avg, value=float(avg), unit="")


def _detect_report_type(data: Any) -> ReportType:
    """Detect report type from JSON structure"""
    if not isinstance(data, dict):
        # For non-dict data, return UNKNOWN
        return ReportType.UNKNOWN
    
    keys_lower = {k.lower(): v for k, v in data.items()}
    
    # K6 indicators
    if any(k in keys_lower for k in ["http_req_duration", "http_reqs", "vus"]):
        return ReportType.K6
    
    # Locust indicators
    if any(k in keys_lower for k in ["response_times", "num_requests", "num_failures", "failure_rate"]):
        return ReportType.LOCUST
    
    # JMeter indicators
    if any(k in keys_lower for k in ["samples", "average", "min_time", "max_time"]):
        return ReportType.JMETER
    
    # Grafana/Prometheus indicators
    if any(k in keys_lower for k in ["results", "series", "cpu", "memory", "disk", "network"]):
        return ReportType.GRAFANA
    
    # Generic analytics
    if any(k in keys_lower for k in ["metrics", "stats", "summary", "data"]):
        return ReportType.ANALYTICS
    
    return ReportType.UNKNOWN


def _extract_metadata(data: Any) -> dict:
    """Extract metadata from JSON"""
    metadata = {}
    
    if not isinstance(data, dict):
        # For non-dict data, return empty metadata
        return metadata
    
    metadata_keys = ["timestamp", "date", "test_name", "test_id", "environment", 
                     "version", "build", "branch", "commit", "duration", "elapsed_time"]
    
    for key in metadata_keys:
        if key in data:
            metadata[key] = data[key]
    
    return metadata


def _detect_json_report(data: Any) -> bool:
    """Detect if data is a report-like JSON"""
    if not isinstance(data, dict):
        return False
    
    # Check for common metric-like keys
    has_metrics = any(
        isinstance(v, (int, float))
        for k, v in data.items()
        if not k.startswith("_")
    )
    
    return bool(data) and has_metrics
