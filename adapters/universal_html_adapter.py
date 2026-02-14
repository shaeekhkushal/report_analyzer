"""
Universal HTML Report Parser
Extracts metrics from ANY HTML report regardless of source (K6, Locust, JMeter, Grafana, etc.)
Works by identifying common patterns in HTML structure
"""

from bs4 import BeautifulSoup
import re
from typing import Dict, List, Tuple
from core.models import UniversalReport, ReportType, Metric

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
        
        # Strategy 3: Extract from key-value divs/spans (generic dashboards)
        self._extract_from_key_value_pairs()
        
        # Strategy 4: Extract from structured text/descriptions
        self._extract_from_text_patterns()
        
        # Detect report type from metrics found
        report_type = self._detect_report_type()
        
        report = UniversalReport(
            report_type=report_type,
            metrics=self.metrics,
            metadata=self.metadata
        )
        
        return report
    
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
            rows = table.select("tbody tr, tr")
            
            for row in rows:
                cells = row.select("td, th")
                
                if len(cells) >= 2:
                    # Two-column format: label | value
                    if len(cells) == 2:
                        label = cells[0].get_text(strip=True).lower()
                        value = cells[1].get_text(strip=True)
                        self._add_metric_from_text(label, value)
                    
                    # Multi-column format: extract header and value pairs
                    elif len(cells) >= 3:
                        # First cell is often the row label
                        row_label = cells[0].get_text(strip=True).lower()
                        
                        # Other cells are metrics
                        for i, cell in enumerate(cells[1:], 1):
                            value = cell.get_text(strip=True)
                            metric_name = f"{row_label}_{i}" if row_label else f"metric_{i}"
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
        label = re.sub(r'\s+', '_', label)  # spaces to underscores
        label = re.sub(r'[^a-z0-9_]', '', label)  # remove special chars
        
        if not label or label in self.metrics:
            return
        
        # Extract numeric value
        value_clean = value.replace(",", "").strip()
        match = re.search(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', value_clean)
        
        if match:
            try:
                numeric_value = float(match.group())
                # Clean unit
                unit = unit.replace(",", "").strip() if unit else ""
                
                metric = Metric(
                    name=label,
                    value=numeric_value,
                    unit=unit
                )
                self.metrics[label] = metric
            except (ValueError, AttributeError):
                pass
    
    def _detect_report_type(self) -> ReportType:
        """Detect report type based on metrics found"""
        metric_names = set(self.metrics.keys())
        
        # K6 indicators
        if any(name in metric_names for name in ["total_requests", "failed_requests", "http_req_duration"]):
            return ReportType.K6
        
        # Locust indicators
        if any(name in metric_names for name in ["requests", "failures", "response_time_percentile"]):
            return ReportType.LOCUST
        
        # JMeter indicators
        if any(name in metric_names for name in ["samples", "errors", "average", "throughput"]):
            return ReportType.JMETER
        
        # Grafana indicators
        if any(name in metric_names for name in ["cpu", "memory", "disk", "network"]):
            return ReportType.GRAFANA
        
        # Generic performance test
        if any(name in metric_names for name in ["requests", "errors", "latency", "throughput", "avg", "p95", "p99"]):
            return ReportType.ANALYTICS
        
        return ReportType.UNKNOWN


def parse_universal_html(soup: BeautifulSoup) -> UniversalReport:
    """Parse any HTML report format"""
    parser = UniversalHTMLParser(soup)
    return parser.parse()


def _detect_any_html(soup: BeautifulSoup) -> bool:
    """Detect if it's any kind of HTML (fallback detector - always true for HTML)"""
    # If we have a soup object, it's HTML
    return bool(soup.find())
