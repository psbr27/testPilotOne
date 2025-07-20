# Mock Testing Strategy for TestPilot

## 📋 Overview

Based on analysis of `nrf_tests_updated.xlsx`, we need to create a comprehensive mock testing framework that validates:

1. **HTTP Status Code** validation (primary check)
2. **Response Payload** comparison (JSON file-based)
3. **Pattern Matching** (regex/string patterns in responses)

## 🔍 Excel File Analysis

### Test Structure Found:
- **11 sheets** with test scenarios (NRFRegistration, NRFDiscovery, etc.)
- **Standard columns**: Test_Name, podExec, Command, Request_Payload, Expected_Status, Response_Payload, Pattern_Match
- **Test flows**: Multi-step workflows grouped by Test_Name
- **Validation types**: 3 levels of validation as described below

### Key Findings:
- **288 total test steps** across all sheets (example: NRFRegistration=53, NRFDiscovery=107)
- **Response_Payload**: JSON file references (e.g., `reg_02_payload_01.json`)
- **Pattern_Match**: Complex JSON patterns with line breaks (`_x000D_`)
- **Commands**: Primarily curl with HTTP methods (GET, PUT, DELETE, POST)

## 🎯 Mock Testing Strategy

### 1. **Three-Layer Validation System**

```python
class MockTestValidator:
    def validate_step(self, response, expected_status, response_payload, pattern_match):
        """
        Validates test step with three checks:
        1. HTTP Status Code (mandatory)
        2. Response Payload (if present)
        3. Pattern Match (if present)
        """
        results = ValidationResults()

        # Layer 1: HTTP Status Code (MANDATORY)
        if not self.validate_http_status(response.status_code, expected_status):
            results.fail("HTTP status mismatch")
            return results  # Early exit on status failure

        # Layer 2: Response Payload (if specified)
        if response_payload:
            if not self.validate_response_payload(response.json(), response_payload):
                results.fail("Response payload mismatch")
                return results

        # Layer 3: Pattern Match (if specified)
        if pattern_match:
            if not self.validate_pattern_match(response.text, pattern_match):
                results.fail("Pattern match failed")
                return results

        results.pass_all()
        return results
```

### 2. **Mock Server Architecture**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Test Runner   │───▶│   Mock Server    │───▶│  Validation     │
│                 │    │                  │    │  Engine         │
│ - Excel Parser  │    │ - HTTP Endpoints │    │ - Status Check  │
│ - Test Executor │    │ - JSON Responses │    │ - Payload Check │
│ - Result Logger │    │ - Pattern Data   │    │ - Pattern Match │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### 3. **Test Types Classification**

| Test Type | Example | Validation | Mock Strategy |
|-----------|---------|------------|---------------|
| **CRUD Operations** | PUT/GET/DELETE NF instances | Status + Payload | Stateful mock with data persistence |
| **Discovery Queries** | GET with filters | Status + Pattern | Dynamic response generation |
| **Error Scenarios** | Invalid payloads | Status + Error pattern | Predefined error responses |
| **Validation Checks** | Field validation | Status + Specific patterns | Rule-based response validation |

## 🛠 Implementation Plan

### Phase 1: Core Mock Framework

```python
# 1. Mock Server Setup
class NRFMockServer:
    def __init__(self):
        self.app = Flask(__name__)
        self.data_store = {}  # Stateful storage
        self.response_payloads = self.load_response_payloads()
        self.setup_routes()

    def setup_routes(self):
        @self.app.route('/nnrf-nfm/v1/nf-instances/', methods=['PUT', 'GET', 'DELETE'])
        def nf_instances():
            return self.handle_nf_instances_request()

# 2. Validation Engine
class ValidationEngine:
    def validate_http_status(self, actual, expected):
        return actual == int(expected)

    def validate_response_payload(self, actual_json, expected_file):
        expected_json = self.load_json_file(expected_file)
        return self.deep_json_compare(actual_json, expected_json)

    def validate_pattern_match(self, response_text, pattern):
        cleaned_pattern = self.clean_pattern(pattern)  # Handle _x000D_
        return self.pattern_matches(response_text, cleaned_pattern)
```

### Phase 2: Test Data Management

```python
# 3. Response Payload Manager
class ResponsePayloadManager:
    def __init__(self, payloads_dir="test_payloads/"):
        self.payloads_dir = payloads_dir
        self.payloads_cache = {}

    def load_payload(self, filename):
        """Load JSON payload from file"""
        if filename not in self.payloads_cache:
            with open(f"{self.payloads_dir}/{filename}") as f:
                self.payloads_cache[filename] = json.load(f)
        return self.payloads_cache[filename]

# 4. Pattern Match Processor
class PatternMatchProcessor:
    def clean_excel_pattern(self, pattern):
        """Clean Excel patterns (remove _x000D_, format JSON)"""
        return pattern.replace('_x000D_', '').strip()

    def create_regex_pattern(self, pattern):
        """Convert pattern to regex for flexible matching"""
        # Handle JSON patterns, string patterns, etc.
        pass
```

### Phase 3: Test Execution Framework

```python
# 5. Test Executor
class MockTestExecutor:
    def __init__(self, mock_server_url, excel_file):
        self.mock_server_url = mock_server_url
        self.excel_parser = ExcelParser(excel_file)
        self.validator = ValidationEngine()

    def execute_test_flow(self, test_name, sheet_name):
        """Execute multi-step test flow"""
        steps = self.get_test_steps(test_name, sheet_name)
        flow_context = {}

        for step in steps:
            result = self.execute_step(step, flow_context)
            if not result.passed:
                return self.fail_flow(result)
            flow_context.update(result.context)

        return self.pass_flow()

    def execute_step(self, step, context):
        """Execute single test step with all validations"""
        # Build request from step data
        # Send request to mock server
        # Validate response using 3-layer system
        # Return ValidationResult
        pass
```

## 📁 Project Structure

```
testPilotOne/
├── mock_testing/
│   ├── __init__.py
│   ├── mock_server.py          # Flask mock server
│   ├── validation_engine.py    # 3-layer validation
│   ├── test_executor.py        # Test execution logic
│   ├── pattern_processor.py    # Pattern matching utilities
│   └── response_manager.py     # Payload management
├── test_payloads/             # JSON response files
│   ├── reg_02_payload_01.json
│   ├── disc_nfServiceList_match.json
│   └── ...
├── tests/
│   ├── test_mock_server.py     # Unit tests for mock server
│   ├── test_validation.py      # Validation engine tests
│   └── test_integration.py     # End-to-end tests
└── MOCK_TESTING_STRATEGY.md   # This document
```

## 🚀 Development Workflow

### Step 1: Extract Test Data
```bash
# Extract response payloads and patterns from Excel
python extract_test_data.py nrf_tests_updated.xlsx
```

### Step 2: Start Mock Server
```bash
# Start mock server with test data
python mock_testing/mock_server.py --port 8081 --data test_payloads/
```

### Step 3: Run Mock Tests
```bash
# Run specific test flow
python run_mock_tests.py --excel nrf_tests_updated.xlsx --test "test_5_1_1_Reg_01" --sheet "NRFRegistration"

# Run all tests in a sheet
python run_mock_tests.py --excel nrf_tests_updated.xlsx --sheet "NRFDiscovery"

# Run all tests
python run_mock_tests.py --excel nrf_tests_updated.xlsx --all
```

## 🧪 Example Test Scenarios

### Scenario 1: Registration with Payload Validation
```yaml
Test: test_5_1_1_Reg_01_NRF_Registration_with_mandatory_parameters
Steps:
  1. PUT /nnrf-nfm/v1/nf-instances/
     - Expect: 201
     - Validate: Status only
  2. GET /nnrf-nfm/v1/nf-instances/
     - Expect: 200 + reg_02_payload_01.json
     - Validate: Status + Payload match
  3. DELETE /nnrf-nfm/v1/nf-instances/
     - Expect: 204
     - Validate: Status only
```

### Scenario 2: Discovery with Pattern Matching
```yaml
Test: test_5_1_6_Validate_NRF_supports_registration_of_SMF
Steps:
  1. GET /nnrf-nfm/v1/nf-instances/
     - Expect: 200 + Pattern match for vsmfSupportInd
     - Validate: Status + Pattern ("vsmfSupportInd": true)
```

### Scenario 3: Error Validation
```yaml
Test: test_5_1_8_reg66_validate_badRequest
Steps:
  1. PUT /nnrf-nfm/v1/nf-instances/
     - Expect: 400 + Error pattern
     - Validate: Status + Pattern (Bad Request JSON)
```

## 📊 Success Metrics

- **Test Coverage**: All 288 test steps from Excel
- **Validation Accuracy**: 100% status code validation + 95% payload/pattern matching
- **Performance**: < 100ms per test step execution
- **Maintainability**: Easy addition of new test scenarios
- **CI/CD Integration**: Automated test execution in pipeline

## 🔄 Next Steps

1. **Create mock server foundation** (Flask app with basic routes)
2. **Implement validation engine** (3-layer validation system)
3. **Extract test payloads** from referenced JSON files
4. **Build pattern matching** engine for complex patterns
5. **Create test executor** that runs Excel-based test flows
6. **Add comprehensive logging** and reporting
7. **Integrate with existing TestPilot** framework

This strategy provides a robust foundation for creating comprehensive mock tests that validate the same scenarios as your production tests, but against a controlled mock environment.
