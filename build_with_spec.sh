#!/bin/bash
# Build script using .spec file for better module detection
# Usage: bash build_with_spec.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check prerequisites
if [ ! -f "test_pilot.py" ]; then
    log_error "test_pilot.py not found. Run from project root."
    exit 1
fi

if ! command -v pyinstaller &> /dev/null; then
    log_error "PyInstaller not installed. Run: pip install pyinstaller"
    exit 1
fi

# Clean previous builds
log_info "Cleaning previous builds..."
rm -rf dist build *.spec

# Create the spec file
log_info "Creating testPilot.spec file..."
cat > testPilot.spec << 'EOF'
# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path

project_root = os.path.dirname(os.path.abspath(SPEC))
sys.path.insert(0, project_root)

def find_local_modules():
    modules = []
    for py_file in Path(project_root).glob('*.py'):
        if py_file.name != 'test_pilot.py':
            modules.append(py_file.stem)
    
    for init_file in Path(project_root).rglob('__init__.py'):
        package_path = init_file.parent
        relative_path = package_path.relative_to(project_root)
        module_name = str(relative_path).replace(os.sep, '.')
        modules.append(module_name)
        
        for py_file in package_path.glob('*.py'):
            if py_file.name != '__init__.py':
                full_module = f"{module_name}.{py_file.stem}"
                modules.append(full_module)
    return modules

local_modules = find_local_modules()
print(f"Auto-detected modules: {local_modules}")

standard_imports = [
    'pandas', 'tabulate', 'paramiko', 'openpyxl', 'xlrd', 'json', 're', 'deepdiff'
]

all_imports = standard_imports + local_modules

a = Analysis(
    ['test_pilot.py'],
    pathex=[project_root],
    binaries=[],
    datas=[],
    hiddenimports=all_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='testPilot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='testPilot',
)
EOF

# Build using the spec file
log_info "Building with PyInstaller using spec file..."
pyinstaller --clean testPilot.spec

# Verify build
if [ -d "dist/testPilot" ]; then
    log_info "Build completed successfully!"
    log_info "Binary location: dist/testPilot/"
    
    # Test the binary
    log_info "Testing binary..."
    if ./dist/testPilot/testPilot --help &> /dev/null; then
        log_info "✅ Binary test passed"
    else
        log_warning "⚠️  Binary test failed - check for missing modules"
    fi
else
    log_error "Build failed"
    exit 1
fi
