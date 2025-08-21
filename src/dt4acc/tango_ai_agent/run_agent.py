#!/usr/bin/env python3
"""
Simple launcher for Tango AI Agent
"""

import sys
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(src_path))

if __name__ == "__main__":
    try:
        from dt4acc.tango_ai_agent.main import main
        exit_code = main()
        sys.exit(exit_code)
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure you're in the correct directory and dependencies are installed")
        print("   Run: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
