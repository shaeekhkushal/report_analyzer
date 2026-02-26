"""
Metric Normalization Layer
Converts tool-specific metric names to universal schema for consistent analysis
"""

from typing import Dict, Optional, List
from core.models import Metric, ReportType


class MetricNormalizer:
    """
    Normalizes metrics from different performance testing tools to a universal schema
    
    Universal Schema:
    - total_requests: Total number of requests/transactions
    - failed_requests: Number of failed requests
    - failure_rate: Percentage of failed requests (0-100)
    - success_rate: Percentage of successful requests (0-100)
    - http_duration_avg: Average response time (ms)
    - http_duration_median: Median response time (ms)
    - http_duration_min: Minimum response time (ms)
    - http_duration_max: Maximum response time (ms)
    - http_duration_p90: 90th percentile response time (ms)
    - http_duration_p95: 95th percentile response time (ms)
    - http_duration_p99: 99th percentile response time (ms)
    - throughput: Requests per second
    - concurrent_users: Number of concurrent virtual users
    - test_duration: Total test duration (seconds)
    """
    
    # Mapping table: universal_name -> [list of possible tool-specific names]
    METRIC_MAPPINGS = {
        # Total Requests
        "total_requests": [
            "total_requests", "totalrequests", "total requests",
            "requests", "# requests", "num_requests", "request_count",
            "samples", "# samples", "num_samples", "sample_count",
            "transactions", "total_transactions", "transaction_count",
            "requestcount", "request count", "totalreqs",
            "count", "total", "all_requests"
        ],
        
        # Failed Requests
        "failed_requests": [
            "failed_requests", "failedrequests", "failed requests",
            "failures", "# failures", "num_failures", "failure_count",
            "errors", "# errors", "num_errors", "error_count",
            "failed", "fails", "error", "ko", "nok",
            "failedcount", "errorcount", "failed_count"
        ],
        
        # Failure Rate (percentage)
        "failure_rate": [
            "failure_rate", "failurerate", "failure rate",
            "error_rate", "errorrate", "error rate",
            "error_%", "error %", "error%", "error pct",
            "failure_%", "failure %", "failure%", "failure pct",
            "fail_rate", "fail rate", "failed_rate",
            "error_percentage", "failure_percentage"
        ],
        
        # Success Rate (percentage)
        "success_rate": [
            "success_rate", "successrate", "success rate",
            "success_%", "success %", "success%", "success pct",
            "pass_rate", "passrate", "pass rate",
            "ok_rate", "okrate"
        ],
        
        # Average Response Time
        "http_duration_avg": [
            "http_duration_avg", "http_req_duration_avg", "httpdurationavg",
            "avg", "average", "avg_response_time", "average_response_time",
            "response_time_avg", "responsetime_avg", "mean", "mean_response_time",
            "avg_time", "avgtime", "average_time", "averagetime",
            "avg_latency", "average_latency", "latency_avg",
            "mean_latency", "response_avg", "avgresponsetime"
        ],
        
        # Median Response Time
        "http_duration_median": [
            "http_duration_median", "http_req_duration_median",
            "median", "median_response_time", "response_time_median",
            "p50", "50th_percentile", "50th percentile", "50%",
            "percentile_50", "percentile50", "med", "median_time",
            "median_latency", "latency_median", "response_median"
        ],
        
        # Minimum Response Time
        "http_duration_min": [
            "http_duration_min", "http_req_duration_min",
            "min", "minimum", "min_response_time", "minimum_response_time",
            "response_time_min", "responsetime_min",
            "min_time", "mintime", "minimum_time",
            "min_latency", "minimum_latency", "latency_min"
        ],
        
        # Maximum Response Time
        "http_duration_max": [
            "http_duration_max", "http_req_duration_max",
            "max", "maximum", "max_response_time", "maximum_response_time",
            "response_time_max", "responsetime_max",
            "max_time", "maxtime", "maximum_time",
            "max_latency", "maximum_latency", "latency_max"
        ],
        
        # P90 Response Time
        "http_duration_p90": [
            "http_duration_p90", "http_req_duration_p90",
            "p90", "90th_percentile", "90th percentile", "90%", "90%ile",
            "percentile_90", "percentile90", "response_time_p90",
            "latency_p90", "p_90"
        ],
        
        # P95 Response Time
        "http_duration_p95": [
            "http_duration_p95", "http_req_duration_p95",
            "p95", "95th_percentile", "95th percentile", "95%", "95%ile",
            "percentile_95", "percentile95", "response_time_p95",
            "latency_p95", "p_95", "95th_pct", "95th pct"
        ],
        
        # P99 Response Time
        "http_duration_p99": [
            "http_duration_p99", "http_req_duration_p99",
            "p99", "99th_percentile", "99th percentile", "99%", "99%ile",
            "percentile_99", "percentile99", "response_time_p99",
            "latency_p99", "p_99", "99th_pct", "99th pct"
        ],
        
        # Throughput (requests per second)
        "throughput": [
            "throughput", "rps", "requests_per_second", "requests_per_sec",
            "req_per_sec", "req/s", "requests/s", "req/sec",
            "transactions_per_second", "tps", "trans_per_sec",
            "rate", "request_rate", "transaction_rate"
        ],
        
        # Concurrent Users / Virtual Users
        "concurrent_users": [
            "concurrent_users", "concurrentusers", "concurrent users",
            "vus", "virtual_users", "virtualusers", "virtual users",
            "users", "num_users", "user_count",
            "threads", "num_threads", "thread_count",
            "connections", "concurrent_connections"
        ],
        
        # Test Duration
        "test_duration": [
            "test_duration", "testduration", "test duration",
            "duration", "total_duration", "elapsed_time",
            "run_duration", "execution_time", "test_time"
        ]
    }
    
    # Reverse mapping for quick lookup: tool_name -> universal_name
    _REVERSE_MAPPING: Optional[Dict[str, str]] = None
    
    @classmethod
    def _build_reverse_mapping(cls) -> Dict[str, str]:
        """Build reverse lookup table (tool_name -> universal_name)"""
        if cls._REVERSE_MAPPING is not None:
            return cls._REVERSE_MAPPING
        
        reverse = {}
        for universal_name, tool_names in cls.METRIC_MAPPINGS.items():
            for tool_name in tool_names:
                # Store lowercase for case-insensitive matching
                reverse[tool_name.lower()] = universal_name
        
        cls._REVERSE_MAPPING = reverse
        return reverse
    
    @classmethod
    def normalize_metric_name(cls, tool_name: str) -> str:
        """
        Normalize a tool-specific metric name to universal schema
        
        Args:
            tool_name: Original metric name from tool report
            
        Returns:
            Universal metric name, or original if no mapping found
        """
        reverse_map = cls._build_reverse_mapping()
        
        # Clean the tool name
        cleaned = tool_name.lower().strip()
        cleaned = cleaned.replace("_", " ").replace("-", " ")
        
        # Try exact match first
        if cleaned in reverse_map:
            return reverse_map[cleaned]
        
        # Try with spaces removed
        no_spaces = cleaned.replace(" ", "")
        if no_spaces in reverse_map:
            return reverse_map[no_spaces]
        
        # Try partial matching for complex names
        for tool_pattern, universal_name in reverse_map.items():
            if tool_pattern in cleaned or cleaned in tool_pattern:
                # Verify it's a meaningful match (not just "a" in "average")
                if len(tool_pattern) > 3 and len(cleaned) > 3:
                    return universal_name
        
        # No mapping found, return original
        return tool_name
    
    @classmethod
    def normalize_metrics(cls, metrics: Dict[str, Metric]) -> Dict[str, Metric]:
        """
        Normalize all metrics in a dictionary
        
        Args:
            metrics: Dictionary of metric_name -> Metric objects
            
        Returns:
            New dictionary with normalized metric names
        """
        normalized = {}
        
        for original_name, metric in metrics.items():
            # Get normalized name
            universal_name = cls.normalize_metric_name(original_name)
            
            # Create new metric with normalized name
            normalized_metric = Metric(
                name=universal_name,
                value=metric.value,
                unit=metric.unit,
                percentile=metric.percentile
            )
            
            # Use normalized name as key
            # If duplicate, keep the first one (could be improved with priority logic)
            if universal_name not in normalized:
                normalized[universal_name] = normalized_metric
        
        return normalized
    
    @classmethod
    def get_metric_with_fallbacks(cls, metrics: Dict[str, Metric], 
                                   primary_name: str, 
                                   fallback_names: Optional[List[str]] = None) -> Optional[Metric]:
        """
        Get metric value with fallback options
        
        Args:
            metrics: Dictionary of metrics
            primary_name: Primary metric name to look for
            fallback_names: List of alternative names to try
            
        Returns:
            Metric object if found, None otherwise
        """
        # Try primary name
        if primary_name in metrics:
            return metrics[primary_name]
        
        # Try fallbacks
        if fallback_names:
            for fallback in fallback_names:
                if fallback in metrics:
                    return metrics[fallback]
        
        # Try all possible variations from mapping table
        if primary_name in cls.METRIC_MAPPINGS:
            for variant in cls.METRIC_MAPPINGS[primary_name]:
                if variant in metrics:
                    return metrics[variant]
        
        return None
    
    @classmethod
    def get_metric_value(cls, metrics: Dict[str, Metric], 
                        metric_name: str, 
                        default: float = 0.0) -> float:
        """
        Get metric value with fallbacks, returns default if not found
        
        Args:
            metrics: Dictionary of metrics
            metric_name: Universal metric name
            default: Default value if not found
            
        Returns:
            Metric value or default
        """
        metric = cls.get_metric_with_fallbacks(metrics, metric_name)
        return metric.value if metric else default
    
    @classmethod
    def detect_tool_from_metrics(cls, metric_names: List[str]) -> ReportType:
        """
        Detect tool type from metric name patterns
        
        Args:
            metric_names: List of metric names extracted from report
            
        Returns:
            Detected ReportType
        """
        metric_set = set(name.lower().strip() for name in metric_names)
        
        # K6 specific indicators (strong signals)
        k6_indicators = ["http_req_duration", "http_req_blocked", "http_req_connecting", 
                        "http_req_waiting", "http_req_sending", "http_req_receiving"]
        if any(ind in metric_set for ind in k6_indicators):
            return ReportType.K6
        
        # Locust indicators
        locust_indicators = ["response_time_percentile", "num_requests", "num_failures", 
                           "current_rps", "95%ile", "median (ms)"]
        if any(ind.replace(" ", "").replace("_", "") in "".join(metric_set) for ind in locust_indicators):
            return ReportType.LOCUST
        
        # JMeter indicators
        jmeter_indicators = ["# samples", "error %", "std. dev", "throughput", 
                           "kb/sec", "avg bytes"]
        if any(ind.lower() in metric_set for ind in jmeter_indicators):
            return ReportType.JMETER
        
        # Gatling indicators
        gatling_indicators = ["meanresponsetime", "stddeviation", "percentiles1", 
                            "percentiles2", "percentiles3", "percentiles4"]
        if any(ind in metric_set for ind in gatling_indicators):
            return ReportType.ANALYTICS  # Use ANALYTICS for Gatling
        
        # Generic performance test indicators
        perf_indicators = ["requests", "errors", "latency", "throughput", "response_time",
                          "p95", "p99", "average", "failures"]
        if sum(1 for ind in perf_indicators if ind in metric_set) >= 3:
            return ReportType.ANALYTICS
        
        return ReportType.UNKNOWN


def normalize_metrics(metrics: Dict[str, Metric]) -> Dict[str, Metric]:
    """Convenience function for normalizing metrics"""
    return MetricNormalizer.normalize_metrics(metrics)


def get_metric_value(metrics: Dict[str, Metric], metric_name: str, default: float = 0.0) -> float:
    """Convenience function for getting metric values with fallbacks"""
    return MetricNormalizer.get_metric_value(metrics, metric_name, default)
