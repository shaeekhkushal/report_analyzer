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


# ============================================================================
# Enhanced Analysis Models (for detailed reporting)
# ============================================================================

class MetricStatus(Enum):
    """Status evaluation for metrics"""
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"
    INFO = "info"


class IssueCategory(Enum):
    """Issue severity categories"""
    CRITICAL = "critical"
    HIGH = "high"
    MODERATE = "moderate"
    WARNING = "warning"
    INFO = "info"


@dataclass
class MetricWithStatus:
    """Metric with evaluation status and target"""
    name: str
    value: float
    unit: str
    status: MetricStatus
    target: Optional[float] = None
    target_unit: Optional[str] = None
    percentile: Optional[int] = None
    notes: str = ""
    
    def status_icon(self) -> str:
        """Get status icon for display"""
        icons = {
            MetricStatus.PASS: "✅",
            MetricStatus.WARNING: "⚠️",
            MetricStatus.FAIL: "❌",
            MetricStatus.INFO: "ℹ️"
        }
        return icons.get(self.status, "")
    
    def formatted_value(self) -> str:
        """Format value with unit"""
        if self.value >= 1000 and self.unit == "ms":
            return f"{self.value/1000:.2f}s"
        elif self.value >= 1000000:
            return f"{self.value/1000000:.2f}M"
        elif self.value >= 1000:
            return f"{self.value/1000:.2f}K"
        return f"{self.value:.2f}{self.unit}"
    
    def gap_percentage(self) -> Optional[float]:
        """Calculate gap from target as percentage"""
        if self.target is None or self.target == 0:
            return None
        return ((self.value - self.target) / self.target) * 100


@dataclass
class Issue:
    """Identified performance or reliability issue"""
    id: int
    title: str
    category: IssueCategory
    details: str
    impact: str
    likely_causes: list[str] = field(default_factory=list)
    affected_metrics: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    
    def severity_label(self) -> str:
        """Get formatted severity label"""
        return self.category.value.upper()


@dataclass
class Recommendation:
    """Actionable recommendation"""
    category: str  # "Immediate Diagnostics", "Targeted Optimizations", "Next Test Iteration"
    title: str
    details: str
    priority: int = 1  # 1=high, 2=medium, 3=low
    related_issues: list[int] = field(default_factory=list)


@dataclass
class ExecutiveSummary:
    """High-level test summary"""
    test_type: str
    test_date: Optional[str] = None
    duration: Optional[str] = None
    test_status: str = "UNKNOWN"
    source_file: str = ""
    key_findings: list[str] = field(default_factory=list)
    critical_issue: Optional[str] = None


@dataclass
class RequestStatistics:
    """Request-level statistics"""
    total_requests: Optional[MetricWithStatus] = None
    failed_requests: Optional[MetricWithStatus] = None
    success_rate: Optional[MetricWithStatus] = None
    requests_rate: Optional[MetricWithStatus] = None


@dataclass
class ResponseTimeAnalysis:
    """Response time breakdown"""
    avg: Optional[MetricWithStatus] = None
    median: Optional[MetricWithStatus] = None
    p90: Optional[MetricWithStatus] = None
    p95: Optional[MetricWithStatus] = None
    p99: Optional[MetricWithStatus] = None
    max: Optional[MetricWithStatus] = None
    min: Optional[MetricWithStatus] = None


@dataclass
class LoadProfile:
    """Load test configuration"""
    min_vus: Optional[int] = None
    max_vus: Optional[int] = None
    iterations: Optional[int] = None
    duration: Optional[str] = None
    rps: Optional[float] = None


@dataclass
class KeyMetrics:
    """Organized key metrics"""
    request_statistics: RequestStatistics = field(default_factory=RequestStatistics)
    response_time_analysis: ResponseTimeAnalysis = field(default_factory=ResponseTimeAnalysis)
    load_profile: LoadProfile = field(default_factory=LoadProfile)
    custom_metrics: list[MetricWithStatus] = field(default_factory=list)


@dataclass
class IssueList:
    """Categorized issues"""
    critical: list[Issue] = field(default_factory=list)
    high: list[Issue] = field(default_factory=list)
    moderate: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)
    info: list[Issue] = field(default_factory=list)
    
    def all_issues(self) -> list[Issue]:
        """Get all issues in severity order"""
        return (self.critical + self.high + self.moderate + 
                self.warnings + self.info)
    
    def total_count(self) -> int:
        """Total number of issues"""
        return len(self.all_issues())


@dataclass
class GapAnalysis:
    """Performance gap analysis"""
    metric: str
    current: float
    target: float
    unit: str
    gap_percentage: float
    required_improvement: str


@dataclass
class DetailedAnalysis:
    """Complete detailed analysis output"""
    executive_summary: ExecutiveSummary
    key_metrics: KeyMetrics
    issues: IssueList
    recommendations: list[Recommendation] = field(default_factory=list)
    gap_analysis: list[GapAnalysis] = field(default_factory=list)
    source_report: Optional[UniversalReport] = None
    
    def has_critical_issues(self) -> bool:
        """Check if there are critical issues"""
        return len(self.issues.critical) > 0
    
    def total_issues(self) -> int:
        """Total number of issues"""
        return self.issues.total_count()
