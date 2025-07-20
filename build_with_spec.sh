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
    # Add root-level Python files
    for py_file in Path(project_root).glob('*.py'):
        if py_file.name != 'test_pilot.py':
            modules.append(py_file.stem)
    
    # Add src package and its modules
    src_path = Path(project_root) / 'src'
    if src_path.exists():
        modules.append('src')
        # Add testpilot package
        testpilot_path = src_path / 'testpilot'
        if testpilot_path.exists():
            modules.append('src.testpilot')
    
    # Add scripts package and its modules
    scripts_path = Path(project_root) / 'scripts'
    if scripts_path.exists():
        modules.append('scripts')
    
    # Add examples package and its modules
    examples_path = Path(project_root) / 'examples'
    if examples_path.exists():
        modules.append('examples')
        # Add examples/scripts if it exists
        examples_scripts_path = examples_path / 'scripts'
        if examples_scripts_path.exists():
            modules.append('examples.scripts')

    # Recursively find all packages and modules
    for init_file in Path(project_root).rglob('__init__.py'):
        package_path = init_file.parent
        relative_path = package_path.relative_to(project_root)
        module_name = str(relative_path).replace(os.sep, '.')
        modules.append(module_name)

        # Add all Python files in the package
        for py_file in package_path.glob('*.py'):
            if py_file.name != '__init__.py':
                full_module = f"{module_name}.{py_file.stem}"
                modules.append(full_module)
    
    return modules

local_modules = find_local_modules()
print(f"Auto-detected modules: {local_modules}")

# Add specific modules that might be missed by auto-detection
specific_modules = [
    'src.testpilot.core.test_pilot_core',
    'src.testpilot.ui.console_table_fmt',
    'src.testpilot.utils.config_resolver',
    'src.testpilot.utils.excel_parser',
    'src.testpilot.utils.logger',
    'src.testpilot.utils.myutils',
    'src.testpilot.utils.ssh_connector',
    'examples.scripts.pattern_match_parser',
    'examples.scripts.pattern_to_dict_converter'
]

# Add standard imports that are required
standard_imports = [
    'pandas', 'tabulate', 'paramiko', 'openpyxl', 'xlrd', 'json', 're', 'deepdiff',
    'argparse', 'datetime', 'os', 'platform', 'subprocess', 'sys', 'time'
]

all_imports = standard_imports + local_modules + specific_modules

# Remove duplicates while preserving order
all_imports = list(dict.fromkeys(all_imports))

a = Analysis(
    ['test_pilot.py'],
    pathex=[project_root],
    binaries=[],
    datas=[
        ('config', 'config'),
        ('src/testpilot', 'src/testpilot'),
        ('examples', 'examples')
    ],
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
