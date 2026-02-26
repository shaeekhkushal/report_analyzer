from core.models import UniversalReport, TestSummary
from core.metric_normalizer import MetricNormalizer

def interpret(report):
    """Generate insights from report (supports both UniversalReport and TestSummary for backward compatibility)"""
    
    insights = []
    
    # Handle UniversalReport format
    if isinstance(report, UniversalReport):
        return _interpret_universal(report)
    
    # Handle legacy TestSummary format
    if isinstance(report, TestSummary):
        return _interpret_test_summary(report)
    
    return insights

def _interpret_universal(report: UniversalReport) -> list:
    """Generate detailed, descriptive insights from UniversalReport metrics"""
    insights = []
    
    # Convert metrics to dict for easy access
    metrics_dict = {m.name: m for m in report.all_metrics()}
    
    # Use MetricNormalizer for robust metric retrieval with fallbacks
    get_metric = lambda name, default=None: MetricNormalizer.get_metric_value(metrics_dict, name, default if default is not None else 0.0)
    
    # ====== RELIABILITY ANALYSIS ======
    failure_rate = get_metric("failure_rate")
    failed_requests = get_metric("failed_requests")
    total_requests = get_metric("total_requests")
    
    if failure_rate > 0 or failed_requests > 0:
        if failure_rate > 5:
            insights.append(f"CRITICAL RELIABILITY ISSUE: Failure rate is {failure_rate:.2f}% - {failed_requests:.0f} requests failed out of {total_requests:.0f} total. This indicates systemic issues in the application.")
        elif failure_rate > 1:
            insights.append(f"MODERATE RELIABILITY CONCERN: Failure rate at {failure_rate:.2f}% is above the recommended threshold of 1%. Investigate root causes to improve stability.")
        elif total_requests > 0:
            insights.append(f"HEALTHY RELIABILITY: Failure rate is {failure_rate:.2f}% - well within acceptable limits. System is stable and dependable.")
    
    # ====== LATENCY & RESPONSE TIME ANALYSIS ======
    p95_latency = get_metric("http_duration_p95")
    p99_latency = get_metric("http_duration_p99")
    avg_latency = get_metric("http_duration_avg")
    median_latency = get_metric("http_duration_median")
    min_latency = get_metric("http_duration_min")
    max_latency = get_metric("http_duration_max")
    p90_latency = get_metric("http_duration_p90")
    
    # Detailed latency assessment
    if avg_latency is not None and median_latency is not None:
        latency_skew = avg_latency - median_latency
        if abs(latency_skew) > 200:
            insights.append(f"LATENCY DISTRIBUTION: Average response time ({avg_latency:.0f}ms) is significantly higher than median ({median_latency:.0f}ms). This suggests occasional slow requests pulling up the average.")
        else:
            insights.append(f"LATENCY DISTRIBUTION: Response times are fairly consistent. Average is {avg_latency:.0f}ms with median at {median_latency:.0f}ms.")
    
    # P95 latency evaluation
    if p95_latency is not None:
        if p95_latency > 2000:
            insights.append(f"HIGH P95 LATENCY: 95% of requests exceed {p95_latency:.0f}ms. Users will experience noticeable delays. Consider optimizations.")
        elif p95_latency > 1000:
            insights.append(f"ELEVATED P95 LATENCY: P95 response time is {p95_latency:.0f}ms. While acceptable for some use cases, investigate for improvement opportunities.")
        else:
            insights.append(f"GOOD P95 LATENCY: P95 at {p95_latency:.0f}ms indicates responsive performance for the majority of requests.")
    
    # P99 tail latency (critical for user experience)
    if p99_latency is not None:
        if p99_latency > 5000:
            insights.append(f"SEVERE TAIL LATENCY: 1% of users experience response times exceeding {p99_latency:.0f}ms. This significantly impacts user experience.")
        elif p99_latency > 3000:
            insights.append(f"CONCERNING TAIL LATENCY: P99 at {p99_latency:.0f}ms. Some users will experience slow responses - consider investigating bottlenecks.")
    
    # ====== EXTREME VALUES & OUTLIERS ======
    if max_latency is not None and p95_latency is not None:
        outlier_ratio = max_latency / p95_latency if p95_latency > 0 else 0
        if max_latency > 10000:
            insights.append(f"EXTREME RESPONSE TIMES: Maximum latency of {max_latency:.0f}ms detected. Investigate for timeout events, database locks, or resource exhaustion.")
        elif outlier_ratio > 5:
            insights.append(f"SIGNIFICANT OUTLIERS: Maximum response time ({max_latency:.0f}ms) is {outlier_ratio:.1f}x the P95 ({p95_latency:.0f}ms). Some requests are experiencing severe delays.")
        else:
            if max_latency > 2000:
                insights.append(f"ACCEPTABLE OUTLIERS: Maximum response time ({max_latency:.0f}ms) is {outlier_ratio:.1f}x the P95 ({p95_latency:.0f}ms). Shows some variability but generally reasonable.")
    
    # ====== THROUGHPUT ANALYSIS ======
    throughput = get_metric("throughput")
    
    if throughput > 0:
        if throughput < 1:
            insights.append(f"LOW THROUGHPUT: System is handling less than 1 request/sec. Verify load test configuration and system capacity.")
        elif throughput < 10:
            insights.append(f"LIGHT LOAD: Throughput at {throughput:.1f} requests/sec suggests low-scale load testing.")
        elif throughput > 100:
            insights.append(f"HIGH THROUGHPUT: System is processing {throughput:.1f} requests/sec - good capacity under test load.")
        else:
            insights.append(f"STEADY THROUGHPUT: System maintains {throughput:.1f} requests/sec - consistent performance.")
    
    # ====== COMPREHENSIVE SUMMARY ======
    # If no specific insights were generated
    if not insights:
        insights.append("Analysis complete. No critical performance issues detected.")
    
    return insights

def _interpret_test_summary(summary: TestSummary) -> list:
    """Generate detailed insights from TestSummary metrics"""
    insights = []

    # ====== RELIABILITY ANALYSIS ======
    if summary.failure_rate > 5:
        insights.append(f"CRITICAL RELIABILITY ISSUE: Failure rate is {summary.failure_rate:.2f}%. This indicates systemic issues in the application that require immediate attention.")
    elif summary.failure_rate > 1:
        insights.append(f"MODERATE RELIABILITY CONCERN: Failure rate at {summary.failure_rate:.2f}% is above recommended threshold. Investigate and improve stability.")
    else:
        insights.append(f"HEALTHY RELIABILITY: Failure rate is {summary.failure_rate:.2f}% - system is stable and dependable.")

    # ====== LATENCY ANALYSIS ======
    avg_time = summary.http_duration.avg
    median_time = summary.http_duration.med
    p95_time = summary.http_duration.p95
    p90_time = summary.http_duration.p90
    max_time = summary.http_duration.max
    
    # Latency distribution analysis
    if abs(avg_time - median_time) > 200:
        insights.append(f"LATENCY DISTRIBUTION: Average ({avg_time:.0f}ms) is higher than median ({median_time:.0f}ms), indicating some slow outliers.")
    else:
        insights.append(f"LATENCY DISTRIBUTION: Response times are consistent. Average and median are closely aligned (~{avg_time:.0f}ms).")
    
    # Average latency evaluation
    if avg_time > 1000:
        insights.append(f"HIGH AVERAGE LATENCY: Mean response time is {avg_time:.0f}ms. Users will perceive noticeable delays.")
    elif avg_time > 500:
        insights.append(f"MODERATE LATENCY: Average response time is {avg_time:.0f}ms. There's room for optimization.")
    else:
        insights.append(f"GOOD AVERAGE LATENCY: Mean response time is {avg_time:.0f}ms - responsive performance.")
    
    # P95 evaluation
    if p95_time > 2000:
        insights.append(f"HIGH P95 LATENCY: 95% of requests exceed {p95_time:.0f}ms. Critical optimization needed.")
    elif p95_time > 1000:
        insights.append(f"ELEVATED P95 LATENCY: P95 is {p95_time:.0f}ms. Consider investigating performance bottlenecks.")
    else:
        insights.append(f"GOOD P95 LATENCY: P95 at {p95_time:.0f}ms indicates responsive performance.")
    
    # P90 tail latency
    if p90_time > 5000:
        insights.append(f"SEVERE TAIL LATENCY: 10% of requests experience {p90_time:.0f}ms+ responses. Significant impact on user experience.")
    elif p90_time > 3000:
        insights.append(f"CONCERNING TAIL LATENCY: P90 at {p90_time:.0f}ms - some users experience noticeable delays.")

    # ====== OUTLIERS & EXTREME VALUES ======
    outlier_ratio = max_time / p95_time if p95_time > 0 else 0
    if max_time > 10000:
        insights.append(f"EXTREME DELAYS: Maximum response time {max_time:.0f}ms detected. Investigate timeout events and resource bottlenecks.")
    elif outlier_ratio > 5:
        insights.append(f"SIGNIFICANT OUTLIERS: Max time ({max_time:.0f}ms) is {outlier_ratio:.1f}x P95 ({p95_time:.0f}ms). Some requests experiencing severe delays.")
    else:
        if max_time > 2000:
            insights.append(f"ACCEPTABLE VARIATION: Maximum {max_time:.0f}ms is {outlier_ratio:.1f}x P95 - reasonable outlier range.")

    return insights if insights else ["Analysis complete. No critical issues detected."]
