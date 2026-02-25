"""
Detailed Analysis Engine
Generates comprehensive, structured analysis reports with:
- Executive summaries
- Categorized metrics with status
- Severity-based issues
- Actionable recommendations
- Gap analysis
"""

from typing import Optional, Dict, List
from core.models import (
    UniversalReport, DetailedAnalysis, ExecutiveSummary, KeyMetrics,
    IssueList, Issue, IssueCategory, Recommendation, GapAnalysis,
    MetricWithStatus, MetricStatus, RequestStatistics, ResponseTimeAnalysis,
    LoadProfile
)
from core.thresholds import PerformanceThresholds, get_target, PERFORMANCE_TARGETS
from core.metric_normalizer import MetricNormalizer
from datetime import datetime


class DetailedAnalyzer:
    """
    Comprehensive analyzer that generates detailed reports from UniversalReport data
    """
    
    def __init__(self, report: UniversalReport, test_type: str = "default", source_file: str = ""):
        self.report = report
        self.test_type = test_type
        self.source_file = source_file
        self.thresholds = PerformanceThresholds(test_type)
        # Convert to dict of Metric objects for MetricNormalizer
        self.metrics_dict_obj = {m.name: m for m in report.all_metrics()}
        # Keep simple value dict for backward compatibility
        self.metrics_dict = {m.name: m.value for m in report.all_metrics()}
        self.issue_counter = 0
    
    def _get_metric(self, name: str, default: float = 0.0) -> float:
        """Get metric value with fallbacks using MetricNormalizer"""
        return MetricNormalizer.get_metric_value(self.metrics_dict_obj, name, default)
    
    def analyze(self) -> DetailedAnalysis:
        """Generate complete detailed analysis"""
        
        # Build executive summary
        exec_summary = self._build_executive_summary()
        
        # Organize key metrics
        key_metrics = self._build_key_metrics()
        
        # Identify issues
        issues = self._identify_issues()
        
        # Generate recommendations
        recommendations = self._generate_recommendations(issues)
        
        # Create gap analysis
        gap_analysis = self._build_gap_analysis()
        
        return DetailedAnalysis(
            executive_summary=exec_summary,
            key_metrics=key_metrics,
            issues=issues,
            recommendations=recommendations,
            gap_analysis=gap_analysis,
            source_report=self.report
        )
    
    def _build_executive_summary(self) -> ExecutiveSummary:
        """Build executive summary section"""
        
        # Use MetricNormalizer for robust metric retrieval with fallbacks
        total_requests = self._get_metric("total_requests")
        failed_requests = self._get_metric("failed_requests")
        failure_rate = self._get_metric("failure_rate")
        p95 = self._get_metric("http_duration_p95")
        
        # Determine overall status
        test_status = "PASS"
        if failure_rate > 5 or p95 > 5000:
            test_status = "FAILED"
        elif failure_rate > 1 or p95 > 2000:
            test_status = "WARNING"
        
        # Extract test metadata
        test_date = self.report.metadata.get("test_date") or self.report.metadata.get("timestamp")
        duration = self.report.metadata.get("duration") or self.report.metadata.get("test_duration")
        
        # Generate key findings
        key_findings = []
        
        if total_requests > 0:
            key_findings.append(
                f"Total Requests: {int(total_requests):,}; "
                f"Failed: {int(failed_requests)} → {failure_rate:.2f}% failure rate"
            )
        
        if p95 > 0:
            status_text = "FAILED" if p95 > 5000 else ("WARNING" if p95 > 2000 else "PASS")
            key_findings.append(f"P95 response time: {p95:.2f} ms → {status_text}")
        
        # Identify critical issue
        critical_issue = None
        if failure_rate > 5:
            critical_issue = f"High failure rate ({failure_rate:.2f}%) indicates systemic reliability issues"
        elif p95 > 10000:
            critical_issue = f"Extreme P95 latency ({p95:.2f}ms) - severe performance degradation under load"
        
        return ExecutiveSummary(
            test_type=self.test_type.title() + " Test",
            test_date=test_date,
            duration=duration,
            test_status=test_status,
            source_file=self.source_file,
            key_findings=key_findings,
            critical_issue=critical_issue
        )
    
    def _build_key_metrics(self) -> KeyMetrics:
        """Organize metrics into structured categories"""
        
        # Request Statistics
        request_stats = RequestStatistics()
        
        if "total_requests" in self.metrics_dict:
            value = self.metrics_dict["total_requests"]
            status = self.thresholds.evaluate_metric("total_requests", value)
            request_stats.total_requests = MetricWithStatus(
                name="Total Requests",
                value=value,
                unit="count",
                status=status if status != MetricStatus.INFO else MetricStatus.PASS
            )
        
        if "failed_requests" in self.metrics_dict:
            value = self.metrics_dict["failed_requests"]
            total = self.metrics_dict.get("total_requests", 1)
            percentage = (value / total * 100) if total > 0 else 0
            status = MetricStatus.FAIL if percentage > 5 else (MetricStatus.WARNING if percentage > 1 else MetricStatus.PASS)
            request_stats.failed_requests = MetricWithStatus(
                name="Failed Requests",
                value=value,
                unit=f"count ({percentage:.2f}%)",
                status=status,
                notes="Above 1% target" if percentage > 1 else "Within acceptable limits"
            )
        
        if "failure_rate" in self.metrics_dict:
            value = self.metrics_dict["failure_rate"]
            status = self.thresholds.evaluate_metric("failure_rate", value)
            target_val = 1.0
            request_stats.success_rate = MetricWithStatus(
                name="Success Rate",
                value=100 - value,
                unit="%",
                status=status,
                target=99.0,
                target_unit="%"
            )
        
        # Response Time Analysis
        response_analysis = ResponseTimeAnalysis()
        
        for metric_key, attr_name in [
            ("http_duration_avg", "avg"),
            ("http_duration_median", "median"),
            ("http_duration_p90", "p90"),
            ("http_duration_p95", "p95"),
            ("http_duration_p99", "p99"),
            ("http_duration_max", "max"),
            ("http_duration_min", "min")
        ]:
            # Also try without http_duration prefix
            value = self.metrics_dict.get(metric_key) or self.metrics_dict.get(attr_name.replace("avg", "average"))
            
            if value is not None:
                status = self.thresholds.evaluate_metric(metric_key, value)
                target = None
                if attr_name in ["p95", "p99", "avg"]:
                    target_info = get_target(f"{attr_name}_response_time")
                    target = target_info["value"] if target_info else None
                
                notes = ""
                if status == MetricStatus.FAIL:
                    notes = "CRITICAL - Exceeds acceptable threshold"
                elif status == MetricStatus.WARNING:
                    notes = "Above target - optimization recommended"
                
                metric_obj = MetricWithStatus(
                    name=f"http_req_duration ({attr_name})",
                    value=value,
                    unit="ms",
                    status=status,
                    target=target,
                    target_unit="ms",
                    notes=notes
                )
                setattr(response_analysis, attr_name, metric_obj)
        
        # Load Profile
        load_profile = LoadProfile()
        
        # Try to extract VU information
        min_vus = self.report.metadata.get("min_vus") or self.metrics_dict.get("min_vus")
        max_vus = self.report.metadata.get("max_vus") or self.metrics_dict.get("max_vus")
        iterations = self.metrics_dict.get("iterations") or self.metrics_dict.get("total_requests")
        rps = self.metrics_dict.get("rps") or self.metrics_dict.get("throughput") or self.metrics_dict.get("requests_per_sec")
        
        load_profile.min_vus = int(min_vus) if min_vus else None
        load_profile.max_vus = int(max_vus) if max_vus else None
        load_profile.iterations = int(iterations) if iterations else None
        load_profile.rps = float(rps) if rps else None
        
        return KeyMetrics(
            request_statistics=request_stats,
            response_time_analysis=response_analysis,
            load_profile=load_profile
        )
    
    def _identify_issues(self) -> IssueList:
        """Identify and categorize issues"""
        
        issues = IssueList()
        
        # === CRITICAL ISSUES ===
        
        # Issue: Extreme Latency
        p95 = self.metrics_dict.get("http_duration_p95") or self.metrics_dict.get("p95")
        median = self.metrics_dict.get("http_duration_median") or self.metrics_dict.get("median")
        max_latency = self.metrics_dict.get("http_duration_max") or self.metrics_dict.get("max")
        
        if p95 and p95 > 10000:  # > 10 seconds
            self.issue_counter += 1
            issues.critical.append(Issue(
                id=self.issue_counter,
                title="Extreme Latency Under Load",
                category=IssueCategory.CRITICAL,
                details=f"P95 {p95:.2f} ms" + (f", median {median:.2f} ms" if median else "") + (f", max {max_latency:.2f} ms" if max_latency else ""),
                impact="Unacceptable user experience; likely to cause client timeouts, retries, and cascading backlog",
                likely_causes=[
                    "Database query performance issues (missing indexes, N+1 queries, heavy joins)",
                    "Resource contention under high concurrency",
                    "Connection pool exhaustion",
                    "Synchronous blocking operations",
                    "Memory pressure or GC pauses"
                ],
                affected_metrics=["p95", "p99", "max_latency"],
                citations=[self.source_file]
            ))
        elif p95 and p95 > 5000:  # > 5 seconds
            self.issue_counter += 1
            issues.high.append(Issue(
                id=self.issue_counter,
                title="High P95 Latency",
                category=IssueCategory.HIGH,
                details=f"P95 response time is {p95:.2f} ms, significantly above 500ms target",
                impact="Poor user experience for 5% of requests; may cause timeout errors in client applications",
                likely_causes=[
                    "Backend processing bottlenecks",
                    "Inefficient database queries",
                    "Insufficient caching",
                    "Resource saturation at high load"
                ],
                affected_metrics=["p95"],
                citations=[self.source_file]
            ))
        
        # Issue: Request Failures
        failure_rate = self.metrics_dict.get("failure_rate", 0)
        failed_requests = self.metrics_dict.get("failed_requests", 0)
        total_requests = self.metrics_dict.get("total_requests", 0)
        
        if failure_rate > 5:
            self.issue_counter += 1
            issues.critical.append(Issue(
                id=self.issue_counter,
                title="High Request Failure Rate",
                category=IssueCategory.CRITICAL,
                details=f"{int(failed_requests)} failed requests ({failure_rate:.2f}%) out of {int(total_requests)} total",
                impact="Significant service disruption; users experiencing frequent errors",
                likely_causes=[
                    "Service timeouts under load",
                    "Connection pool exhaustion",
                    "Resource throttling or rate limiting",
                    "Application errors triggered by slow dependencies",
                    "Infrastructure capacity limits exceeded"
                ],
                affected_metrics=["failure_rate", "failed_requests"],
                citations=[self.source_file]
            ))
        elif failure_rate > 1:
            self.issue_counter += 1
            issues.high.append(Issue(
                id=self.issue_counter,
                title="Elevated Request Failure Rate",
                category=IssueCategory.HIGH,
                details=f"Failure rate at {failure_rate:.2f}% is above the recommended threshold of 1%",
                impact="Intermittent service issues affecting user trust and reliability metrics",
                likely_causes=[
                    "Occasional timeouts",
                    "Resource contention",
                    "Transient infrastructure issues"
                ],
                affected_metrics=["failure_rate"],
                citations=[self.source_file]
            ))
        
        # === HIGH ISSUES ===
        
        # Issue: Latency Distribution Skew
        avg = self.metrics_dict.get("http_duration_avg") or self.metrics_dict.get("avg")
        if avg and median and abs(avg - median) > 1000:
            self.issue_counter += 1
            issues.high.append(Issue(
                id=self.issue_counter,
                title="Significant Latency Distribution Skew",
                category=IssueCategory.HIGH,
                details=f"Average ({avg:.0f}ms) significantly higher than median ({median:.0f}ms) - difference of {abs(avg-median):.0f}ms",
                impact="Indicates highly variable performance with some very slow outliers pulling up the average",
                likely_causes=[
                    "Periodic background tasks interfering with request handling",
                    "Cache misses for certain data patterns",
                    "Resource contention spikes",
                    "Garbage collection pauses"
                ],
                affected_metrics=["avg", "median"],
                citations=[self.source_file]
            ))
        
        # === MODERATE ISSUES ===
        
        # Issue: Throughput concerns
        rps = self.metrics_dict.get("rps") or self.metrics_dict.get("throughput")
        if rps and rps < 5:
            self.issue_counter += 1
            issues.moderate.append(Issue(
                id=self.issue_counter,
                title="Low Throughput",
                category=IssueCategory.MODERATE,
                details=f"System handling only {rps:.2f} requests/second",
                impact="Limited capacity to handle concurrent users; may not scale to production load",
                likely_causes=[
                    "Sequential processing limiting parallelism",
                    "Synchronous I/O operations",
                    "Insufficient worker threads/processes",
                    "Resource constraints (CPU, memory, network)"
                ],
                affected_metrics=["throughput", "rps"],
                citations=[self.source_file]
            ))
        
        # === WARNINGS ===
        
        # Check for receiving time variability (if available)
        receiving_max = self.metrics_dict.get("http_req_receiving_max")
        receiving_median = self.metrics_dict.get("http_req_receiving_median")
        
        if receiving_max and receiving_median and receiving_max > 1000 and receiving_median < 10:
            self.issue_counter += 1
            issues.warnings.append(Issue(
                id=self.issue_counter,
                title="High Response Receiving Time Variability",
                category=IssueCategory.WARNING,
                details=f"http_req_receiving shows max of {receiving_max:.2f}ms while median is {receiving_median:.2f}ms",
                impact="Occasional slow payload transfer suggesting queued responses or saturated workers",
                likely_causes=[
                    "Network congestion",
                    "Server's send buffer saturation",
                    "Load balancer queuing",
                    "Response size variability"
                ],
                affected_metrics=["http_req_receiving"],
                citations=[self.source_file]
            ))
        
        return issues
    
    def _generate_recommendations(self, issues: IssueList) -> List[Recommendation]:
        """Generate actionable recommendations based on issues"""
        
        recommendations = []
        
        # === IMMEDIATE DIAGNOSTICS ===
        if issues.critical or issues.high:
            recommendations.append(Recommendation(
                category="Immediate Diagnostics",
                title="Enable detailed tracing and profiling",
                details=(
                    "Trace the slowest requests during high-load periods. "
                    "Correlate application spans to database query plans, identify N+1 patterns, "
                    "heavy joins, or slow remote calls. The dominance of waiting time indicates "
                    "backend contention rather than client/network issues."
                ),
                priority=1,
                related_issues=[i.id for i in issues.critical + issues.high if "latency" in i.title.lower()]
            ))
            
            recommendations.append(Recommendation(
                category="Immediate Diagnostics",
                title="Review connection pools and timeouts",
                details=(
                    "Right-size database and HTTP connection pools. Verify queue depths and "
                    "thread/worker backlogs during stress to avoid head-of-line blocking and "
                    "cascading delays. Check for connection leak patterns."
                ),
                priority=1,
                related_issues=[i.id for i in issues.critical + issues.high]
            ))
        
        # === TARGETED OPTIMIZATIONS ===
        
        # Database optimization
        if any("latency" in i.title.lower() or "slow" in i.details.lower() for i in issues.critical + issues.high):
            recommendations.append(Recommendation(
                category="Targeted Optimizations",
                title="Database query optimization",
                details=(
                    "Add or adjust indexes for frequently accessed paths. Validate that query "
                    "cardinality and sort/group operations are properly indexed. Review execution "
                    "plans for table scans vs. index seeks. Consider query result caching for "
                    "hot data patterns."
                ),
                priority=1,
                related_issues=[i.id for i in issues.all_issues() if "latency" in i.title.lower()]
            ))
        
        # Application-level optimization
        recommendations.append(Recommendation(
            category="Targeted Optimizations",
            title="Application-level performance improvements",
            details=(
                "Remove synchronous fan-out calls; make expensive lookups async/parallel where safe. "
                "Introduce response-level caching for repeated lookups. Consider payload optimization "
                "(partial fields, pagination) to reduce processing and transfer time."
            ),
            priority=2,
            related_issues=[i.id for i in issues.high + issues.moderate]
        ))
        
        # Infrastructure scaling
        if any("throughput" in i.title.lower() or "capacity" in i.details.lower() for i in issues.all_issues()):
            recommendations.append(Recommendation(
                category="Targeted Optimizations",
                title="Infrastructure capacity planning",
                details=(
                    "Consider horizontal autoscaling at the worker tier. Ensure CPU and memory "
                    "headroom and check for container throttling during load plateaus. Verify "
                    "load balancer configuration for even distribution."
                ),
                priority=2,
                related_issues=[i.id for i in issues.moderate]
            ))
        
        # === NEXT TEST ITERATION ===
        recommendations.append(Recommendation(
            category="Next Test Iteration",
            title="Stage-annotated load testing",
            details=(
                "Create a staged test script (e.g., 20 → 40 → 80 → 120 VUs with sustained holds). "
                "Add per-stage thresholds and tags to capture the exact VU level where SLOs break "
                "(first P95 > 500ms; first error rate > 1%). Use dashboard overlays to visualize "
                "p50/p95/p99 trends across load stages."
            ),
            priority=3,
            related_issues=[]
        ))
        
        recommendations.append(Recommendation(
            category="Next Test Iteration",
            title="Validate improvements with baseline comparison",
            details=(
                "After implementing fixes, re-run the same test profile to validate improvements. "
                "Compare key metrics (P95, failure rate, throughput) against this baseline. "
                "Document changes and performance improvements for tracking."
            ),
            priority=3,
            related_issues=[]
        ))
        
        return recommendations
    
    def _build_gap_analysis(self) -> List[GapAnalysis]:
        """Build gap analysis comparing current vs targets"""
        
        gaps = []
        
        # Key metrics to analyze
        metrics_to_check = [
            ("http_duration_p95", "p95", "P95 Response Time"),
            ("http_duration_p99", "p99", "P99 Response Time"),
            ("http_duration_avg", "avg", "Avg Response Time"),
            ("failure_rate", "failure_rate", "Error Rate"),
        ]
        
        for metric_key, target_key, display_name in metrics_to_check:
            value = self.metrics_dict.get(metric_key)
            if value is None:
                continue
            
            target_info = get_target(f"{target_key}_response_time") or get_target(target_key)
            if not target_info:
                continue
            
            target = target_info["value"]
            unit = target_info["unit"]
            
            # Calculate gap
            if "rate" in metric_key.lower():
                # For rates, lower is better
                gap_pct = ((value - target) / target) * 100 if target > 0 else 0
                required = f"Reduce by {abs(gap_pct):.1f}%" if gap_pct > 0 else "Target met"
            else:
                # For latency, lower is better
                gap_pct = ((value - target) / target) * 100 if target > 0 else 0
                required = f"Reduce by {abs(gap_pct):.1f}%" if gap_pct > 0 else "Target met"
            
            if gap_pct > 0:  # Only show gaps that need improvement
                gaps.append(GapAnalysis(
                    metric=display_name,
                    current=value,
                    target=target,
                    unit=unit,
                    gap_percentage=gap_pct,
                    required_improvement=required
                ))
        
        return gaps


def generate_detailed_analysis(
    report: UniversalReport,
    test_type: str = "default",
    source_file: str = ""
) -> DetailedAnalysis:
    """
    Main entry point for generating detailed analysis
    
    Args:
        report: UniversalReport with extracted metrics
        test_type: Type of test (smoke, load, stress, etc.)
        source_file: Source filename for citations
    
    Returns:
        DetailedAnalysis with comprehensive structured insights
    """
    analyzer = DetailedAnalyzer(report, test_type, source_file)
    return analyzer.analyze()
