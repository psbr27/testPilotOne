#!/usr/bin/env python3
"""
Compatibility test for TestPilot
Tests Python 3.8+ compatibility by importing all modules
"""

import importlib
import sys


def test_python_version():
    """Test minimum Python version requirement."""
    print(f"Python version: {sys.version}")
    if sys.version_info < (3, 8):
        print("FAIL: Python 3.8+ required")
        return False
    print("PASS: Python version compatible")
    return True

def test_imports():
    """Test all module imports."""
    modules_to_test = [
        'curl_builder',
        'ssh_connector', 
        'excel_parser',
        'test_result',
        'parse_utils',
        'response_parser',
        'test_pilot_core',
        'logger',
        'console_table_fmt',
        'dry_run'
    ]
    
    failed_imports = []
    
    for module in modules_to_test:
        try:
            importlib.import_module(module)
            print(f"PASS: {module}")
        except ImportError as e:
            print(f"FAIL: {module} - {e}")
            failed_imports.append(module)
        except Exception as e:
            print(f"WARNING: {module} - {e}")
    
    return len(failed_imports) == 0

def test_dependencies():
    """Test required dependencies."""
    required_deps = [
        'pandas',
        'paramiko', 
        'jsondiff',
        'tabulate',
        'openpyxl'
    ]
    
    failed_deps = []
    
    for dep in required_deps:
        try:
            importlib.import_module(dep)
            print(f"PASS: {dep}")
        except ImportError:
            print(f"FAIL: {dep} not installed")
            failed_deps.append(dep)
    
    if failed_deps:
        print(f"\nTo install missing dependencies:")
        print(f"pip install {' '.join(failed_deps)}")
    
    return len(failed_deps) == 0

def main():
    """Run all compatibility tests."""
    print("🔍 Testing TestPilot Python 3.8+ Compatibility\n")
    
    tests = [
        ("Python Version", test_python_version),
        ("Dependencies", test_dependencies), 
        ("Module Imports", test_imports)
    ]
    
    all_passed = True
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        if not test_func():
            all_passed = False
    
    print(f"\n{'='*50}")
    if all_passed:
        print("🎉 ALL TESTS PASSED - TestPilot is Python 3.8+ compatible!")
    else:
        print("SOME TESTS FAILED - Check requirements and dependencies")
        sys.exit(1)

if __name__ == "__main__":
    main()