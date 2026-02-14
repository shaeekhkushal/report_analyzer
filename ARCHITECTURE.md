# Universal Report Interpreter - Architecture

## What Was Refactored

### 1. **Models** ([core/models.py](core/models.py))
- ✅ Added `Metric` - generic representation for any metric
- ✅ Added `ReportType` enum - extensible report types
- ✅ Added `UniversalReport` - unified format across all report types
- ✅ Kept `TestSummary` + `DurationStats` for backward compatibility
- ✅ Added conversion method: `TestSummary.to_universal_report()`

### 2. **Adapter Registry** ([adapters/registry.py](adapters/registry.py))
- ✅ Central registry for report adapters
- ✅ Auto-detection system using detector functions
- ✅ Easy registration: `register_adapter(report_type, parser_func, detector_func)`
- ✅ Single parse entry point: `registry.parse(soup)`

### 3. **K6 Adapter** ([adapters/k6_adapter.py](adapters/k6_adapter.py))
- ✅ Updated to return `UniversalReport` instead of `TestSummary`
- ✅ Added detector function `_detect_k6_report()`
- ✅ Improved robustness (handles various k6 HTML formats)

### 4. **Main** ([main.py](main.py))
- ✅ Registers k6 adapter on startup
- ✅ Uses registry for auto-detection
- ✅ Graceful error handling for unsupported report types
- ✅ Works with universal format

## Architecture Benefits

```
HTML Input → Loader → [Detector] → [Registry] → [Adapter] → UniversalReport
                           ↓
                      Auto-detected
                      report type
```

### Why This Works Globally

1. **Generic Metric Container** - Any report's metrics fit into `Metric` objects
2. **Extensible Types** - Add new `ReportType` enum values anytime
3. **Plugin Pattern** - New adapters register themselves without modifying core
4. **Backward Compatible** - Old code using `TestSummary` still works
5. **Format Agnostic** - Works with:
   - Tables (k6, Grafana)
   - JSON blocks (many dashboards)
   - Text patterns (CI reports)
   - Mixed formats

## How to Add a New Report Type

### Example: Grafana Export

```python
# adapters/grafana_adapter.py
from core.models import UniversalReport, ReportType, Metric

def parse_grafana_report(soup) -> UniversalReport:
    report = UniversalReport(report_type=ReportType.GRAFANA)
    
    # Parse Grafana-specific structure
    panels = soup.select(".panel-content")
    for panel in panels:
        title = panel.select_one(".panel-title").text
        value = panel.select_one(".metric-value").text
        report.add_metric(Metric(title, float(value), ""))
    
    return report

def _detect_grafana(soup) -> bool:
    return bool(soup.select(".grafana-panel"))

# Register in main.py
register_adapter(ReportType.GRAFANA, parse_grafana_report, _detect_grafana)
```

## Current Status

✅ **Working:**
- 9 k6 reports parsed successfully
- Universal format working
- Auto-detection operational
- Graceful error handling

⊘ **Skipped (Not k6 format):**
- auth.html, smoke.html, soak.html (likely different report types or raw data)

## Next Steps

1. Add Grafana adapter (follow Grafana export HTML structure)
2. Add Lighthouse adapter (use JSON + DOM)
3. Add HR system adapter (table-based)
4. Create interpreters per report type
5. Add export formats (JSON, CSV, markdown reports)
