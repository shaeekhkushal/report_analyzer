"""
Universal HTML Report Parser
Extracts metrics from ANY HTML report regardless of source (K6, Locust, JMeter, Grafana, etc.)
Works by identifying common patterns in HTML structure
"""

from bs4 import BeautifulSoup
import re
from typing import Dict, List, Tuple
from core.models import UniversalReport, ReportType, Metric
from core.metric_normalizer import MetricNormalizer

class UniversalHTMLParser:
    """
    Generic HTML parser that identifies metrics in any HTML structure.
    Works with: K6, Locust, JMeter, Grafana, custom dashboards, etc.
    """
    
    def __init__(self, soup: BeautifulSoup):
        self.soup = soup
        self.metrics: Dict[str, Metric] = {}
        self.metadata = {}
    
    def parse(self) -> UniversalReport:
        """Extract all metrics from HTML and return UniversalReport"""
        # Strategy 1: Extract from metric cards/panels (K6, Grafana style)
        self._extract_from_cards()
        
        # Strategy 2: Extract from tables (most reports have these)
        self._extract_from_tables()
        
        # Strategy 3: Tool-specific extraction (Locust, JMeter)
        self._extract_locust_specific()
        self._extract_jmeter_specific()
        
        # Strategy 4: Extract from key-value divs/spans (generic dashboards)
        self._extract_from_key_value_pairs()
        
        # Strategy 5: Extract from structured text/descriptions
        self._extract_from_text_patterns()
        
        # Normalize metrics to universal schema
        self.metrics = MetricNormalizer.normalize_metrics(self.metrics)
        
        # Calculate derived metrics (like failure_rate)
        self._calculate_derived_metrics()
        
        # Detect report type from metrics found
        report_type = self._detect_report_type()
        
        report = UniversalReport(
            report_type=report_type,
            metrics=self.metrics,
            metadata=self.metadata
        )
        
        return report
    
    def _calculate_derived_metrics(self):
        """Calculate metrics that can be derived from other metrics"""
        # Calculate failure rate if we have total_requests and failed_requests
        if "total_requests" in self.metrics and "failed_requests" in self.metrics:
            # Only calculate if not already present
            if "failure_rate" not in self.metrics:
                total = self.metrics["total_requests"].value
                failed = self.metrics["failed_requests"].value
                
                if total > 0:
                    failure_rate = (failed / total) * 100
                    self.metrics["failure_rate"] = Metric(
                        name="failure_rate",
                        value=failure_rate,
                        unit="%"
                    )
        
        # Calculate success rate if we have failure_rate
        if "failure_rate" in self.metrics:
            if "success_rate" not in self.metrics:
                failure_rate = self.metrics["failure_rate"].value
                success_rate = 100 - failure_rate
                self.metrics["success_rate"] = Metric(
                    name="success_rate",
                    value=success_rate,
                    unit="%"
                )
        
        # Calculate throughput if we have total_requests and duration
        if "total_requests" in self.metrics and "test_duration" in self.metrics:
            if "throughput" not in self.metrics:
                total = self.metrics["total_requests"].value
                duration = self.metrics["test_duration"].value
                
                if duration > 0:
                    throughput = total / duration
                    self.metrics["throughput"] = Metric(
                        name="throughput",
                        value=throughput,
                        unit="req/s"
                    )
    
    def _extract_from_cards(self):
        """Extract from metric cards (common in dashboards)"""
        # Common CSS classes for metric cards
        card_selectors = [
            ".metric-card", ".card", ".panel", ".widget",
            "[class*='metric']", "[class*='stat']", "[class*='card']"
        ]
        
        for selector in card_selectors:
            cards = self.soup.select(selector)
            for card in cards:
                # Look for title and value
                title_elem = card.select_one("h1, h2, h3, h4, h5, h6, .title, .label, [class*='title']")
                value_elem = card.select_one(".value, .metric-value, [class*='value'], .number, [class*='metric']")
                
                if title_elem and value_elem:
                    title = title_elem.get_text(strip=True).lower()
                    value = value_elem.get_text(strip=True)
                    
                    self._add_metric_from_text(title, value)
    
    def _extract_from_tables(self):
        """Extract from tables (most common in reports)"""
        tables = self.soup.select("table")
        
        for table in tables:
            # Try to extract table headers for better context
            headers = []
            header_row = table.select_one("thead tr")
            if header_row:
                headers = [th.get_text(strip=True).lower() for th in header_row.select("th")]
            
            rows = table.select("tbody tr, tr")
            
            for row in rows:
                cells = row.select("td, th")
                
                if len(cells) >= 2:
                    # Two-column format: label | value
                    if len(cells) == 2:
                        label = cells[0].get_text(strip=True).lower()
                        value = cells[1].get_text(strip=True)
                        self._add_metric_from_text(label, value)
                    
                    # Multi-column format with headers
                    elif headers and len(cells) == len(headers):
                        row_label = cells[0].get_text(strip=True).lower()
                        
                        # Extract each cell with its header
                        for i, (header, cell) in enumerate(zip(headers, cells)):
                            if i == 0:  # Skip label column
                                continue
                            value = cell.get_text(strip=True)
                            # Use header as metric name with row label as prefix if needed
                            metric_name = f"{row_label}_{header}" if row_label and row_label not in ["total", "aggregated"] else header
                            self._add_metric_from_text(metric_name, value)
                    
                    # Multi-column format without headers: extract header and value pairs
                    elif len(cells) >= 3:
                        # First cell is often the row label
                        row_label = cells[0].get_text(strip=True).lower()
                        
                        # Other cells are metrics
                        for i, cell in enumerate(cells[1:], 1):
                            value = cell.get_text(strip=True)
                            metric_name = f"{row_label}_{i}" if row_label else f"metric_{i}"
                            self._add_metric_from_text(metric_name, value)
    
    def _extract_locust_specific(self):
        """Extract Locust-specific patterns from HTML"""
        tables = self.soup.select("table")
        
        for table in tables:
            # Look for Locust statistics table
            headers = []
            header_row = table.select_one("thead tr, tr:first-child")
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.select("th, td")]
            
            # Check if this looks like a Locust table
            locust_headers = ["# requests", "# failures", "median", "95%ile", "requests/s", "failures/s"]
            if any(h.lower() in [hdr.lower() for hdr in headers] for h in locust_headers):
                rows = table.select("tbody tr, tr")
                
                for row in rows:
                    cells = row.select("td")
                    if not cells or len(cells) < 2:
                        continue
                    
                    # First cell is type/name (GET, POST, Total, Aggregated)
                    row_type = cells[0].get_text(strip=True)
                    
                    # Prioritize aggregate rows (Total, Aggregated)
                    is_aggregate = row_type.lower() in ["total", "aggregated", "total requests"]
                    
                    # Extract metrics from this row
                    for i, (header, cell) in enumerate(zip(headers, cells)):
                        if i == 0:  # Skip type column
                            continue
                        
                        value_text = cell.get_text(strip=True)
                        if not value_text or value_text == "N/A":
                            continue
                        
                        # For aggregate rows, use header directly
                        # For specific rows, prefix with type
                        if is_aggregate:
                            metric_name = header
                        else:
                            metric_name = f"{row_type}_{header}"
                        
                        # Add with priority (aggregate rows overwrite individual ones)
                        self._add_metric_from_text(metric_name, value_text)
                
                # Store metadata if found
                if is_aggregate:
                    self.metadata["has_aggregate_data"] = True
    
    def _extract_jmeter_specific(self):
        """Extract JMeter-specific patterns from HTML"""
        # JMeter Dashboard has multiple sections
        
        # 1. Look for Statistics table
        stats_section = self.soup.find("div", id=lambda x: x and "statistics" in x.lower() if x else False)
        if not stats_section:
            stats_section = self.soup
        
        tables = stats_section.select("table")
        for table in tables:
            headers = []
            header_row = table.select_one("thead tr, tr:first-child")
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.select("th, td")]
            
            # Check if this is a JMeter statistics table
            jmeter_headers = ["# samples", "average", "min", "max", "std. dev.", "error %", "throughput", "kb/sec"]
            if any(h.lower() in [hdr.lower() for hdr in headers] for h in jmeter_headers):
                rows = table.select("tbody tr, tr")
                
                for row in rows:
                    cells = row.select("td")
                    if not cells or len(cells) < 2:
                        continue
                    
                    # First cell is label (request name or "Total")
                    label = cells[0].get_text(strip=True)
                    is_total = label.lower() in ["total", "overall"]
                    
                    # Extract metrics
                    for i, (header, cell) in enumerate(zip(headers, cells)):
                        if i == 0:  # Skip label column
                            continue
                        
                        value_text = cell.get_text(strip=True)
                        if not value_text or value_text == "N/A":
                            continue
                        
                        # For total/overall rows, use header directly
                        if is_total:
                            metric_name = header
                        else:
                            metric_name = f"{label}_{header}"
                        
                        self._add_metric_from_text(metric_name, value_text)
        
        # 2. Look for Percentiles table
        percentile_divs = self.soup.find_all("div", string=re.compile("percentile", re.IGNORECASE))
        for div in percentile_divs:
            # Find nearby table
            parent = div.parent
            if parent:
                table = parent.find("table")
                if table:
                    rows = table.select("tr")
                    for row in rows:
                        cells = row.select("td, th")
                        if len(cells) >= 2:
                            percentile = cells[0].get_text(strip=True)
                            value = cells[1].get_text(strip=True)
                            
                            # Convert "90%" to "p90"
                            if "%" in percentile:
                                pct_num = percentile.replace("%", "").strip()
                                metric_name = f"p{pct_num}"
                                self._add_metric_from_text(metric_name, value)
    
    def _extract_from_key_value_pairs(self):
        """Extract from div/span pairs with common patterns"""
        # Look for common key-value patterns
        patterns = [
            # div contains label and value
            ("div", lambda div: div.select_one("[class*='label'], [class*='key']"), 
                     lambda div: div.select_one("[class*='value']")),
            # span contains both
            ("span", lambda sp: sp.select_one("[class*='label']"), 
                    lambda sp: sp.select_one("[class*='value']")),
        ]
        
        for tag, get_label_fn, get_value_fn in patterns:
            elements = self.soup.select(tag)
            for elem in elements:
                label_elem = get_label_fn(elem)
                value_elem = get_value_fn(elem)
                
                if label_elem and value_elem:
                    label = label_elem.get_text(strip=True).lower()
                    value = value_elem.get_text(strip=True)
                    self._add_metric_from_text(label, value)
    
    def _extract_from_text_patterns(self):
        """Extract metrics from text patterns like "metric: 123", "metric=456", etc."""
        text = self.soup.get_text()
        
        # Pattern: "word(s): number" or "word(s) = number"
        pattern = r'([a-z\s_%\-]+)\s*[:=]\s*([\d,.\-\+eE]+)\s*([a-z%]*)'
        matches = re.finditer(pattern, text, re.IGNORECASE)
        
        seen = set()  # Avoid duplicates
        for match in matches:
            label = match.group(1).strip().lower()
            value = match.group(2)
            unit = match.group(3).strip()
            
            # Skip if already extracted
            if label in seen or label in self.metrics:
                continue
            
            seen.add(label)
            self._add_metric_from_text(label, value, unit)
    
    def _add_metric_from_text(self, label: str, value: str, unit: str = ""):
        """Convert label and value to Metric, adding to metrics dict"""
        # Clean label
        label = label.strip().lower()
        
        # Handle special characters in label (like # and %)
        # Keep original for better matching, but create clean version
        label_clean = re.sub(r'\s+', '_', label)  # spaces to underscores
        label_clean = re.sub(r'[^a-z0-9_]', '', label_clean)  # remove special chars
        
        if not label_clean:
            return
        
        # Extract numeric value and unit from value string
        value_clean = value.replace(",", "").strip()
        
        # Handle percentage values (e.g., "2.5%", "0.52%")
        if "%" in value_clean:
            match = re.search(r'([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*%', value_clean)
            if match:
                try:
                    numeric_value = float(match.group(1))
                    # Don't multiply by 100, keep as percentage value
                    unit = "%"
                    
                    metric = Metric(
                        name=label_clean,
                        value=numeric_value,
                        unit=unit
                    )
                    # Don't overwrite if already exists (prioritize first extraction)
                    if label_clean not in self.metrics:
                        self.metrics[label_clean] = metric
                    return
                except (ValueError, AttributeError):
                    pass
        
        # Handle values with units (e.g., "234 ms", "100 req/s")
        value_match = re.search(r'([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*([a-z/%]*)', value_clean, re.IGNORECASE)
        
        if value_match:
            try:
                numeric_value = float(value_match.group(1))
                extracted_unit = value_match.group(2).strip() if value_match.group(2) else ""
                
                # Use provided unit or extracted unit
                final_unit = unit if unit else extracted_unit
                
                metric = Metric(
                    name=label_clean,
                    value=numeric_value,
                    unit=final_unit
                )
                
                # Don't overwrite if already exists (prioritize first extraction)
                if label_clean not in self.metrics:
                    self.metrics[label_clean] = metric
            except (ValueError, AttributeError):
                pass
    
    def _detect_report_type(self) -> ReportType:
        """Detect report type based on metrics found"""
        # Use MetricNormalizer's improved detection
        metric_names = list(self.metrics.keys())
        detected_type = MetricNormalizer.detect_tool_from_metrics(metric_names)
        
        # If still unknown, try legacy detection patterns
        if detected_type == ReportType.UNKNOWN:
            metric_names_set = set(metric_names)
            
            # K6 indicators (after normalization)
            if any(name in metric_names_set for name in ["total_requests", "failed_requests", "http_duration_p95"]):
                return ReportType.K6
            
            # Generic performance test
            if any(name in metric_names_set for name in ["http_duration_avg", "throughput", "failure_rate"]):
                return ReportType.ANALYTICS
        
        return detected_type


def parse_universal_html(soup: BeautifulSoup) -> UniversalReport:
    """Parse any HTML report format"""
    parser = UniversalHTMLParser(soup)
    return parser.parse()


def _detect_any_html(soup: BeautifulSoup) -> bool:
    """Detect if it's any kind of HTML (fallback detector - always true for HTML)"""
    # If we have a soup object, it's HTML
    return bool(soup.find())
