# Unit Testing Guide for TestPilot

This document provides comprehensive instructions for running unit tests across all TestPilot components.

## 📋 Test Suite Overview

**Total Test Files: 240 tests across organized directories**
**Test Structure: Organized by functionality**
**Coverage Areas: Core validation, Exporters, Mock integration, UI components, Utils, NRF functionality, Response validation**

### 📁 Test Directory Structure
```
tests/
├── core/           # Core validation & engine tests (4 files)
├── exporters/      # HTML reports & exporters (1 file)
├── mock/           # Mock server & integration (1 file)
├── nrf/            # NRF-specific functionality (11 files)
├── ui/             # Dashboard & UI components (0 files)
├── utils/          # Excel parser & utilities (2 files)
└── validation/     # Pattern matching & validation (10 files)
```

---

## 🚀 Quick Start

### Run All Tests
```bash
# Run complete test suite
python -m pytest tests/ -v

# Run with coverage report
python -m pytest tests/ --cov=src --cov-report=html

# Run with detailed output
python -m pytest tests/ -v --tb=long
```

### Run Tests by Category
```bash
# Core functionality tests (validation engine, response validator)
python -m pytest tests/core/ -v

# Exporter tests (HTML reports, test results)
python -m pytest tests/exporters/ -v

# Mock integration tests
python -m pytest tests/mock/ -v

# NRF-specific functionality tests
python -m pytest tests/nrf/ -v

# Utility tests (Excel parser, kubectl logs)
python -m pytest tests/utils/ -v

# Validation tests (pattern matching, response validation)
python -m pytest tests/validation/ -v
```

---

## 🎯 Specific Test Scenarios

### 1. Core Functionality Testing

#### Test Core Components
```bash
# Test validation engine
python -m pytest tests/core/test_validation_engine.py -v

# Test enhanced response validator
python -m pytest tests/core/test_enhanced_response_validator.py -v

# Test test pilot core functionality
python -m pytest tests/core/test_test_pilot_core.py -v

# Test negative edge cases
python -m pytest tests/core/test_enhanced_response_validator_negative_edge.py -v
```

#### Test Specific Core Functions
```bash
# Test validation engine functions
python -m pytest tests/core/test_validation_engine.py -k "validation" -v

# Test response validator functions
python -m pytest tests/core/test_enhanced_response_validator.py -k "pattern" -v

# Test core pilot functions
python -m pytest tests/core/test_test_pilot_core.py -k "process_single_step" -v
```

### 2. Utilities Testing

#### Test Excel Parser
```bash
# Test Excel parsing functionality
python -m pytest tests/utils/test_excel_parser.py -v

# Test kubectl logs coverage
python -m pytest tests/utils/test_kubectl_logs_coverage.py -v
```

#### Test Specific Utility Functions
```bash
# Test Excel sheet operations
python -m pytest tests/utils/test_excel_parser.py -k "sheet" -v

# Test kubectl log parsing
python -m pytest tests/utils/test_kubectl_logs_coverage.py -k "kubectl" -v

# Test command extraction
python -m pytest tests/utils/ -k "curl" -v
```

### 3. NRF Functionality Testing

#### Test NRF Components
```bash
# Test all NRF functionality
python -m pytest tests/nrf/ -v

# Test NRF instance tracking
python -m pytest tests/nrf/test_nrf_instance_tracker.py -v

# Test NRF sequence management
python -m pytest tests/nrf/test_nrf_sequence_manager.py -v

# Test NRF basic functionality
python -m pytest tests/nrf/test_nrf_basic.py -v
```

#### Test Specific NRF Scenarios
```bash
# Test NRF registration scenarios
python -m pytest tests/nrf/ -k "registration" -v

# Test NRF delete scenarios
python -m pytest tests/nrf/ -k "delete" -v

# Test NRF integration
python -m pytest tests/nrf/test_curl_integration.py -v
```

### 4. Validation Testing

#### Test Pattern Matching & Validation
```bash
# Test all validation functionality
python -m pytest tests/validation/ -v

# Test pattern matching focus
python -m pytest tests/validation/test_pattern_matching_focus.py -v

# Test array validation
python -m pytest tests/validation/test_array_element_search.py -v

# Test comprehensive patterns
python -m pytest tests/validation/comprehensive_pattern_test_plan.py -v
```

#### Test Specific Validation Scenarios
```bash
# Test unicode handling
python -m pytest tests/validation/test_unicode_fix.py -v

# Test nested key-value validation
python -m pytest tests/validation/test_nested_key_value_fix.py -v

# Test raw output handling
python -m pytest tests/validation/test_raw_output_fix.py -v

# Test array subset validation
python -m pytest tests/validation/test_array_subset_fix.py -v
```

### 5. Mock Integration Testing

#### Test Mock Components
```bash
# Test mock integration
python -m pytest tests/mock/test_mock_integration.py -v

# Test mock server functionality
python -m pytest tests/mock/ -k "server" -v

# Test mock command parsing
python -m pytest tests/mock/ -k "command" -v
```

### 6. Exporter Testing

#### Test Export Components
```bash
# Test enhanced exporter
python -m pytest tests/exporters/test_enhanced_exporter.py -v

# Test HTML report generation
python -m pytest tests/exporters/ -k "html" -v

# Test result exporting
python -m pytest tests/exporters/ -k "export" -v
```

---

## 🐛 Bug Testing

### Test Known Bugs
```bash
# Test documented bugs in core validation
python -m pytest tests/core/ -k "bug" -v

# Test bug fixes in validation
python -m pytest tests/validation/ -k "fix" -v

# Test all bug-related scenarios
python -m pytest tests/ -k "bug" -v
```

---

## 📊 Performance and Stress Testing

### Memory and Performance Tests
```bash
# Test memory scenarios in core validation
python -m pytest tests/core/ -k "memory" -v

# Test performance in validation patterns
python -m pytest tests/validation/ -k "performance" -v

# Test large data structures in utils
python -m pytest tests/utils/ -k "large" -v

# Test NRF performance scenarios
python -m pytest tests/nrf/ -k "performance" -v
```

### Stress Testing
```bash
# Test concurrent scenarios
python -m pytest tests/ -k "concurrent" -v

# Test boundary conditions
python -m pytest tests/ -k "boundary" -v
```

---

## 🔧 Advanced Testing Commands

### Test with Different Output Formats
```bash
# Minimal output
python -m pytest tests/ -q

# Show local variables on failure
python -m pytest tests/ -l

# Stop on first failure
python -m pytest tests/ -x

# Show slowest tests
python -m pytest tests/ --durations=10

# Run specific number of tests
python -m pytest tests/ --maxfail=5
```

### Test with Coverage
```bash
# Generate HTML coverage report
python -m pytest tests/ --cov=src --cov-report=html --cov-report=term

# Coverage for specific module
python -m pytest tests/test_enhanced_response_validator.py --cov=src.testpilot.core.enhanced_response_validator

# Generate XML coverage report (for CI)
python -m pytest tests/ --cov=src --cov-report=xml
```

### Parallel Testing
```bash
# Install pytest-xdist first: pip install pytest-xdist
# Run tests in parallel
python -m pytest tests/ -n 4

# Run tests in parallel with verbose output
python -m pytest tests/ -n auto -v
```

---

## 🎯 Testing by Component

### Core Components (Validation Engine & Response Validator)
```bash
# Complete core testing
python -m pytest tests/core/ -v

# Core validation engine only
python -m pytest tests/core/test_validation_engine.py -v

# Enhanced response validator only
python -m pytest tests/core/test_enhanced_response_validator.py -v
```

### NRF Component Testing
```bash
# All NRF-related tests
python -m pytest tests/nrf/ -v

# NRF sequence and instance management
python -m pytest tests/nrf/test_nrf_sequence_manager.py tests/nrf/test_nrf_instance_tracker.py -v
```

### Validation Component Testing
```bash
# All pattern matching and validation tests
python -m pytest tests/validation/ -v

# Focus on pattern matching
python -m pytest tests/validation/ -k "pattern" -v
```

---

## 📈 Continuous Integration Commands

### CI Pipeline Commands
```bash
# Complete test suite with coverage (for CI)
python -m pytest tests/ --cov=src --cov-report=xml --cov-report=term --junitxml=test-results.xml

# Quick smoke tests
python -m pytest tests/core/test_test_pilot_core.py -k "basic_flow" -v

# Critical path tests
python -m pytest tests/core/test_enhanced_response_validator.py -k "validate_response" -v
```

### Docker Testing
```bash
# Run tests in clean environment
docker run -v $(pwd):/app -w /app python:3.9 python -m pytest tests/ -v
```

---

## 🛠️ Debugging Failed Tests

### Debug Specific Failures
```bash
# Run with pdb on failure
python -m pytest tests/ --pdb

# Show full traceback
python -m pytest tests/ --tb=long

# Run only failed tests from last run
python -m pytest tests/ --lf

# Run failed tests first, then continue
python -m pytest tests/ --ff
```

### Verbose Debugging
```bash
# Show print statements and logging
python -m pytest tests/ -s

# Show local variables in traceback
python -m pytest tests/ -l --tb=long

# Capture and show stdout/stderr
python -m pytest tests/ --capture=no
```

---

## 📝 Test Categories Summary

| Category | Directory | Files | Focus Area |
|----------|-----------|--------|------------|
| **Core** | `tests/core/` | 4 | Validation engine, response validator, core functionality |
| **Exporters** | `tests/exporters/` | 1 | HTML reports, test result exporters |
| **Mock** | `tests/mock/` | 1 | Mock server integration, command parsing |
| **NRF** | `tests/nrf/` | 11 | NRF-specific functionality, instance tracking |
| **UI** | `tests/ui/` | 0 | Dashboard and UI components (placeholder) |
| **Utils** | `tests/utils/` | 2 | Excel parsing, kubectl log coverage |
| **Validation** | `tests/validation/` | 10 | Pattern matching, validation fixes |

**Total: 240 comprehensive test cases across organized directories**

---

## 🏆 Quality Metrics

### Run Quality Checks
```bash
# Test coverage report
python -m pytest tests/ --cov=src --cov-report=term-missing

# Test performance (time each test)
python -m pytest tests/ --durations=0

# Test count by category
python -m pytest tests/ --collect-only -q
```

### Validate Test Quality
```bash
# Check for test naming conventions
python -m pytest tests/ --collect-only | grep "test_"

# Verify no skipped tests (except documented bugs)
python -m pytest tests/ -v | grep "SKIPPED"

# Check test isolation (run in random order)
python -m pytest tests/ --random-order
```

---

## 🚨 Emergency Testing

### Quick Health Check
```bash
# Run one test from each category directory
python -m pytest \
  tests/core/ -k "basic" --maxfail=1 \
  tests/exporters/ --maxfail=1 \
  tests/mock/ --maxfail=1 \
  tests/nrf/ -k "basic" --maxfail=1 \
  tests/utils/ --maxfail=1 \
  tests/validation/ --maxfail=1 \
  -v
```

### Critical Path Testing
```bash
# Test core functionality across all directories
python -m pytest tests/ -k "basic or core or main" --maxfail=5 -v
```

---

**For questions or issues with testing, refer to the bug reports and test documentation in the respective test files.**
