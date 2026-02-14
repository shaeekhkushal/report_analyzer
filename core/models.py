from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from enum import Enum

class ReportType(Enum):
    """Supported report types"""
    K6 = "k6"
    LOCUST = "locust"
    JMETER = "jmeter"
    GRAFANA = "grafana"
    LIGHTHOUSE = "lighthouse"
    HR_SYSTEM = "hr_system"
    ANALYTICS = "analytics"
    JSON = "json"
    CSV = "csv"
    XLSX = "xlsx"
    UNKNOWN = "unknown"

@dataclass
class Metric:
    """Generic metric representation"""
    name: str
    value: float
    unit: str = ""
    percentile: Optional[int] = None  # For p50, p95, p99, etc.
    
    def __repr__(self) -> str:
        if self.percentile:
            return f"{self.name}(p{self.percentile}): {self.value}{self.unit}"
        return f"{self.name}: {self.value}{self.unit}"

@dataclass
class DurationStats:
    """Latency/Duration statistics - common across many report types"""
    avg: float = 0
    med: float = 0
    p90: float = 0
    p95: float = 0
    max: float = 0
    
    def to_metrics(self, prefix: str = "") -> list[Metric]:
        """Convert to generic metric list"""
        name_prefix = f"{prefix}_" if prefix else ""
        return [
            Metric(f"{name_prefix}avg", self.avg, "ms"),
            Metric(f"{name_prefix}median", self.med, "ms", percentile=50),
            Metric(f"{name_prefix}p90", self.p90, "ms", percentile=90),
            Metric(f"{name_prefix}p95", self.p95, "ms", percentile=95),
            Metric(f"{name_prefix}max", self.max, "ms"),
        ]

@dataclass
class TestSummary:
    """K6-specific test summary - backward compatible"""
    total_requests: int = 0
    failed_requests: int = 0
    failure_rate: float = 0
    http_duration: DurationStats = field(default_factory=DurationStats)
    
    def to_universal_report(self) -> "UniversalReport":
        """Convert to universal report format"""
        metrics = {
            "total_requests": Metric("total_requests", float(self.total_requests), "count"),
            "failed_requests": Metric("failed_requests", float(self.failed_requests), "count"),
            "failure_rate": Metric("failure_rate", self.failure_rate, "%"),
        }
        metrics.update({
            m.name: m for m in self.http_duration.to_metrics("http_duration")
        })
        
        return UniversalReport(
            report_type=ReportType.K6,
            metrics=metrics,
            metadata={"source": "k6_html_report"},
            raw_data=self
        )

@dataclass
class UniversalReport:
    """Universal report representation - works across all report types"""
    report_type: ReportType
    metrics: Dict[str, Metric] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_data: Any = None  # Reference to original type-specific data
    
    def get_metric(self, name: str) -> Optional[Metric]:
        """Get a metric by name"""
        return self.metrics.get(name)
    
    def add_metric(self, metric: Metric) -> None:
        """Add a metric"""
        self.metrics[metric.name] = metric
    
    def all_metrics(self) -> list[Metric]:
        """Get all metrics as sorted list"""
        return sorted(self.metrics.values(), key=lambda m: m.name)
    
    def __repr__(self) -> str:
        return f"UniversalReport({self.report_type.value}, {len(self.metrics)} metrics)"
