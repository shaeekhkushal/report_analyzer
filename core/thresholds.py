"""
Performance thresholds and targets for metric evaluation
Configurable targets for different test types and metrics
"""

from dataclasses import dataclass
from typing import Dict, Optional
from core.models import MetricStatus


@dataclass
class ThresholdConfig:
    """Threshold configuration for a metric"""
    target: float
    warning_threshold: float
    fail_threshold: float
    unit: str = ""
    lower_is_better: bool = True  # True for latency/errors, False for throughput
    
    def evaluate(self, value: float) -> MetricStatus:
        """Evaluate a value against thresholds"""
        if self.lower_is_better:
            # For metrics like latency, errors (lower is better)
            if value <= self.target:
                return MetricStatus.PASS
            elif value <= self.warning_threshold:
                return MetricStatus.WARNING
            else:
                return MetricStatus.FAIL
        else:
            # For metrics like throughput, success rate (higher is better)
            if value >= self.target:
                return MetricStatus.PASS
            elif value >= self.warning_threshold:
                return MetricStatus.WARNING
            else:
                return MetricStatus.FAIL


class PerformanceThresholds:
    """Centralized performance thresholds"""
    
    def __init__(self, test_type: str = "default"):
        self.test_type = test_type
        self._init_thresholds()
    
    def _init_thresholds(self):
        """Initialize default thresholds"""
        
        # ===== RESPONSE TIME THRESHOLDS (ms) =====
        if self.test_type == "stress":
            # Stress test - more lenient on latency
            self.response_time = {
                "avg": ThresholdConfig(300, 1000, 3000, "ms"),
                "median": ThresholdConfig(250, 800, 2500, "ms"),
                "p90": ThresholdConfig(500, 2000, 5000, "ms"),
                "p95": ThresholdConfig(1000, 3000, 10000, "ms"),
                "p99": ThresholdConfig(2000, 5000, 15000, "ms"),
                "max": ThresholdConfig(5000, 10000, 30000, "ms"),
            }
        elif self.test_type == "smoke":
            # Smoke test - strict thresholds
            self.response_time = {
                "avg": ThresholdConfig(100, 200, 500, "ms"),
                "median": ThresholdConfig(80, 150, 400, "ms"),
                "p90": ThresholdConfig(200, 400, 1000, "ms"),
                "p95": ThresholdConfig(300, 600, 1500, "ms"),
                "p99": ThresholdConfig(500, 1000, 3000, "ms"),
                "max": ThresholdConfig(1000, 3000, 10000, "ms"),
            }
        elif self.test_type == "load":
            # Load test - balanced thresholds
            self.response_time = {
                "avg": ThresholdConfig(200, 500, 1500, "ms"),
                "median": ThresholdConfig(150, 400, 1200, "ms"),
                "p90": ThresholdConfig(400, 1000, 3000, "ms"),
                "p95": ThresholdConfig(600, 2000, 5000, "ms"),
                "p99": ThresholdConfig(1000, 3000, 8000, "ms"),
                "max": ThresholdConfig(3000, 8000, 20000, "ms"),
            }
        else:
            # Default thresholds
            self.response_time = {
                "avg": ThresholdConfig(200, 500, 1500, "ms"),
                "median": ThresholdConfig(150, 400, 1200, "ms"),
                "p90": ThresholdConfig(400, 1000, 3000, "ms"),
                "p95": ThresholdConfig(500, 2000, 5000, "ms"),
                "p99": ThresholdConfig(1000, 3000, 8000, "ms"),
                "max": ThresholdConfig(3000, 8000, 20000, "ms"),
            }
        
        # ===== RELIABILITY THRESHOLDS =====
        self.reliability = {
            "failure_rate": ThresholdConfig(1.0, 2.0, 5.0, "%"),  # %, lower is better
            "success_rate": ThresholdConfig(99.0, 98.0, 95.0, "%", lower_is_better=False),  # %, higher is better
            "error_count": ThresholdConfig(10, 50, 100, "count"),
        }
        
        # ===== THROUGHPUT THRESHOLDS =====
        self.throughput = {
            "rps": ThresholdConfig(10.0, 5.0, 1.0, "req/s", lower_is_better=False),  # Higher is better
            "total_requests": ThresholdConfig(1000, 500, 100, "count", lower_is_better=False),
        }
        
        # ===== CHECK THRESHOLDS =====
        self.checks = {
            "pass_rate": ThresholdConfig(95.0, 90.0, 80.0, "%", lower_is_better=False),
        }
    
    def get_threshold(self, metric_name: str) -> Optional[ThresholdConfig]:
        """Get threshold config for a metric"""
        # Try to find in response_time
        if "duration" in metric_name or "latency" in metric_name or "time" in metric_name:
            for key, threshold in self.response_time.items():
                if key in metric_name:
                    return threshold
        
        # Try reliability
        if "failure" in metric_name or "error" in metric_name:
            for key, threshold in self.reliability.items():
                if key in metric_name:
                    return threshold
        
        # Try throughput
        if "throughput" in metric_name or "rps" in metric_name or "rate" in metric_name:
            for key, threshold in self.throughput.items():
                if key in metric_name:
                    return threshold
        
        # Try checks
        if "check" in metric_name or "pass" in metric_name:
            for key, threshold in self.checks.items():
                if key in metric_name:
                    return threshold
        
        return None
    
    def evaluate_metric(self, metric_name: str, value: float) -> MetricStatus:
        """Evaluate a metric value"""
        threshold = self.get_threshold(metric_name)
        if threshold:
            return threshold.evaluate(value)
        return MetricStatus.INFO  # No threshold defined


# ===== GLOBAL TARGETS (for gap analysis) =====
PERFORMANCE_TARGETS = {
    "p95_response_time": {"value": 500, "unit": "ms", "description": "95th percentile response time"},
    "p99_response_time": {"value": 1000, "unit": "ms", "description": "99th percentile response time"},
    "avg_response_time": {"value": 200, "unit": "ms", "description": "Average response time"},
    "failure_rate": {"value": 1.0, "unit": "%", "description": "Request failure rate"},
    "error_rate": {"value": 1.0, "unit": "%", "description": "Error rate"},
    "success_rate": {"value": 99.0, "unit": "%", "description": "Success rate"},
    "check_pass_rate": {"value": 100.0, "unit": "%", "description": "Check pass rate"},
    "throughput": {"value": 100.0, "unit": "req/s", "description": "Requests per second"},
}


def get_target(metric_name: str) -> Optional[Dict]:
    """Get target for a metric"""
    # Normalize metric name for matching
    normalized = metric_name.lower().replace("_", "").replace("-", "")
    
    for target_key, target_value in PERFORMANCE_TARGETS.items():
        normalized_key = target_key.lower().replace("_", "").replace("-", "")
        if normalized_key in normalized or normalized in normalized_key:
            return target_value
    
    return None
