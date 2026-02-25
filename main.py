import os
import sys
from pathlib import Path
from core.loader import load_file
from adapters.json_adapter import parse_json_report, _detect_json_report
from adapters.csv_adapter import parse_csv_report, _detect_csv_report
from adapters.xlsx_adapter import parse_xlsx_report, _detect_xlsx_report
from adapters.registry import register_adapter, get_registry
from core.models import ReportType
from core.rules import interpret
from core.detailed_analysis import generate_detailed_analysis
from core.formatters import TextFormatter

REPORTS_DIR = "report_sample"

# Configuration - set to True to enable detailed analysis
USE_DETAILED_ANALYSIS = True

def find_reports(folder):
    """Find all supported report files"""
    supported_extensions = [".html", ".json", ".csv", ".xlsx", ".xls"]
    return [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if any(f.lower().endswith(ext) for ext in supported_extensions)
    ]

def print_report(report, insights, filename):
    """Print basic report summary"""
    print(f"\n{'='*80}")
    print(f"Report: {filename}")
    print(f"Type: {report.report_type.value}")
    print(f"{'='*80}")
    
    # Print all metrics
    print("\nMetrics:")
    if report.all_metrics():
        for metric in report.all_metrics():
            print(f"  {metric}")
    else:
        print("  (No metrics extracted)")
    
    print("\nInsights:")
    if insights:
        for i in insights:
            print("-", i)
    else:
        print("- No specific insights generated.")

def print_detailed_report(analysis):
    """Print detailed analysis report"""
    # Use the text formatter for nicely formatted output
    print(TextFormatter.format(analysis))

def main():
    # Check for command line arguments
    if len(sys.argv) > 1:
        if "--help" in sys.argv or "-h" in sys.argv:
            print("Universal Report Analyzer - CLI")
            print("=" * 50)
            print("\nUsage:")
            print("  python main.py [options]")
            print("\nOptions:")
            print("  --help, -h       Show this help message")
            print("  --detailed       Enable detailed analysis (default: True)")
            print("  --basic          Use basic analysis only")
            print("\nThe tool analyzes all report files in the 'report_sample' folder.")
            return
        
        # Check if user wants basic analysis
        if "--basic" in sys.argv:
            global USE_DETAILED_ANALYSIS
            USE_DETAILED_ANALYSIS = False
    
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
        print("No reports found in 'report_sample' folder.")
        print("Please add HTML, JSON, CSV, or XLSX report files to analyze.")
        return
    
    print("=" * 80)
    print("UNIVERSAL REPORT ANALYZER - CLI")
    print("=" * 80)
    print(f"\nFound {len(reports)} report(s) in '{REPORTS_DIR}'")
    print(f"Analysis Mode: {'Detailed' if USE_DETAILED_ANALYSIS else 'Basic'}")
    print("\nProcessing...\n")

    success_count = 0
    error_count = 0

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
            
            if USE_DETAILED_ANALYSIS:
                # Detect test type from filename
                test_type = "default"
                filename_lower = filename.lower()
                if "stress" in filename_lower:
                    test_type = "stress"
                elif "smoke" in filename_lower:
                    test_type = "smoke"
                elif "load" in filename_lower:
                    test_type = "load"
                
                # Generate detailed analysis
                detailed = generate_detailed_analysis(report, test_type=test_type, source_file=filename)
                print_detailed_report(detailed)
            else:
                # Generate basic insights
                insights = interpret(report)
                print_report(report, insights, filename)
            
            success_count += 1
            
        except Exception as e:
            error_count += 1
            print(f"\n{'='*80}")
            print(f"❌ Error processing: {filename}")
            print(f"{'='*80}")
            print(f"Error: {str(e)}")
            
            # Print detailed traceback in debug mode
            if "--debug" in sys.argv:
                import traceback
                traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 80)
    print("PROCESSING COMPLETE")
    print("=" * 80)
    print(f"✅ Successfully processed: {success_count}")
    if error_count > 0:
        print(f"❌ Errors: {error_count}")
    print("=" * 80)

if __name__ == "__main__":
    main()
