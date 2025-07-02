#!/usr/bin/env python3
"""
Debug script to check module imports and paths before PyInstaller build
Run this before building to identify missing modules
"""

import sys
import os
import importlib
from pathlib import Path

def check_module_import(module_name):
    """Check if a module can be imported and show its location"""
    try:
        module = importlib.import_module(module_name)
        module_file = getattr(module, '__file__', 'Built-in module')
        print(f"✅ {module_name}: {module_file}")
        return True
    except ImportError as e:
        print(f"❌ {module_name}: Import failed - {e}")
        return False
    except Exception as e:
        print(f"⚠️  {module_name}: Other error - {e}")
        return False

def find_python_files_in_project():
    """Find all Python files in current directory"""
    python_files = []
    for file_path in Path('.').rglob('*.py'):
        if '__pycache__' not in str(file_path):
            python_files.append(file_path)
    return python_files

def main():
    print("=== PyInstaller Module Debug ===")
    print(f"Python executable: {sys.executable}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.path}")
    print()
    
    # Modules from your PyInstaller hidden imports
    modules_to_check = [
        'console_table_fmt',
        'logger',
        'validation_engine', 
        'response_parser',
        'test_pilot_core',
        'excel_parser',
        'ssh_connector',
        'dry_run',
        'tools.log_analyzer',
        'tools.validate_table_arguments',
        'table_demo',
        'test_result',
        'parse_instant_utils',
        'parse_utils',
        'curl_builder',
        # Standard libraries
        'pandas',
        'tabulate',
        'paramiko',
        'openpyxl',
        'xlrd',
        'deepdiff'
    ]
    
    print("=== Checking Module Imports ===")
    failed_modules = []
    for module in modules_to_check:
        if not check_module_import(module):
            failed_modules.append(module)
    
    print("\n=== Project Python Files ===")
    python_files = find_python_files_in_project()
    for file_path in sorted(python_files):
        print(f"📄 {file_path}")
    
    if failed_modules:
        print(f"\n=== Failed Modules ({len(failed_modules)}) ===")
        for module in failed_modules:
            print(f"❌ {module}")
            
            # Try to find the file in the project
            potential_files = [
                f"{module}.py",
                f"{module}/__init__.py",
                f"src/{module}.py",
                f"lib/{module}.py"
            ]
            
            found = False
            for potential_file in potential_files:
                if Path(potential_file).exists():
                    print(f"   Found file: {potential_file}")
                    found = True
                    break
            
            if not found:
                print(f"   File not found in common locations")
    
    print(f"\n=== Summary ===")
    print(f"Total modules checked: {len(modules_to_check)}")
    print(f"Failed imports: {len(failed_modules)}")
    print(f"Python files in project: {len(python_files)}")

if __name__ == "__main__":
    main()
