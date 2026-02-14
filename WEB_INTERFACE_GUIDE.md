# Web Interface Guide - Universal Report Analyzer

## Quick Start

### Option 1: Run with Web Interface (Recommended)
```bash
# Install dependencies
pip install flask werkzeug

# Start the web server
python app.py
```

Then open your browser to **`http://localhost:5000`**

### Option 2: Batch Processing (Command Line)
```bash
# Process all reports in report_sample/ folder
python main.py
```

---

## Web Interface Features

### 📤 Upload Section (Left Panel)
1. **Drag & Drop** - Simply drag files onto the upload area
2. **Click to Browse** - Or click the upload area to select files
3. **Multiple Files** - Upload several files at once
4. **Supported Formats**:
   - HTML (K6, Locust, JMeter, Grafana, etc.)
   - JSON (flat or nested structures)
   - CSV (key-value or column-based)
   - Excel (.xlsx, .xls - single/multi-sheet)
   - Max size: 50MB per file

### 📋 Results Section (Right Panel)
- **Uploaded Tab** - Shows uploaded files and their analysis
- **Samples Tab** - Load and analyze sample reports from `report_sample/` folder
- **Report Card** shows:
  - Filename and report type (color-coded)
  - File format
  - Extracted metrics (with values and units)
  - Insights and recommendations

### 🎯 Buttons
- **Upload Files** - Upload selected files and process them
- **Load Sample Reports** - Process all reports in the samples folder
- **Clear All** - Delete all uploaded files

---

## Features

### Supported Report Types
- ✅ **K6** - Load testing reports
- ✅ **Locust** - Distributed load testing
- ✅ **JMeter** - Apache JMeter results
- ✅ **Grafana** - Dashboard exports
- ✅ **Lighthouse** - Web performance audits
- ✅ **CSV/JSON/Excel** - Any structured data
- ✅ **Generic HTML** - Unknown HTML reports (auto-detected)

### Metric Extraction
The system automatically:
- Detects report type
- Extracts relevant metrics (latency, throughput, error rates, etc.)
- Generates performance insights
- Identifies anomalies and warnings

### Insights Generated
- **Failure Rate Analysis** - Critical/Warning/Good status
- **Latency Analysis** - P95, average response times
- 🔍 **Outliers Detection** - Unusual spike patterns
- ⏱️ **Extreme Stalls** - Detection of very long delays
- **Throughput Analysis** - Requests/second trends

---

## API Endpoints (if you prefer programmatic access)

```bash
# Upload files
POST /upload
Content-Type: multipart/form-data
Form data: files (multiple)

# Get sample reports
GET /sample-reports

# Get uploaded reports
GET /uploaded-reports

# Clear uploads
POST /clear-uploads

# System status
GET /health
```

---

## Workflow Example

1. **Start server**: `python app.py`
2. **Open browser**: `http://localhost:5000`
3. **Upload report**: Drag-drop a K6 HTML report
4. **View metrics**: See extracted performance metrics
5. **Read insights**: Get recommendations based on analysis
6. **Upload more**: Add additional files without restarting

---

## Troubleshooting

### Flask not found
```bash
pip install flask werkzeug
```

### Port 5000 already in use
Edit `app.py` and change:
```python
app.run(debug=True, port=5001)  # Use different port
```

### Files not uploading
- Check file size (max 50MB)
- Verify file format (.html, .json, .csv, .xlsx, .xls)
- Check browser console for error messages

### No metrics extracted
- Ensure the report has readable data
- Try uploading a sample report first
- Check browser console for errors

---

## Directory Structure

```
report_analyzer/
├── app.py                    # Flask web server
├── main.py                   # Batch processing
├── templates/
│   └── index.html           # Web interface (UI)
├── uploads/                 # Uploaded files storage
├── report_sample/           # Sample reports
├── core/
│   ├── loader.py           # File loading
│   ├── models.py           # Data structures
│   ├── rules.py            # Analysis rules
│   └── dom_utils.py        # HTML parsing utilities
└── adapters/
    ├── registry.py         # Adapter management
    ├── k6_adapter.py       # K6 report parser
    ├── universal_html_adapter.py
    ├── json_adapter.py
    ├── csv_adapter.py
    └── xlsx_adapter.py
```

---

## Tips & Tricks

### 🚀 Performance
- Upload multiple files at once for batch processing
- Use "Load Sample Reports" to test the system
- Processing typically takes < 1 second per file

### Best Practices
- Organize reports by test type
- Upload baseline reports first for comparison
- Use consistent naming (e.g., `smoke-2026-02-09.html`)

### 🔧 Development
To modify the web interface:
- Edit `templates/index.html` for UI changes
- Update `app.py` for backend logic
- Restart server after changes

---

## Questions?

See `README.md` for architecture details or check the inline code comments in the source files.
