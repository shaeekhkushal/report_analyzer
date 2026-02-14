#!/bin/bash

# Universal Report Analyzer - Web Interface Startup Script

echo "🚀 Starting Universal Report Analyzer"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if Flask is installed
python -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📦 Installing Flask and Werkzeug..."
    pip install flask werkzeug
fi

# Create uploads directory if it doesn't exist
mkdir -p uploads

echo ""
echo "✅ All dependencies ready"
echo ""
echo "🌐 Starting web server..."
echo "📍 Open your browser to: http://localhost:5000"
echo ""
echo "📁 Supported formats:"
echo "   • HTML reports (K6, Locust, JMeter, Grafana, etc.)"
echo "   • JSON files"
echo "   • CSV files"
echo "   • Excel files (.xlsx, .xls)"
echo ""
echo "💡 Features:"
echo "   • Drag & drop file upload"
echo "   • Multi-file batch processing"
echo "   • Real-time metric extraction"
echo "   • Automatic performance insights"
echo ""
echo "Press Ctrl+C to stop the server"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python app.py
