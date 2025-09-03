#!/bin/bash

# Create PDF and PowerPoint presentation from Markdown
echo "🚀 Creating EPICS to Tango Presentation..."

# Install required packages
echo "📦 Installing required packages..."
pip3 install -r requirements_presentation.txt

# Run the conversion script
echo "🔄 Converting Markdown to PDF and PowerPoint..."
python3 convert_to_presentation.py

echo "✅ Presentation creation complete!"
echo "📁 Files created:"
echo "   - EPICS_TO_TANGO_PRESENTATION.pdf"
echo "   - EPICS_TO_TANGO_PRESENTATION.pptx"
echo ""
echo "💡 Note: For PDF conversion, you may need to install wkhtmltopdf:"
echo "   macOS: brew install wkhtmltopdf"
echo "   Ubuntu: sudo apt-get install wkhtmltopdf"
echo "   Windows: Download from https://wkhtmltopdf.org/downloads.html"
