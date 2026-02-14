# Universal Report Analyzer - Multi-Format Support

## ✅ Completed Implementation

### File Formats Supported
- ✅ **HTML** - K6, Locust, Grafana, custom dashboards, any HTML report
- ✅ **JSON** - API responses, exported metrics, structured data
- ✅ **CSV** - Exported test results, metrics tables, any tabular data
- ✅ **XLSX/Excel** - Dashboard exports, performance reports, spreadsheets

### Architecture

```
┌─────────────────────────────────┐
│   Universal File Loader         │
│   (core/loader.py)              │
│  - detect_file_type()           │
│  - load_html/json/csv/xlsx()    │
└────────────┬────────────────────┘
             │
    ┌────────▼─────────────────────┐
    │   Adapter Registry           │
    │   (adapters/registry.py)     │
    │  - Auto-detection            │
    │  - Fallback to universal     │
    └────────┬────────────────────┘
             │
    ┌────────┴────────────────────────┐
    │        4 Adapters               │
    │  - k6_adapter.py                │
    │  - json_adapter.py              │
    │  - csv_adapter.py               │
    │  - xlsx_adapter.py              │
    └────────┬────────────────────────┘
             │
    ┌────────▼──────────────────┐
    │   Universal Models        │
    │   (core/models.py)        │
    │  - UniversalReport        │
    │  - Metric                 │
    │  - ReportType enum        │
    └────────┬──────────────────┘
             │
    ┌────────▼──────────────────┐
    │   Interpretation          │
    │   (core/rules.py)         │
    │  - Generate insights      │
    └───────────────────────────┘
```

### File Type Detection

| Format | Extension | Detection Method | Adapter |
|--------|-----------|------------------|---------|
| HTML | .html | BeautifulSoup parsing | k6_adapter + universal_html_adapter |
| JSON | .json | json.load() | json_adapter |
| CSV | .csv | csv.DictReader | csv_adapter |
| Excel | .xlsx, .xls | openpyxl | xlsx_adapter |

### New Components Created

#### 1. Enhanced Loader (core/loader.py)
- `load_file()` - Universal entry point
- `detect_file_type()` - Extension-based detection
- Individual loaders for each format
- Automatic format detection

#### 2. JSON Adapter (adapters/json_adapter.py)
- Extracts top-level metrics
- Recursively finds nested metrics
- Aggregates array data
- Auto-detects K6, Locust, JMeter, Grafana formats

#### 3. CSV Adapter (adapters/csv_adapter.py)
- Key-value pair extraction (single row)
- Column-based metrics (multi-row)
- Automatic metric column detection
- Handles named columns: metric/name/label, value/result/avg

#### 4. Excel Adapter (adapters/xlsx_adapter.py)
- Multi-sheet support
- Metric-value pair extraction
- Column aggregation
- Metadata extraction

### Usage Examples

```python
from core.loader import load_file
from adapters.registry import get_registry

# Load any file format
data, file_type = load_file("report.json")  # or .csv, .xlsx, .html

# Get registry and parse
registry = get_registry()
report = registry.parse(data, report_type=ReportType.JSON)

# Access metrics
for metric in report.all_metrics():
    print(f"{metric.name}: {metric.value} {metric.unit}")
```

### Current Test Files

```
report_sample/
├── test_report.json          # K6-format JSON report
├── test_metrics.csv          # Performance metrics CSV
├── performance_metrics.xlsx  # Excel spreadsheet with metrics
├── baseline-report-*.html    # K6 HTML reports
├── smoke-report-*.html       # K6 HTML reports
├── load-report-*.html        # K6 HTML reports
├── stress-report-*.html      # K6 HTML reports
├── spike-report-*.html       # K6 HTML reports
├── auth.html                 # Unknown format (template)
├── smoke.html                # Unknown format (template)
└── soak.html                 # Unknown format (template)
```

### Result Summary (14 reports processed)

- ✅ 9 K6 HTML reports detected and parsed
- ✅ 1 K6 JSON report detected and parsed
- ✅ 1 CSV report detected and parsed
- ✅ 1 Excel report detected and parsed
- ⚠️ 3 unknown HTML files (templates with no metrics)

### How to Add New Report Types

1. Create adapter: `adapters/new_type_adapter.py`
   ```python
   def parse_new_type_report(data) -> UniversalReport:
       metrics = {}
       # Extract metrics from data
       return UniversalReport(report_type=ReportType.NEW_TYPE, metrics=metrics)
   
   def _detect_new_type(data) -> bool:
       # Detection logic
       return True/False
   ```

2. Register in `main.py`:
   ```python
   register_adapter(
       ReportType.NEW_TYPE,
       parse_new_type_report,
       _detect_new_type
   )
   ```

3. Done! System automatically handles files.

### Dependencies Added

- `openpyxl` - for Excel/XLSX support

### Key Features

✅ **Format Agnostic** - Works with any file type  
✅ **Auto-Detection** - Identifies report type automatically  
✅ **Fallback Parsing** - Graceful handling of unknown formats  
✅ **Extensible** - Easy to add new file types  
✅ **Backward Compatible** - All existing K6 reports still work  
✅ **Metadata Extraction** - Captures test info from files  
✅ **Insight Generation** - Works across all formats  

### Example Output

```
Found 14 reports

Report: test_report.json
Type: k6
Metrics:
  total_requests: 5000.0count
  failed_requests: 45.0count
  failure_rate: 0.9%
  avg: 234.5ms
  p95: 520.0ms
  throughput: 125.5/sec

Report: performance_metrics.xlsx
Type: analytics
Metrics:
  avg_response_time: 23.5ms
  p95_response_time: 45.8ms
  p99_response_time: 89.2ms

Report: test_metrics.csv
Type: unknown
Metrics:
  avg_response_time: 89.3ms
  p95_response_time: 145.2ms
  success_rate: 100.0%
```

## Next Steps

Possible enhancements:
1. Add XML adapter
2. Add Prometheus/Grafana API support
3. Add PDF report parsing
4. Add database query integration
5. Export results to JSON/CSV
6. Add report comparison
7. Add trend analysis
