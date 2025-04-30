#!/usr/bin/env python3
"""
Script to generate tests data for evaluate Shakers AI Support System.
"""
import os
import sys
import subprocess
from datetime import datetime

def generate_data():
    """Set up the testing environment."""
    print("\n🔧 Setting up testing environment...")
    
    # Create necessary directories
    os.makedirs("tests/data", exist_ok=True)
    os.makedirs("tests/results", exist_ok=True)
    os.makedirs("tests/results/figures", exist_ok=True)
    
    # Generate test data if it doesn't exist
    if not os.path.exists("tests/data/test_queries.json"):
        print("Generating test data...")
        subprocess.run([sys.executable, "tests/generate_test_data.py"], check=True)
    else:
        print("Test data already exists.")

if __name__ == "__main__":
    # Start generating data
    print("\n" + "="*80)
    print(f"🚀 Generating Shakers AI Support System test data at {datetime.now().isoformat()}")
    print("="*80)
    
    # Setup environment
    generate_data()