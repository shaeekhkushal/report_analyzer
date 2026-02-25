"""
Output formatters for DetailedAnalysis
Supports multiple output formats: text, HTML, markdown, JSON
"""

from typing import List
from core.models import (
    DetailedAnalysis, Issue, Recommendation, MetricWithStatus,
    IssueCategory, MetricStatus
)


class TextFormatter:
    """Plain text formatter for console output"""
    
    @staticmethod
    def format(analysis: DetailedAnalysis) -> str:
        """Format analysis as plain text"""
        lines = []
        
        # Header
        lines.append("=" * 80)
        lines.append(f"{analysis.executive_summary.test_type.upper()} RESULTS REPORT")
        lines.append("=" * 80)
        
        # Executive Summary
        lines.append("\nEXECUTIVE SUMMARY")
        lines.append("-" * 80)
        summary = analysis.executive_summary
        
        if summary.test_date:
            lines.append(f"Test Date: {summary.test_date}")
        if summary.duration:
            lines.append(f"Duration: {summary.duration}")
        lines.append(f"Test Status: {summary.test_status}")
        if summary.source_file:
            lines.append(f"Source: {summary.source_file}")
        
        lines.append("\nKey Findings:")
        for finding in summary.key_findings:
            lines.append(f"  • {finding}")
        
        if summary.critical_issue:
            lines.append(f"\n⚠️  CRITICAL: {summary.critical_issue}")
        
        # Key Metrics
        lines.append("\n" + "=" * 80)
        lines.append("KEY PERFORMANCE METRICS")
        lines.append("=" * 80)
        
        # Request Statistics
        req_stats = analysis.key_metrics.request_statistics
        if any([req_stats.total_requests, req_stats.failed_requests, req_stats.success_rate]):
            lines.append("\n1. REQUEST STATISTICS")
            lines.append("-" * 40)
            
            if req_stats.total_requests:
                lines.append(TextFormatter._format_metric(req_stats.total_requests))
            if req_stats.failed_requests:
                lines.append(TextFormatter._format_metric(req_stats.failed_requests))
            if req_stats.success_rate:
                lines.append(TextFormatter._format_metric(req_stats.success_rate))
        
        # Response Time Analysis
        resp = analysis.key_metrics.response_time_analysis
        if any([resp.avg, resp.median, resp.p90, resp.p95, resp.p99, resp.max]):
            lines.append("\n2. RESPONSE TIME ANALYSIS")
            lines.append("-" * 40)
            
            for metric in [resp.avg, resp.median, resp.p90, resp.p95, resp.p99, resp.max]:
                if metric:
                    lines.append(TextFormatter._format_metric(metric))
        
        # Load Profile
        load = analysis.key_metrics.load_profile
        if any([load.min_vus, load.max_vus, load.iterations, load.rps]):
            lines.append("\n3. LOAD PROFILE")
            lines.append("-" * 40)
            if load.min_vus:
                lines.append(f"  Min VUs: {load.min_vus}")
            if load.max_vus:
                lines.append(f"  Max VUs: {load.max_vus}")
            if load.iterations:
                lines.append(f"  Total Iterations: {load.iterations:,}")
            if load.rps:
                lines.append(f"  Requests/sec: {load.rps:.2f}")
        
        # Issues
        if analysis.issues.total_count() > 0:
            lines.append("\n" + "=" * 80)
            lines.append("IDENTIFIED ISSUES")
            lines.append("=" * 80)
            
            if analysis.issues.critical:
                lines.append("\nCRITICAL ISSUES")
                lines.append("-" * 40)
                for issue in analysis.issues.critical:
                    lines.append(TextFormatter._format_issue(issue))
            
            if analysis.issues.high:
                lines.append("\nHIGH PRIORITY ISSUES")
                lines.append("-" * 40)
                for issue in analysis.issues.high:
                    lines.append(TextFormatter._format_issue(issue))
            
            if analysis.issues.moderate:
                lines.append("\nMODERATE ISSUES")
                lines.append("-" * 40)
                for issue in analysis.issues.moderate:
                    lines.append(TextFormatter._format_issue(issue))
            
            if analysis.issues.warnings:
                lines.append("\nWARNINGS")
                lines.append("-" * 40)
                for issue in analysis.issues.warnings:
                    lines.append(TextFormatter._format_issue(issue))
        
        # Recommendations
        if analysis.recommendations:
            lines.append("\n" + "=" * 80)
            lines.append("RECOMMENDATIONS")
            lines.append("=" * 80)
            
            # Group by category
            categories = {}
            for rec in analysis.recommendations:
                if rec.category not in categories:
                    categories[rec.category] = []
                categories[rec.category].append(rec)
            
            for category, recs in categories.items():
                lines.append(f"\n{category.upper()}")
                lines.append("-" * 40)
                for rec in recs:
                    lines.append(f"\n• {rec.title}")
                    lines.append(f"  {rec.details}")
        
        # Gap Analysis
        if analysis.gap_analysis:
            lines.append("\n" + "=" * 80)
            lines.append("PERFORMANCE GAP ANALYSIS")
            lines.append("=" * 80)
            lines.append(f"\n{'Metric':<25} {'Current':<15} {'Target':<15} {'Gap':<15}")
            lines.append("-" * 70)
            
            for gap in analysis.gap_analysis:
                current_str = f"{gap.current:.2f}{gap.unit}"
                target_str = f"{gap.target:.2f}{gap.unit}"
                gap_str = f"+{gap.gap_percentage:.1f}%" if gap.gap_percentage > 0 else f"{gap.gap_percentage:.1f}%"
                lines.append(f"{gap.metric:<25} {current_str:<15} {target_str:<15} {gap_str:<15}")
        
        lines.append("\n" + "=" * 80)
        
        return "\n".join(lines)
    
    @staticmethod
    def _format_metric(metric: MetricWithStatus) -> str:
        """Format a single metric with status"""
        icon = metric.status_icon()
        value_str = metric.formatted_value()
        
        line = f"  {icon} {metric.name}: {value_str}"
        
        if metric.target:
            line += f" (target: {metric.target}{metric.target_unit or metric.unit})"
        
        if metric.notes:
            line += f" - {metric.notes}"
        
        return line
    
    @staticmethod
    def _format_issue(issue: Issue) -> str:
        """Format a single issue"""
        lines = [
            f"\nIssue #{issue.id}: {issue.title}",
            f"Severity: {issue.severity_label()}",
            f"Details: {issue.details}",
            f"Impact: {issue.impact}"
        ]
        
        if issue.likely_causes:
            lines.append("Likely Causes:")
            for cause in issue.likely_causes:
                lines.append(f"  • {cause}")
        
        return "\n".join(lines)


class MarkdownFormatter:
    """Markdown formatter for documentation and reports"""
    
    @staticmethod
    def format(analysis: DetailedAnalysis) -> str:
        """Format analysis as markdown"""
        lines = []
        
        # Title
        lines.append(f"# {analysis.executive_summary.test_type.upper()} RESULTS REPORT\n")
        
        # Executive Summary
        lines.append("## EXECUTIVE SUMMARY\n")
        summary = analysis.executive_summary
        
        lines.append(f"**Test Type:** {summary.test_type}  ")
        if summary.test_date:
            lines.append(f"**Test Date:** {summary.test_date}  ")
        if summary.duration:
            lines.append(f"**Duration:** {summary.duration}  ")
        lines.append(f"**Test Status:** {summary.test_status}  ")
        if summary.source_file:
            lines.append(f"**Source:** {summary.source_file}  ")
        
        if summary.key_findings:
            lines.append("\n**Key Findings:**\n")
            for finding in summary.key_findings:
                lines.append(f"- {finding}")
        
        if summary.critical_issue:
            lines.append(f"\n> ⚠️ **CRITICAL:** {summary.critical_issue}\n")
        
        # Key Metrics
        lines.append("\n## KEY PERFORMANCE METRICS\n")
        
        # Request Statistics
        req_stats = analysis.key_metrics.request_statistics
        if any([req_stats.total_requests, req_stats.failed_requests, req_stats.success_rate]):
            lines.append("### 1. Request Statistics\n")
            lines.append("| Metric | Value | Status | Notes |")
            lines.append("|--------|-------|--------|-------|")
            
            for metric in [req_stats.total_requests, req_stats.failed_requests, req_stats.success_rate]:
                if metric:
                    lines.append(MarkdownFormatter._format_metric_row(metric))
        
        # Response Time Analysis
        resp = analysis.key_metrics.response_time_analysis
        if any([resp.avg, resp.median, resp.p90, resp.p95, resp.p99, resp.max]):
            lines.append("\n### 2. Response Time Analysis\n")
            lines.append("| Metric | Value | Target | Status | Notes |")
            lines.append("|--------|-------|--------|--------|-------|")
            
            for metric in [resp.avg, resp.median, resp.p90, resp.p95, resp.p99, resp.max]:
                if metric:
                    lines.append(MarkdownFormatter._format_metric_row(metric, include_target=True))
        
        # Load Profile
        load = analysis.key_metrics.load_profile
        if any([load.min_vus, load.max_vus, load.iterations, load.rps]):
            lines.append("\n### 3. Load Profile\n")
            if load.min_vus:
                lines.append(f"- **Min VUs:** {load.min_vus}")
            if load.max_vus:
                lines.append(f"- **Max VUs:** {load.max_vus}")
            if load.iterations:
                lines.append(f"- **Total Iterations:** {load.iterations:,}")
            if load.rps:
                lines.append(f"- **Requests/sec:** {load.rps:.2f}")
        
        # Issues
        if analysis.issues.total_count() > 0:
            lines.append("\n## IDENTIFIED ISSUES\n")
            
            if analysis.issues.critical:
                lines.append("### 🔴 CRITICAL ISSUES\n")
                for issue in analysis.issues.critical:
                    lines.append(MarkdownFormatter._format_issue(issue))
            
            if analysis.issues.high:
                lines.append("\n### 🟠 HIGH PRIORITY ISSUES\n")
                for issue in analysis.issues.high:
                    lines.append(MarkdownFormatter._format_issue(issue))
            
            if analysis.issues.moderate:
                lines.append("\n### 🟡 MODERATE ISSUES\n")
                for issue in analysis.issues.moderate:
                    lines.append(MarkdownFormatter._format_issue(issue))
            
            if analysis.issues.warnings:
                lines.append("\n### ⚠️ WARNINGS\n")
                for issue in analysis.issues.warnings:
                    lines.append(MarkdownFormatter._format_issue(issue))
        
        # Recommendations
        if analysis.recommendations:
            lines.append("\n## RECOMMENDATIONS\n")
            
            categories = {}
            for rec in analysis.recommendations:
                if rec.category not in categories:
                    categories[rec.category] = []
                categories[rec.category].append(rec)
            
            for category, recs in categories.items():
                lines.append(f"\n### {category}\n")
                for rec in recs:
                    lines.append(f"#### {rec.title}\n")
                    lines.append(f"{rec.details}\n")
        
        # Gap Analysis
        if analysis.gap_analysis:
            lines.append("\n## PERFORMANCE GAP ANALYSIS\n")
            lines.append("| Metric | Current | Target | Gap | Required Improvement |")
            lines.append("|--------|---------|--------|-----|---------------------|")
            
            for gap in analysis.gap_analysis:
                current = f"{gap.current:.2f}{gap.unit}"
                target = f"{gap.target:.2f}{gap.unit}"
                gap_str = f"+{gap.gap_percentage:.1f}%"
                lines.append(f"| {gap.metric} | {current} | {target} | {gap_str} | {gap.required_improvement} |")
        
        return "\n".join(lines)
    
    @staticmethod
    def _format_metric_row(metric: MetricWithStatus, include_target: bool = False) -> str:
        """Format metric as markdown table row"""
        icon = metric.status_icon()
        value = metric.formatted_value()
        notes = metric.notes or "—"
        
        if include_target and metric.target:
            target_str = f"{metric.target}{metric.target_unit or metric.unit}"
            return f"| {metric.name} | {value} | {target_str} | {icon} | {notes} |"
        else:
            return f"| {metric.name} | {value} | {icon} | {notes} |"
    
    @staticmethod
    def _format_issue(issue: Issue) -> str:
        """Format issue as markdown"""
        lines = [
            f"**Issue #{issue.id}: {issue.title}**\n",
            f"- **Severity:** {issue.severity_label()}",
            f"- **Details:** {issue.details}",
            f"- **Impact:** {issue.impact}"
        ]
        
        if issue.likely_causes:
            lines.append("- **Likely Causes:**")
            for cause in issue.likely_causes:
                lines.append(f"  - {cause}")
        
        lines.append("")  # Empty line after issue
        return "\n".join(lines)


class HTMLFormatter:
    """HTML formatter for web display"""
    
    @staticmethod
    def format(analysis: DetailedAnalysis) -> str:
        """Format analysis as HTML"""
        html = []
        
        # Header
        html.append('<div class="detailed-analysis">')
        html.append(f'<h1>{analysis.executive_summary.test_type} Results Report</h1>')
        
        # Executive Summary
        html.append('<section class="executive-summary">')
        html.append('<h2>Executive Summary</h2>')
        
        summary = analysis.executive_summary
        status_class = summary.test_status.lower().replace(" ", "-")
        
        html.append('<div class="summary-info">')
        html.append(f'<div class="info-item"><strong>Test Type:</strong> {summary.test_type}</div>')
        if summary.test_date:
            html.append(f'<div class="info-item"><strong>Test Date:</strong> {summary.test_date}</div>')
        if summary.duration:
            html.append(f'<div class="info-item"><strong>Duration:</strong> {summary.duration}</div>')
        html.append(f'<div class="info-item"><strong>Status:</strong> <span class="status-badge {status_class}">{summary.test_status}</span></div>')
        html.append('</div>')
        
        if summary.key_findings:
            html.append('<div class="key-findings">')
            html.append('<h3>Key Findings</h3>')
            html.append('<ul>')
            for finding in summary.key_findings:
                html.append(f'<li>{finding}</li>')
            html.append('</ul>')
            html.append('</div>')
        
        if summary.critical_issue:
            html.append(f'<div class="alert alert-critical">⚠️ <strong>CRITICAL:</strong> {summary.critical_issue}</div>')
        
        html.append('</section>')
        
        # Key Metrics
        html.append('<section class="key-metrics">')
        html.append('<h2>Key Performance Metrics</h2>')
        
        # Request Statistics
        req_stats = analysis.key_metrics.request_statistics
        if any([req_stats.total_requests, req_stats.failed_requests, req_stats.success_rate]):
            html.append('<div class="metric-section">')
            html.append('<h3>1. Request Statistics</h3>')
            html.append('<table class="metrics-table">')
            html.append('<thead><tr><th>Metric</th><th>Value</th><th>Status</th><th>Notes</th></tr></thead>')
            html.append('<tbody>')
            
            for metric in [req_stats.total_requests, req_stats.failed_requests, req_stats.success_rate]:
                if metric:
                    html.append(HTMLFormatter._format_metric_row(metric))
            
            html.append('</tbody></table>')
            html.append('</div>')
        
        # Response Time Analysis
        resp = analysis.key_metrics.response_time_analysis
        if any([resp.avg, resp.median, resp.p90, resp.p95, resp.p99, resp.max]):
            html.append('<div class="metric-section">')
            html.append('<h3>2. Response Time Analysis</h3>')
            html.append('<table class="metrics-table">')
            html.append('<thead><tr><th>Metric</th><th>Value</th><th>Target</th><th>Status</th><th>Notes</th></tr></thead>')
            html.append('<tbody>')
            
            for metric in [resp.avg, resp.median, resp.p90, resp.p95, resp.p99, resp.max]:
                if metric:
                    html.append(HTMLFormatter._format_metric_row(metric, include_target=True))
            
            html.append('</tbody></table>')
            html.append('</div>')
        
        # Load Profile
        load = analysis.key_metrics.load_profile
        if any([load.min_vus, load.max_vus, load.iterations, load.rps]):
            html.append('<div class="metric-section">')
            html.append('<h3>3. Load Profile</h3>')
            html.append('<ul class="load-profile">')
            if load.min_vus:
                html.append(f'<li><strong>Min VUs:</strong> {load.min_vus}</li>')
            if load.max_vus:
                html.append(f'<li><strong>Max VUs:</strong> {load.max_vus}</li>')
            if load.iterations:
                html.append(f'<li><strong>Total Iterations:</strong> {load.iterations:,}</li>')
            if load.rps:
                html.append(f'<li><strong>Requests/sec:</strong> {load.rps:.2f}</li>')
            html.append('</ul>')
            html.append('</div>')
        
        html.append('</section>')
        
        # Issues
        if analysis.issues.total_count() > 0:
            html.append('<section class="issues-section">')
            html.append('<h2>Identified Issues</h2>')
            
            issue_groups = [
                ('critical', '🔴 Critical Issues', analysis.issues.critical),
                ('high', '🟠 High Priority Issues', analysis.issues.high),
                ('moderate', '🟡 Moderate Issues', analysis.issues.moderate),
                ('warning', '⚠️ Warnings', analysis.issues.warnings)
            ]
            
            for severity, title, issues in issue_groups:
                if issues:
                    html.append(f'<div class="issue-group {severity}">')
                    html.append(f'<h3>{title}</h3>')
                    for issue in issues:
                        html.append(HTMLFormatter._format_issue(issue))
                    html.append('</div>')
            
            html.append('</section>')
        
        # Recommendations
        if analysis.recommendations:
            html.append('<section class="recommendations-section">')
            html.append('<h2>Recommendations</h2>')
            
            categories = {}
            for rec in analysis.recommendations:
                if rec.category not in categories:
                    categories[rec.category] = []
                categories[rec.category].append(rec)
            
            for category, recs in categories.items():
                html.append(f'<div class="recommendation-category">')
                html.append(f'<h3>{category}</h3>')
                for rec in recs:
                    html.append('<div class="recommendation">')
                    html.append(f'<h4>{rec.title}</h4>')
                    html.append(f'<p>{rec.details}</p>')
                    html.append('</div>')
                html.append('</div>')
            
            html.append('</section>')
        
        # Gap Analysis
        if analysis.gap_analysis:
            html.append('<section class="gap-analysis-section">')
            html.append('<h2>Performance Gap Analysis</h2>')
            html.append('<table class="gap-table">')
            html.append('<thead><tr><th>Metric</th><th>Current</th><th>Target</th><th>Gap</th><th>Required Improvement</th></tr></thead>')
            html.append('<tbody>')
            
            for gap in analysis.gap_analysis:
                current = f"{gap.current:.2f}{gap.unit}"
                target = f"{gap.target:.2f}{gap.unit}"
                gap_str = f"+{gap.gap_percentage:.1f}%"
                html.append(f'<tr>')
                html.append(f'<td>{gap.metric}</td>')
                html.append(f'<td>{current}</td>')
                html.append(f'<td>{target}</td>')
                html.append(f'<td class="gap-negative">{gap_str}</td>')
                html.append(f'<td>{gap.required_improvement}</td>')
                html.append(f'</tr>')
            
            html.append('</tbody></table>')
            html.append('</section>')
        
        html.append('</div>')  # Close .detailed-analysis
        
        return '\n'.join(html)
    
    @staticmethod
    def _format_metric_row(metric: MetricWithStatus, include_target: bool = False) -> str:
        """Format metric as HTML table row"""
        icon = metric.status_icon()
        value = metric.formatted_value()
        status_class = metric.status.value
        notes = metric.notes or '—'
        
        if include_target and metric.target:
            target_str = f"{metric.target}{metric.target_unit or metric.unit}"
            return f'<tr><td>{metric.name}</td><td>{value}</td><td>{target_str}</td><td class="status-{status_class}">{icon}</td><td>{notes}</td></tr>'
        else:
            return f'<tr><td>{metric.name}</td><td>{value}</td><td class="status-{status_class}">{icon}</td><td>{notes}</td></tr>'
    
    @staticmethod
    def _format_issue(issue: Issue) -> str:
        """Format issue as HTML"""
        html = [f'<div class="issue" data-severity="{issue.category.value}">']
        html.append(f'<h4>Issue #{issue.id}: {issue.title}</h4>')
        html.append(f'<p><strong>Severity:</strong> <span class="severity-badge {issue.category.value}">{issue.severity_label()}</span></p>')
        html.append(f'<p><strong>Details:</strong> {issue.details}</p>')
        html.append(f'<p><strong>Impact:</strong> {issue.impact}</p>')
        
        if issue.likely_causes:
            html.append('<p><strong>Likely Causes:</strong></p>')
            html.append('<ul>')
            for cause in issue.likely_causes:
                html.append(f'<li>{cause}</li>')
            html.append('</ul>')
        
        html.append('</div>')
        return '\n'.join(html)
