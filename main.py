import os
from pathlib import Path
from core.loader import load_file
from adapters.json_adapter import parse_json_report, _detect_json_report
from adapters.csv_adapter import parse_csv_report, _detect_csv_report
from adapters.xlsx_adapter import parse_xlsx_report, _detect_xlsx_report
from adapters.registry import register_adapter, get_registry
from core.models import ReportType
from core.rules import interpret

REPORTS_DIR = "report_sample"

def find_reports(folder):
    """Find all supported report files"""
    supported_extensions = [".html", ".json", ".csv", ".xlsx", ".xls"]
    return [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if any(f.lower().endswith(ext) for ext in supported_extensions)
    ]

def print_report(report, insights, filename):
    print(f"\n==============================")
    print(f"Report: {filename}")
    print(f"Type: {report.report_type.value}")
    print(f"==============================")
    
    # Print all metrics
    print("\nMetrics:")
    if report.all_metrics():
        for metric in report.all_metrics():
            print(f"  {metric}")
    else:
        print("  (No metrics extracted)")
    
    print("\nInsights")
    if insights:
        for i in insights:
            print("-", i)
    else:
        print("- No specific insights generated.")

def main():
    # Register all adapters
    register_adapter(
        ReportType.JSON,
        parse_json_report,
        _detect_json_report
    )
    
    register_adapter(
        ReportType.CSV,
        parse_csv_report,
        _detect_csv_report
    )
    
    register_adapter(
        ReportType.XLSX,
        parse_xlsx_report,
        _detect_xlsx_report
    )
    
    registry = get_registry()
    
    reports = find_reports(REPORTS_DIR)

    if not reports:
        print("No reports found.")
        return
    
    print(f"Found {len(reports)} reports\n")

    for path in sorted(reports):
        filename = os.path.basename(path)
        
        try:
            # Load file in appropriate format
            data, file_type = load_file(path)
            
            # Determine report type by file type first
            report_type = None
            if file_type == "json":
                report_type = ReportType.JSON
            elif file_type == "csv":
                report_type = ReportType.CSV
            elif file_type == "xlsx":
                report_type = ReportType.XLSX
            
            # Parse with registry
            report = registry.parse(data, report_type=report_type)
            
            # Generate insights
            insights = interpret(report.raw_data if hasattr(report, 'raw_data') else report)

            print_report(report, insights, filename)
            
        except Exception as e:
            print(f"\n⊘ Error processing {filename}: {str(e)}")

if __name__ == "__main__":
    main()
