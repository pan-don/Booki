#!/usr/bin/env python
"""
Entry point for running the Flask API on Hugging Face Spaces.
Uses port 7860 as required by HF Spaces.
"""

import sys
from pathlib import Path

# Add project root to path to ensure imports work
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.app import create_app

app = create_app()

if __name__ == "__main__":
    # HF Spaces expects port 7860
    app.run(host="0.0.0.0", port=7860, debug=False)