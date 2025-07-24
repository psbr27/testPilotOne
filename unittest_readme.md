# Unit Testing Guide for TestPilot

This document provides comprehensive instructions for running unit tests across all TestPilot components.

## 📋 Test Suite Overview

**Total Test Files: 5**
**Total Test Cases: 145+**
**Coverage Areas: Core functionality, Excel parsing, Enhanced response validation, Negative/Edge cases, kubectl log parsing**

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
# Core functionality tests
python -m pytest tests/test_test_pilot_core.py -v

# Excel parser tests
python -m pytest tests/test_excel_parser.py -v

# Enhanced response validator tests
python -m pytest tests/test_enhanced_response_validator.py -v

# Negative and edge case tests
python -m pytest tests/test_enhanced_response_validator_negative_edge.py -v

# kubectl logs coverage tests
python -m pytest tests/test_kubectl_logs_coverage.py -v
```

---

## 🎯 Specific Test Scenarios

### 1. Core Functionality Testing

#### Test Single Functions
```bash
# Test command building
python -m pytest tests/test_test_pilot_core.py::TestCommandBuilding -v

# Test step processing
python -m pytest tests/test_test_pilot_core.py::TestStepProcessing -v

# Test pod execution scenarios
python -m pytest tests/test_test_pilot_core.py::TestPodExecution -v
```

#### Test Specific Functions
```bash
# Test process_single_step function
python -m pytest tests/test_test_pilot_core.py -k "process_single_step" -v

# Test execute_command function
python -m pytest tests/test_test_pilot_core.py -k "execute_command" -v

# Test build_command_for_step function
python -m pytest tests/test_test_pilot_core.py -k "build_command" -v
```

### 2. Excel Parser Testing

#### Test Excel Operations
```bash
# Test sheet parsing
python -m pytest tests/test_excel_parser.py::TestExcelParsing -v

# Test curl command extraction
python -m pytest tests/test_excel_parser.py::TestCurlCommandExtraction -v

# Test error handling
python -m pytest tests/test_excel_parser.py::TestErrorHandling -v
```

#### Test Specific Scenarios
```bash
# Test sheet filtering
python -m pytest tests/test_excel_parser.py -k "sheet" -v

# Test command parsing
python -m pytest tests/test_excel_parser.py -k "curl" -v

# Test validation
python -m pytest tests/test_excel_parser.py -k "validation" -v
```

### 3. Enhanced Response Validator Testing

#### Main Validator Tests (82 tests)
```bash
# All validator tests
python -m pytest tests/test_enhanced_response_validator.py -v

# Pattern matching tests
python -m pytest tests/test_enhanced_response_validator.py -k "pattern" -v

# Dictionary matching tests
python -m pytest tests/test_enhanced_response_validator.py -k "dict" -v

# Configuration tests
python -m pytest tests/test_enhanced_response_validator.py -k "config" -v
```

#### Test Individual Functions
```bash
# Test _remove_ignored_fields
python -m pytest tests/test_enhanced_response_validator.py -k "remove_ignored" -v

# Test _is_subset_dict
python -m pytest tests/test_enhanced_response_validator.py -k "subset_dict" -v

# Test _search_nested_key_value
python -m pytest tests/test_enhanced_response_validator.py -k "nested_key" -v

# Test main validation function
python -m pytest tests/test_enhanced_response_validator.py -k "validate_response_enhanced" -v
```

### 4. Negative and Edge Case Testing

#### Run Negative Tests (17 tests)
```bash
# All negative/edge tests
python -m pytest tests/test_enhanced_response_validator_negative_edge.py -v

# Negative cases only
python -m pytest tests/test_enhanced_response_validator_negative_edge.py::TestNegativeCases -v

# Boundary conditions only
python -m pytest tests/test_enhanced_response_validator_negative_edge.py::TestBoundaryConditions -v

# Edge-to-edge interactions only
python -m pytest tests/test_enhanced_response_validator_negative_edge.py::TestEdgeToEdgeInteractions -v
```

#### Test Specific Failure Modes
```bash
# Test malformed data handling
python -m pytest tests/test_enhanced_response_validator_negative_edge.py -k "malformed" -v

# Test memory exhaustion scenarios
python -m pytest tests/test_enhanced_response_validator_negative_edge.py -k "memory" -v

# Test thread safety
python -m pytest tests/test_enhanced_response_validator_negative_edge.py -k "thread_safety" -v

# Test encoding issues
python -m pytest tests/test_enhanced_response_validator_negative_edge.py -k "encoding" -v
```

### 5. kubectl Logs Coverage Testing

#### kubectl Log Tests (19 tests)
```bash
# All kubectl tests
python -m pytest tests/test_kubectl_logs_coverage.py -v

# Verbose curl output tests
python -m pytest tests/test_kubectl_logs_coverage.py::TestKubectlVerboseCurlOutput -v

# Error scenario tests
python -m pytest tests/test_kubectl_logs_coverage.py::TestKubectlErrorScenarios -v

# Complex scenario tests
python -m pytest tests/test_kubectl_logs_coverage.py::TestKubectlComplexScenarios -v

# Real-world pattern tests
python -m pytest tests/test_kubectl_logs_coverage.py::TestKubectlRealWorldPatterns -v
```

#### Test Specific kubectl Scenarios
```bash
# Test TTY warnings and curl verbose output
python -m pytest tests/test_kubectl_logs_coverage.py -k "tty_warning" -v

# Test HTTP/2 connections
python -m pytest tests/test_kubectl_logs_coverage.py -k "http2" -v

# Test connection failures
python -m pytest tests/test_kubectl_logs_coverage.py -k "connection_failure" -v

# Test large log handling
python -m pytest tests/test_kubectl_logs_coverage.py -k "large_log" -v
```

---

## 🐛 Bug Testing

### Test Known Bugs
```bash
# Test documented UnboundLocalError bug
python -m pytest tests/test_enhanced_response_validator.py -k "partial_false_bug" -v

# Test all bug-related scenarios
python -m pytest tests/ -k "bug" -v
```

---

## 📊 Performance and Stress Testing

### Memory and Performance Tests
```bash
# Test memory exhaustion scenarios
python -m pytest tests/test_enhanced_response_validator_negative_edge.py -k "memory_exhaustion" -v

# Test resource exhaustion protection
python -m pytest tests/test_enhanced_response_validator_negative_edge.py -k "resource_exhaustion" -v

# Test large data structures
python -m pytest tests/test_kubectl_logs_coverage.py -k "large_log" -v

# Test boundary conditions
python -m pytest tests/test_enhanced_response_validator_negative_edge.py::TestBoundaryConditions -v
```

### Thread Safety Testing
```bash
# Test concurrent access
python -m pytest tests/test_enhanced_response_validator_negative_edge.py -k "thread_safety" -v
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

### Enhanced Response Validator (Core Component)
```bash
# Complete validator testing (99 tests)
python -m pytest tests/test_enhanced_response_validator.py tests/test_enhanced_response_validator_negative_edge.py -v

# Only positive cases (82 tests)
python -m pytest tests/test_enhanced_response_validator.py -v

# Only negative/edge cases (17 tests)
python -m pytest tests/test_enhanced_response_validator_negative_edge.py -v
```

### kubectl Integration Testing
```bash
# All kubectl-related tests
python -m pytest tests/test_kubectl_logs_coverage.py -v

# Real-world kubectl scenarios
python -m pytest tests/test_kubectl_logs_coverage.py -k "real" -v
```

---

## 📈 Continuous Integration Commands

### CI Pipeline Commands
```bash
# Complete test suite with coverage (for CI)
python -m pytest tests/ --cov=src --cov-report=xml --cov-report=term --junitxml=test-results.xml

# Quick smoke tests
python -m pytest tests/test_test_pilot_core.py::TestStepProcessing::test_process_single_step_basic_flow -v

# Critical path tests
python -m pytest tests/test_enhanced_response_validator.py::TestValidateResponseEnhanced -v
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

| Category | File | Tests | Focus Area |
|----------|------|-------|------------|
| **Core** | `test_test_pilot_core.py` | 26 | Command execution, step processing |
| **Excel** | `test_excel_parser.py` | 19 | Excel parsing, curl extraction |
| **Validator** | `test_enhanced_response_validator.py` | 82 | Response validation (positive cases) |
| **Negative** | `test_enhanced_response_validator_negative_edge.py` | 17 | Failure modes, edge cases |
| **kubectl** | `test_kubectl_logs_coverage.py` | 19 | kubectl log parsing, real-world scenarios |

**Total: 163+ comprehensive test cases**

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
# Run one test from each category (5 tests total)
python -m pytest \
  tests/test_test_pilot_core.py::TestStepProcessing::test_process_single_step_basic_flow \
  tests/test_excel_parser.py::TestExcelParsing::test_parse_excel_basic_functionality \
  tests/test_enhanced_response_validator.py::TestValidateResponseEnhanced::test_basic_pattern_match \
  tests/test_enhanced_response_validator_negative_edge.py::TestNegativeCases::test_malformed_json_pattern_handling \
  tests/test_kubectl_logs_coverage.py::TestKubectlVerboseCurlOutput::test_kubectl_verbose_curl_with_tty_warning \
  -v
```

### Critical Path Testing
```bash
# Test only the most critical functionality
python -m pytest tests/ -k "basic_flow or basic_functionality or basic_pattern_match" -v
```

---

**For questions or issues with testing, refer to the bug reports and test documentation in the respective test files.**
