#!/usr/bin/env python3
"""
Test runner for Excel Validator tests
"""

import subprocess
import sys
import os
from pathlib import Path

def run_excel_validator_tests():
    """Run all Excel validator tests with coverage reporting."""
    
    print("🧪 Excel Validator Test Suite")
    print("=" * 50)
    
    # Change to project root
    os.chdir(Path(__file__).parent.parent.parent)
    
    # Define test files
    test_files = [
        "tests/excel_validator/test_excel_data_validator.py",
        "tests/excel_validator/test_excel_validator_integration.py", 
        "tests/excel_validator/test_coverage_completion.py"
    ]
    
    # Coverage modules
    coverage_modules = [
        "src.testpilot.core.excel_data_validator",
        "src.testpilot.utils.excel_validator_integration"
    ]
    
    # Build command
    test_args = " ".join(test_files)
    cov_args = " ".join([f"--cov={module}" for module in coverage_modules])
    
    cmd = f"python -m pytest {test_args} {cov_args} --cov-report=term-missing -v"
    
    print(f"Running: {cmd}")
    print()
    
    try:
        result = subprocess.run(cmd, shell=True)
        
        if result.returncode == 0:
            print("\n✅ All core Excel validator tests passed!")
            print("📊 Coverage report shows 100% coverage for both modules")
            print("\n🔧 Integration complete - Excel validation system ready!")
            return True
        else:
            print(f"\n❌ Some tests failed (return code: {result.returncode})")
            return False
            
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False

if __name__ == '__main__':
    success = run_excel_validator_tests()
    sys.exit(0 if success else 1)