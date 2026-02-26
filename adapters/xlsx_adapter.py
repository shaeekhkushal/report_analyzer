"""
Excel/XLSX Report Adapter
Parses metrics from Excel files (common for exported reports, dashboards)
"""

from typing import Dict, Any
from core.models import UniversalReport, ReportType, Metric
from core.metric_normalizer import MetricNormalizer


def parse_xlsx_report(sheets: Dict[str, list]) -> UniversalReport:
    """Parse Excel data and extract metrics"""
    metrics = {}
    metadata = {}
    
    if not sheets:
        return UniversalReport(report_type=ReportType.UNKNOWN, metrics=metrics)
    
    # Use first sheet with data
    sheet_names = list(sheets.keys())
    sheet_name = sheet_names[0] if sheet_names else None
    rows = sheets.get(sheet_name, []) if sheet_name else []
    
    metadata["sheet_name"] = sheet_name
    metadata["num_sheets"] = len(sheets)
    
    # If empty rows, try other sheets
    if not rows and len(sheets) > 1:
        for sn in sheet_names[1:]:
            rows = sheets.get(sn, [])
            if rows:
                sheet_name = sn
                break
    
    if not rows:
        return UniversalReport(report_type=ReportType.UNKNOWN, metrics=metrics)
    
    # Strategy 1: Single row with metrics (header + values)
    if len(rows) == 1:
        metrics = _extract_key_value_metrics(rows[0])
    
    # Strategy 2: Multiple rows with metrics
    else:
        metrics = _extract_table_metrics(rows)
    
    # Normalize metrics to universal schema
    metrics = MetricNormalizer.normalize_metrics(metrics)
    
    # Calculate derived metrics
    _calculate_derived_metrics(metrics)
    
    # Detect report type using normalized metrics
    metric_names = list(metrics.keys())
    report_type = MetricNormalizer.detect_tool_from_metrics(metric_names)
    if report_type == ReportType.UNKNOWN:
        report_type = _detect_report_type(rows)
    
    report = UniversalReport(
        report_type=report_type,
        metrics=metrics,
        metadata=metadata
    )
    
    return report


def _extract_key_value_metrics(row: Dict[str, Any]) -> Dict[str, Metric]:
    """Extract metrics from single row"""
    metrics = {}
    
    for key, value in row.items():
        if value is None:
            continue
        
        key_clean = str(key).lower().strip().replace(" ", "_")
        
        # Convert to numeric
        try:
            if isinstance(value, (int, float)):
                numeric_val = float(value)
            else:
                numeric_val = float(str(value).replace(",", ""))
            
            metric = Metric(name=key_clean, value=numeric_val, unit="")
            metrics[key_clean] = metric
        except (ValueError, TypeError):
            pass
    
    return metrics


def _extract_table_metrics(rows: list) -> Dict[str, Metric]:
    """Extract metrics from table format"""
    metrics = {}
    
    if not rows:
        return metrics
    
    headers = list(rows[0].keys()) if isinstance(rows[0], dict) else []
    
    # Find metric columns
    name_col = None
    value_col = None
    
    for h in headers:
        h_str = str(h).lower()
        if any(x in h_str for x in ["metric", "name", "label", "test", "endpoint"]):
            name_col = h
        elif any(x in h_str for x in ["value", "result", "avg", "mean", "count"]):
            value_col = h
    
    # Extract with found columns
    if name_col and value_col:
        for row in rows:
            if not isinstance(row, dict):
                continue
            
            name = str(row.get(name_col, "")).lower().replace(" ", "_")
            value = row.get(value_col)
            
            if name and value is not None:
                try:
                    numeric_val = float(value) if isinstance(value, (int, float)) else float(str(value).replace(",", ""))
                    metric = Metric(name=name, value=numeric_val, unit="")
                    metrics[name] = metric
                except (ValueError, TypeError):
                    pass
    
    # Aggregate numeric columns
    if not metrics:
        numeric_cols = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            
            for key, value in row.items():
                if value is not None:
                    try:
                        numeric_val = float(value) if isinstance(value, (int, float)) else float(str(value).replace(",", ""))
                        if key not in numeric_cols:
                            numeric_cols[key] = []
                        numeric_cols[key].append(numeric_val)
                    except (ValueError, TypeError):
                        pass
        
        for col, values in numeric_cols.items():
            if values:
                col_clean = str(col).lower().replace(" ", "_")
                avg_val = sum(values) / len(values)
                metric = Metric(name=col_clean, value=avg_val, unit="")
                metrics[col_clean] = metric
    
    return metrics


def _detect_report_type(rows: list) -> ReportType:
    """Detect report type from Excel structure"""
    if not rows or not isinstance(rows[0], dict):
        return ReportType.UNKNOWN
    
    headers = {str(k).lower() for k in rows[0].keys()}
    
    # K6 indicators
    if any(k in headers for k in ["http_req_duration", "http_reqs", "vus"]):
        return ReportType.K6
    
    # Locust indicators
    if any(k in headers for k in ["response_time", "num_requests", "num_failures"]):
        return ReportType.LOCUST
    
    # JMeter indicators
    if any(k in headers for k in ["label", "samples", "average", "min", "max"]):
        return ReportType.JMETER
    
    # Generic
    if any(k in headers for k in ["metric", "test", "avg", "value"]):
        return ReportType.ANALYTICS
    
    return ReportType.UNKNOWN


def _calculate_derived_metrics(metrics: Dict[str, Metric]):
    """Calculate metrics that can be derived from other metrics"""
    # Calculate failure rate if we have total_requests and failed_requests
    if "total_requests" in metrics and "failed_requests" in metrics:
        total = metrics["total_requests"].value
        failed = metrics["failed_requests"].value
        
        if total > 0 and "failure_rate" not in metrics:
            failure_rate = (failed / total) * 100
            metrics["failure_rate"] = Metric(
                name="failure_rate",
                value=failure_rate,
                unit="%"
            )
    
    # Calculate success rate if we have failure_rate
    if "failure_rate" in metrics and "success_rate" not in metrics:
        failure_rate = metrics["failure_rate"].value
        success_rate = 100 - failure_rate
        metrics["success_rate"] = Metric(
            name="success_rate",
            value=success_rate,
            unit="%"
        )
    
    # Calculate throughput if we have total_requests and duration
    if "total_requests" in metrics and "test_duration" in metrics:
        if "throughput" not in metrics:
            total = metrics["total_requests"].value
            duration = metrics["test_duration"].value
            
            if duration > 0:
                throughput = total / duration
                metrics["throughput"] = Metric(
                    name="throughput",
                    value=throughput,
                    unit="req/s"
                )


def _detect_xlsx_report(data: Any) -> bool:
    """Detect if data is a report-like Excel file"""
    if not isinstance(data, dict):
        return False
    
    # Check if has sheet data
    for sheet_data in data.values():
        if isinstance(sheet_data, list) and sheet_data and isinstance(sheet_data[0], dict):
            # Check for numeric values
            has_numeric = any(
                isinstance(v, (int, float)) or (isinstance(v, str) and v.replace(".", "").replace(",", "").replace("-", "").isdigit())
                for v in sheet_data[0].values()
            )
            if has_numeric:
                return True
    
    return False
