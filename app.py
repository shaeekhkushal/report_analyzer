"""
Universal Report Analyzer - Web Interface with File Upload
Allows dynamic file uploads and processing
"""

import os
import json
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from core.loader import load_file, detect_file_type
from adapters.json_adapter import parse_json_report, _detect_json_report
from adapters.csv_adapter import parse_csv_report, _detect_csv_report
from adapters.xlsx_adapter import parse_xlsx_report, _detect_xlsx_report
from adapters.registry import register_adapter, get_registry
from core.models import ReportType
from core.rules import interpret

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

def process_report(filepath):
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
        
        # Get insights
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
        
        return {
            "success": True,
            "filename": filename,
            "file_type": file_type,
            "report_type": report.report_type.value,
            "metrics": metrics_list,
            "insights": insights,
            "metadata": report.metadata
        }
    except Exception as e:
        return {
            "success": False,
            "filename": os.path.basename(filepath),
            "error": str(e)
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
        result = process_report(filepath)
        results.append(result)
    
    return jsonify(results)

@app.route("/sample-reports")
def sample_reports():
    """Get reports from report_sample folder"""
    sample_folder = "report_sample"
    results = []
    
    if os.path.exists(sample_folder):
        for filename in sorted(os.listdir(sample_folder)):
            if allowed_file(filename):
                filepath = os.path.join(sample_folder, filename)
                result = process_report(filepath)
                results.append(result)
    
    return jsonify(results)

@app.route("/uploaded-reports")
def uploaded_reports():
    """Get reports from uploads folder"""
    results = []
    
    if os.path.exists(app.config["UPLOAD_FOLDER"]):
        for filename in sorted(os.listdir(app.config["UPLOAD_FOLDER"])):
            if allowed_file(filename):
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                result = process_report(filepath)
                results.append(result)
    
    return jsonify(results)

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
