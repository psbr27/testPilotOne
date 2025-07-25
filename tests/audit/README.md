# TestPilot Audit Module - Comprehensive Test Suite

This directory contains a comprehensive test suite for the TestPilot audit functionality, covering all aspects of the `-m audit` feature with extensive sunny day, rainy day, and edge case scenarios.

## 📁 Test Structure

```
tests/audit/
├── __init__.py                     # Package initialization
├── test_audit_engine.py           # AuditEngine validation tests
├── test_audit_exporter.py         # Excel export and formatting tests
├── test_audit_processor.py        # Step execution and processing tests
├── test_audit_integration.py      # End-to-end integration tests
├── test_audit_edge_cases.py       # Edge cases and boundary conditions
├── test_fixtures.py               # Test data fixtures and utilities
├── run_all_audit_tests.py         # Comprehensive test runner
└── README.md                       # This documentation
```

## 🧪 Test Categories

### 1. AuditEngine Tests (`test_audit_engine.py`)
- **Sunny Day Cases**: Perfect pattern matches, valid HTTP validation
- **Rainy Day Cases**: Pattern mismatches, HTTP method/status failures
- **Edge Cases**: Malformed JSON, Unicode handling, large objects
- **State Management**: Result storage, summary generation, cleanup

**Key Test Scenarios:**
- ✅ Perfect JSON pattern matching (100% validation)
- ❌ JSON content mismatches with detailed difference tracking
- ❌ HTTP method validation failures
- ❌ Status code validation failures
- 🔧 Exception handling and error recovery
- 📊 Audit summary generation and compliance reporting

### 2. AuditExporter Tests (`test_audit_exporter.py`)
- **Excel Generation**: Multi-sheet workbook creation
- **Data Formatting**: JSON formatting in cells, proper escaping
- **Advanced Formatting**: Conditional formatting, styling, column sizing
- **Error Handling**: File I/O failures, permission issues
- **Performance**: Large dataset export, concurrent operations

**Generated Excel Sheets:**
- `Detailed_Results` - Complete audit trail with all validation details
- `Audit_Summary` - High-level metrics and compliance status
- `Compliance_Report` - Risk assessment and remediation tracking
- `JSON_Data` - Properly formatted JSON patterns and responses
- `Differences_Analysis` - Detailed breakdown of all differences

### 3. AuditProcessor Tests (`test_audit_processor.py`)
- **Command Execution**: SSH vs local execution modes
- **HTTP Parsing**: Method extraction, status code parsing
- **Response Handling**: JSON parsing, error conditions
- **Integration**: AuditEngine integration, dashboard updates
- **Configuration**: Various host setups, CLI tool detection

**Command Processing Features:**
- 🌐 HTTP method extraction from curl commands
- 📊 Status code parsing from various response formats
- 🔗 SSH command execution with kubectl/oc support
- 🖥️ Local command execution fallback
- ⚡ Response parsing and data extraction

### 4. Integration Tests (`test_audit_integration.py`)
- **End-to-End Workflows**: Complete audit flow testing
- **Mock Mode Integration**: Testing with mock execution
- **Performance Testing**: Large-scale audit processing
- **Error Recovery**: Resilience under partial failures
- **Configuration Scenarios**: Multiple host configurations

**Integration Scenarios:**
- 🔄 Complete audit workflow (Excel → Processing → Report)
- 🎭 Mock mode execution with simulated responses
- 📈 Performance testing with 100+ test cases
- 🛡️ Error recovery and system resilience
- ⚙️ Various configuration combinations

### 5. Edge Cases Tests (`test_audit_edge_cases.py`)
- **Memory Limits**: Large JSON objects, deeply nested structures
- **Malformed Data**: Invalid JSON, Unicode issues, boundary values
- **Resource Exhaustion**: File descriptor limits, disk space
- **Concurrent Access**: Thread safety, race conditions
- **Boundary Conditions**: Extreme values, invalid configurations

**Edge Case Categories:**
- 💾 Memory pressure and large data handling
- 🔧 Malformed JSON and data corruption scenarios
- 🌐 Network failures and I/O edge cases
- 🔀 Concurrent access and thread safety
- 📏 Boundary value testing (status codes, data sizes)

### 6. Test Fixtures (`test_fixtures.py`)
- **Sample Data**: JSON patterns, HTTP responses, Excel data
- **Data Generators**: Performance test data, edge case scenarios
- **Utilities**: File management, validation helpers
- **Mock Objects**: Reusable test doubles and fixtures

## 🚀 Running Tests

### Run All Tests
```bash
cd tests/audit
python run_all_audit_tests.py
```

### Run Specific Test Modules
```bash
# Engine tests only
python run_all_audit_tests.py --module "Engine Tests"

# Exporter tests only
python run_all_audit_tests.py --module "Exporter Tests"

# Integration tests only
python run_all_audit_tests.py --module "Integration Tests"
```

### Run Performance Tests
```bash
python run_all_audit_tests.py --performance
```

### Run Edge Case Tests
```bash
python run_all_audit_tests.py --edge-cases
```

### Run Individual Test Files
```bash
# Individual test modules
python -m unittest tests.audit.test_audit_engine -v
python -m unittest tests.audit.test_audit_exporter -v
python -m unittest tests.audit.test_audit_processor -v

# Specific test classes
python -m unittest tests.audit.test_audit_engine.TestAuditEngine -v

# Specific test methods
python -m unittest tests.audit.test_audit_engine.TestAuditEngine.test_perfect_match_validation_pass -v
```

## 📊 Test Coverage

The test suite provides comprehensive coverage across multiple dimensions:

### Functional Coverage
- ✅ **100% Pattern Matching** - All validation scenarios
- ✅ **HTTP Validation** - Methods, status codes, headers
- ✅ **JSON Processing** - Parsing, formatting, validation
- ✅ **Excel Export** - Multi-sheet generation, formatting
- ✅ **Error Handling** - Graceful failure modes
- ✅ **Performance** - Large-scale processing

### Scenario Coverage
- 🌞 **Sunny Day** (60%) - Normal operation scenarios
- 🌧️ **Rainy Day** (25%) - Expected failure conditions
- 🎯 **Edge Cases** (15%) - Boundary and extreme conditions

### Integration Coverage
- 🔗 **Unit Tests** - Individual component testing
- 🔄 **Integration Tests** - Component interaction testing
- 🎭 **Mock Mode** - Simulated environment testing
- 🏭 **Production Mode** - Real environment testing

## 🎯 Test Quality Standards

### Test Naming Convention
```python
def test_[component]_[scenario]_[expected_outcome](self):
    """Test description explaining what is being tested"""
```

Examples:
- `test_perfect_match_validation_pass()` - Sunny day case
- `test_json_pattern_mismatch_fail()` - Rainy day case
- `test_malformed_json_pattern_fail()` - Edge case

### Test Structure Pattern
```python
def test_example(self):
    # Setup - Arrange test data and mocks
    # Execute - Call the method under test
    # Verify - Assert expected outcomes
    # Cleanup - Clean up resources if needed
```

### Assertion Standards
- Use specific assertions (`assertEqual`, `assertIn`, `assertGreater`)
- Include descriptive failure messages
- Test both positive and negative cases
- Verify error conditions and edge cases

## 📈 Performance Benchmarks

The test suite includes performance benchmarks to ensure the audit functionality scales appropriately:

- **Small Tests** (1-10 tests): < 1 second
- **Medium Tests** (10-100 tests): < 10 seconds
- **Large Tests** (100-1000 tests): < 60 seconds
- **Excel Export** (100 tests): < 15 seconds
- **Memory Usage**: < 500MB for 1000 test audit

## 🛠️ Test Utilities

### Fixtures and Mock Data
The `test_fixtures.py` module provides:
- Pre-built JSON patterns for common scenarios
- HTTP response generators
- Excel data creators
- Performance test data generators
- Edge case data collections

### Custom Assertions
```python
from tests.audit.test_fixtures import fixtures

# Validate audit result structure
self.assertTrue(fixtures.validate_audit_result_structure(result))

# Generate test data
test_results = fixtures.generate_audit_results_batch(10, 5, 2)
```

## 🔧 Debugging Tests

### Verbose Output
```bash
python run_all_audit_tests.py --verbose 2
```

### Isolated Test Debugging
```python
# Add to test method for debugging
import pdb; pdb.set_trace()

# Or use logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Test Reports
The test runner generates detailed JSON reports:
```bash
# Report file created: audit_test_report_1641234567.json
```

## 📋 Test Checklist

Before marking audit functionality as complete, verify:

- [ ] All test modules pass (5/5)
- [ ] Performance benchmarks met
- [ ] Edge cases handled gracefully
- [ ] Error conditions tested
- [ ] Integration scenarios covered
- [ ] Mock mode functionality working
- [ ] Excel export quality verified
- [ ] Memory usage within limits
- [ ] Thread safety confirmed
- [ ] Documentation updated

## 🚨 Known Test Limitations

1. **Platform Dependencies**: Some file permission tests may not work on all platforms
2. **Memory Tests**: Large memory tests skipped on systems with < 8GB RAM
3. **Performance Variance**: Performance benchmarks may vary based on system specs
4. **Excel Dependencies**: Requires openpyxl and pandas for Excel testing
5. **Mock Limitations**: Some SSH-specific features not fully testable in mock mode

## 🤝 Contributing

When adding new audit functionality:

1. **Add Unit Tests** - Cover new code with appropriate tests
2. **Update Integration Tests** - Ensure end-to-end scenarios work
3. **Add Edge Cases** - Consider boundary conditions and error cases
4. **Update Fixtures** - Add new test data as needed
5. **Update Documentation** - Keep this README current
6. **Run Full Suite** - Ensure all existing tests still pass

## 📞 Support

For test-related issues:
1. Check test logs and error messages
2. Run individual test modules to isolate issues
3. Review test fixtures for data problems
4. Verify environment setup and dependencies
5. Check known limitations section above
