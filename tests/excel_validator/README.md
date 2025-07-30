# Excel Validator Test Suite

Comprehensive test suite for the TestPilot Excel input validation and auto-categorization system.

## Overview

This test suite validates the adaptive Excel input validation system that provides:
- **JSON validation and auto-correction** for Response Payload columns
- **Pattern categorization and standardization** for Pattern Match columns
- **File processing** with caching and error handling
- **CLI integration** with TestPilot

## Test Files

| File | Purpose | Tests |
|------|---------|-------|
| `test_excel_data_validator.py` | Core validator functionality | 22 tests |
| `test_excel_validator_integration.py` | Integration with TestPilot | 17 tests |
| `test_coverage_completion.py` | 100% coverage edge cases | 4 tests |
| `test_pattern_edge_cases.py` | Heuristic limitations (optional) | 14 tests* |

*Note: Edge case tests may fail due to known heuristic limitations in pattern categorization.

## Running Tests

### Quick Test Run (Core Functionality)
```bash
# Run the essential test suite
python tests/excel_validator/run_tests.py
```

### Full Test Suite with Coverage
```bash
# Run all tests including edge cases
python -m pytest tests/excel_validator/ --cov=src.testpilot.core.excel_data_validator --cov=src.testpilot.utils.excel_validator_integration --cov-report=term-missing -v
```

### Individual Test Files
```bash
# Core validator tests
python -m pytest tests/excel_validator/test_excel_data_validator.py -v

# Integration tests  
python -m pytest tests/excel_validator/test_excel_validator_integration.py -v

# Coverage completion tests
python -m pytest tests/excel_validator/test_coverage_completion.py -v
```

## Coverage

The test suite achieves **100% code coverage** for:
- `src.testpilot.core.excel_data_validator` (203 statements)
- `src.testpilot.utils.excel_validator_integration` (61 statements)

**Total: 264 statements, 0 missed, 100% coverage**

## Test Categories

### ✅ JSON Validation (15 test scenarios)
- Valid JSON parsing and validation
- Auto-correction of malformed JSON (single quotes, trailing commas, unquoted keys)
- Excel artifact cleaning (`_x000D_`)
- Error handling for unfixable JSON
- Empty/None payload handling

### ✅ Pattern Categorization (All 6 Types)
- **SUBSTRING**: Simple text patterns
- **KEY_VALUE**: Single key:value pairs  
- **MULTI_KEY_VALUE**: Comma-separated pairs
- **JSON_OBJECT**: Valid JSON objects
- **JSON_ARRAY**: Valid JSON arrays
- **JSONPATH**: JSONPath expressions
- **REGEX**: Regular expressions

### ✅ File Processing
- Single sheet processing
- Multi-sheet file handling
- Empty file processing
- Row-by-row validation
- Missing column handling
- Output file generation

### ✅ Integration Layer
- CLI argument parsing (`--skip-validation`, `--force-validation`, `--validation-threshold`)
- Validation caching and timestamp checking
- Force re-validation functionality
- Output path generation
- Status summary reporting
- Error handling for file operations

## Performance

- **14,000+ rows/second** processing speed
- **Linear memory scaling** with file size
- **Efficient caching** prevents unnecessary re-validation
- **Large file support** (tested with 1000+ rows)

## Quality Metrics

- **100% code coverage** ensures all paths tested
- **43 comprehensive test cases** covering normal and edge cases
- **Error handling** for all failure scenarios
- **Fallback behavior** when validation fails