"""
Pytest configuration for ChronicAI API tests.

This file sets up the Python path so tests can import from the app package.
"""
import sys
from pathlib import Path

# Add the api directory to Python path
api_dir = Path(__file__).parent
sys.path.insert(0, str(api_dir))
