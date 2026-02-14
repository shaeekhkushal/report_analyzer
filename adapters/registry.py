"""
Adapter registry system for auto-detecting and parsing different report types
Supports: HTML, JSON, CSV, XLSX
"""

from typing import Callable, Optional, Union, Any
from bs4 import BeautifulSoup
from core.models import UniversalReport, ReportType

class AdapterRegistry:
    """Registry for report adapters with auto-detection"""
    
    def __init__(self):
        self._adapters: dict[ReportType, Callable[[Any], UniversalReport]] = {}
        self._detectors: dict[ReportType, Callable[[Any], bool]] = {}
    
    def register(self, 
                 report_type: ReportType, 
                 adapter_func: Callable[[Any], UniversalReport],
                 detector_func: Callable[[Any], bool]) -> None:
        """Register an adapter and its detector"""
        self._adapters[report_type] = adapter_func
        self._detectors[report_type] = detector_func
    
    def detect(self, data: Any) -> ReportType:
        """Auto-detect report type from data"""
        # Try detectors in order of specificity
        for report_type in [ReportType.K6, ReportType.GRAFANA, ReportType.LIGHTHOUSE, 
                           ReportType.LOCUST, ReportType.JMETER]:
            detector = self._detectors.get(report_type)
            if detector and detector(data):
                return report_type
        
        # Default: try to parse with universal adapter
        return ReportType.UNKNOWN
    
    def parse(self, data: Any, report_type: Optional[ReportType] = None) -> UniversalReport:
        """Parse data with specified or detected report type"""
        if report_type is None:
            report_type = self.detect(data)
        
        # Try registered adapter first
        adapter = self._adapters.get(report_type)
        if adapter is not None:
            return adapter(data)
        
        # Fallback to universal parsers based on data type
        if report_type == ReportType.UNKNOWN:
            if isinstance(data, BeautifulSoup):
                from adapters.universal_html_adapter import parse_universal_html
                return parse_universal_html(data)
            elif isinstance(data, dict):
                # Try JSON parser
                from adapters.json_adapter import parse_json_report
                return parse_json_report(data)
            elif isinstance(data, list):
                # Try CSV parser
                from adapters.csv_adapter import parse_csv_report
                return parse_csv_report(data)
        
        raise ValueError(f"No adapter registered for report type: {report_type}")
    
    def get_supported_types(self) -> list[ReportType]:
        """List all registered report types"""
        return list(self._adapters.keys())

# Global registry instance
_global_registry = AdapterRegistry()

def get_registry() -> AdapterRegistry:
    """Get the global adapter registry"""
    return _global_registry

def register_adapter(report_type: ReportType, 
                     adapter_func: Callable[[Any], UniversalReport],
                     detector_func: Callable[[Any], bool]) -> None:
    """Register an adapter globally"""
    _global_registry.register(report_type, adapter_func, detector_func)
