"""
Universal Report Analyzer - Web Interface with File Upload
Allows dynamic file uploads and processing
"""

import os
import json
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
from flask import Response
from werkzeug.utils import secure_filename
from core.loader import load_file, detect_file_type
from adapters.json_adapter import parse_json_report, _detect_json_report
from adapters.csv_adapter import parse_csv_report, _detect_csv_report
from adapters.xlsx_adapter import parse_xlsx_report, _detect_xlsx_report
from adapters.registry import register_adapter, get_registry
from core.models import ReportType
from core.rules import interpret
from core.detailed_analysis import generate_detailed_analysis
from core.formatters import HTMLFormatter, TextFormatter, MarkdownFormatter

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"html", "json", "csv", "xlsx", "xls"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE

# Create upload folder
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Check if file type is allowed"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def register_adapters():
    """Register all adapters"""
    register_adapter(ReportType.JSON, parse_json_report, _detect_json_report)
    register_adapter(ReportType.CSV, parse_csv_report, _detect_csv_report)
    register_adapter(ReportType.XLSX, parse_xlsx_report, _detect_xlsx_report)

def process_report(filepath, generate_detailed=False):
    """Process a single report file"""
    try:
        filename = os.path.basename(filepath)
        file_type = detect_file_type(filepath)
        
        # Load file
        data, _ = load_file(filepath)
        
        # Get registry
        registry = get_registry()
        
        # Determine report type
        report_type = None
        if file_type == "json":
            report_type = ReportType.JSON
        elif file_type == "csv":
            report_type = ReportType.CSV
        elif file_type == "xlsx":
            report_type = ReportType.XLSX
        
        # Parse
        report = registry.parse(data, report_type=report_type)
        
        # Get basic insights
        insights = interpret(report)
        
        # Format metrics
        metrics_list = [
            {
                "name": m.name,
                "value": m.value,
                "unit": m.unit,
                "percentile": m.percentile
            }
            for m in report.all_metrics()
        ]
        
        result = {
            "success": True,
            "filename": filename,
            "file_type": file_type,
            "report_type": report.report_type.value,
            "metrics": metrics_list,
            "insights": insights,
            "metadata": report.metadata
        }
        
        # Generate detailed analysis if requested
        if generate_detailed:
            # Detect test type from filename or metadata
            test_type = "default"
            filename_lower = filename.lower()
            if "stress" in filename_lower:
                test_type = "stress"
            elif "smoke" in filename_lower:
                test_type = "smoke"
            elif "load" in filename_lower:
                test_type = "load"
            
            detailed = generate_detailed_analysis(report, test_type=test_type, source_file=filename)
            
            # Convert to dictionary for JSON serialization (include all fields for CSV export)
            def serialize_issue(issue):
                return {
                    "id": getattr(issue, "id", None),
                    "title": getattr(issue, "title", None),
                    "category": getattr(issue, "category", None).value if getattr(issue, "category", None) else None,
                    "details": getattr(issue, "details", None),
                    "impact": getattr(issue, "impact", None),
                }
            def serialize_rec(rec):
                return {
                    "title": getattr(rec, "title", None),
                    "details": getattr(rec, "details", None),
                    "category": getattr(rec, "category", None),
                }
            def serialize_gap(gap):
                return {
                    "metric": getattr(gap, "metric", None),
                    "current": getattr(gap, "current", None),
                    "target": getattr(gap, "target", None),
                    "gap_percentage": getattr(gap, "gap_percentage", None),
                    "required_improvement": getattr(gap, "required_improvement", None),
                }
            result["detailed_analysis"] = {
                "test_type": detailed.executive_summary.test_type,
                "test_date": detailed.executive_summary.test_date,
                "duration": detailed.executive_summary.duration,
                "test_status": detailed.executive_summary.test_status,
                "source_file": detailed.executive_summary.source_file,
                "key_findings": detailed.executive_summary.key_findings,
                "critical_issue": detailed.executive_summary.critical_issue,
                "issues": [serialize_issue(i) for cat in [detailed.issues.critical, detailed.issues.high, detailed.issues.moderate, detailed.issues.warnings, detailed.issues.info] for i in cat],
                "recommendations": [serialize_rec(r) for r in detailed.recommendations],
                "gap_analysis": [serialize_gap(g) for g in detailed.gap_analysis],
                "total_issues": detailed.total_issues(),
                "has_critical": detailed.has_critical_issues(),
                "html": HTMLFormatter.format(detailed),
                "markdown": MarkdownFormatter.format(detailed),
                "text": TextFormatter.format(detailed)
            }
        
        return result
    except Exception as e:
        import traceback
        return {
            "success": False,
            "filename": os.path.basename(filepath),
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@app.route("/")
def index():
    """Main page"""
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload_file():
    """Handle file upload"""
    if "files" not in request.files:
        return jsonify({"error": "No files provided"}), 400
    
    files = request.files.getlist("files")
    generate_detailed = request.form.get("detailed", "false").lower() == "true"
    results = []
    
    for file in files:
        if file.filename == "":
            continue
        
        if not allowed_file(file.filename):
            results.append({
                "filename": file.filename,
                "success": False,
                "error": f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            })
            continue
        
        # Save file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)
        
        # Process file
        result = process_report(filepath, generate_detailed=generate_detailed)
        results.append(result)
    
    return jsonify(results)

@app.route("/sample-reports")
def sample_reports():
    """Get reports from report_sample folder"""
    sample_folder = "report_sample"
    generate_detailed = request.args.get("detailed", "false").lower() == "true"
    results = []
    
    if os.path.exists(sample_folder):
        for filename in sorted(os.listdir(sample_folder)):
            if allowed_file(filename):
                filepath = os.path.join(sample_folder, filename)
                result = process_report(filepath, generate_detailed=generate_detailed)
                results.append(result)
    
    return jsonify(results)

@app.route("/uploaded-reports")
def uploaded_reports():
    """Get reports from uploads folder"""
    generate_detailed = request.args.get("detailed", "false").lower() == "true"
    results = []
    
    if os.path.exists(app.config["UPLOAD_FOLDER"]):
        for filename in sorted(os.listdir(app.config["UPLOAD_FOLDER"])):
            if allowed_file(filename):
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                result = process_report(filepath, generate_detailed=generate_detailed)
                results.append(result)
    
    return jsonify(results)

@app.route("/analyze/<path:filename>")
def analyze_file(filename):
    """Analyze a specific file with detailed analysis"""
    # Try uploads folder first
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    
    # If not found, try sample folder
    if not os.path.exists(filepath):
        filepath = os.path.join("report_sample", filename)
    
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
    
    result = process_report(filepath, generate_detailed=True)
    return jsonify(result)


# --- CSV Export Route ---
@app.route("/export-csv/<path:filename>")
def export_csv(filename):
    """Export the analysis result as CSV for a given file"""
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if not os.path.exists(filepath):
        filepath = os.path.join("report_sample", filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404

    result = process_report(filepath, generate_detailed=True)
    # Compose CSV from metrics
    import csv
    from io import StringIO
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Metric Name", "Value", "Unit"])
    for metric in result.get("metrics", []):
        writer.writerow([metric["name"], metric["value"], metric.get("unit", "")])
    csv_data = output.getvalue()
    output.close()
    # Set filename for download
    download_name = f"{os.path.splitext(filename)[0]}_analysis.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={download_name}"
        }
    )


# --- Detailed Analysis CSV Export Route ---
@app.route("/export-detailed-csv/<path:filename>")
def export_detailed_csv(filename):
    """Export the detailed analysis as CSV for a given file"""
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if not os.path.exists(filepath):
        filepath = os.path.join("report_sample", filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404

    result = process_report(filepath, generate_detailed=True)
    detailed = result.get("detailed_analysis", {})
    import csv
    from io import StringIO
    output = StringIO()
    writer = csv.writer(output)
    # Executive Summary
    writer.writerow(["Executive Summary"])
    for k in ["test_type", "test_date", "duration", "test_status", "source_file", "critical_issue"]:
        if detailed.get(k):
            writer.writerow([k.replace("_", " ").title(), detailed[k]])
    if detailed.get("key_findings"):
        writer.writerow(["Key Findings"])
        for finding in detailed["key_findings"]:
            writer.writerow([finding])
    writer.writerow([])
    # Issues
    if detailed.get("issues"):
        writer.writerow(["Issues"])
        writer.writerow(["ID", "Title", "Severity", "Details", "Impact"])
        for issue in detailed["issues"]:
            writer.writerow([
                issue.get("id", ""),
                issue.get("title", ""),
                issue.get("category", ""),
                issue.get("details", ""),
                issue.get("impact", "")
            ])
        writer.writerow([])
    # Recommendations
    if detailed.get("recommendations"):
        writer.writerow(["Recommendations"])
        writer.writerow(["Title", "Details", "Category"])
        for rec in detailed["recommendations"]:
            writer.writerow([
                rec.get("title", ""),
                rec.get("details", ""),
                rec.get("category", "")
            ])
        writer.writerow([])
    # Gap Analysis
    if detailed.get("gap_analysis"):
        writer.writerow(["Gap Analysis"])
        writer.writerow(["Metric", "Current", "Target", "Gap %", "Required Improvement"])
        for gap in detailed["gap_analysis"]:
            writer.writerow([
                gap.get("metric", ""),
                gap.get("current", ""),
                gap.get("target", ""),
                gap.get("gap_percentage", ""),
                gap.get("required_improvement", "")
            ])
    csv_data = output.getvalue()
    output.close()
    download_name = f"{os.path.splitext(filename)[0]}_detailed_analysis.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={download_name}"
        }
    )

@app.route("/clear-uploads", methods=["POST"])
def clear_uploads():
    """Clear all uploaded files"""
    try:
        for filename in os.listdir(app.config["UPLOAD_FOLDER"]):
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            if os.path.isfile(filepath):
                os.remove(filepath)
        return jsonify({"success": True, "message": "Uploads cleared"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/health")
def health():
    """Health check"""
    return jsonify({
        "status": "ok",
        "supported_formats": list(ALLOWED_EXTENSIONS),
        "max_file_size_mb": MAX_FILE_SIZE // (1024 * 1024)
    })

if __name__ == "__main__":
    register_adapters()
    print("🚀 Starting Universal Report Analyzer Web Interface")
    print("📍 Open http://localhost:5000 in your browser")
    print("📁 Supported formats: HTML, JSON, CSV, XLSX")
    app.run(debug=True, port=5000)
