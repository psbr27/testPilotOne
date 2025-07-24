# TestPilot Unit Test Plan

## Current Test Coverage

### Existing Tests
- **NRF Module**: Instance tracker, sequence manager, curl integration, double delete scenarios
- **Validation Engine**: Pattern matching, array operations, unicode handling
- **Mock Integration**: Basic mock server testing
- **Exporters**: Enhanced exporter tests

### Critical Gaps in Test Coverage

## High Priority Test Cases

### 1. Core Test Execution (`test_pilot_core.py`)
**Missing Tests:**
- [ ] `process_single_step()` - Test step orchestration
- [ ] `execute_command()` - SSH vs local execution paths
- [ ] `build_command_for_step()` - Command construction
- [ ] `extract_step_data()` - Data extraction logic
- [ ] `manage_workflow_context()` - Context persistence
- [ ] Placeholder substitution logic
- [ ] Error handling for failed commands

### 2. Excel Parser (`excel_parser.py`)
**Missing Tests:**
- [ ] Sheet filtering with ignore keywords
- [ ] Curl command parsing from Excel cells
- [ ] Test flow grouping by Test_Name
- [ ] Handling empty/corrupted Excel files
- [ ] Special characters in test names
- [ ] Missing required columns

### 3. SSH Connector (`ssh_connector.py`)
**Missing Tests:**
- [ ] Connection establishment with retry logic
- [ ] Key-based vs password authentication
- [ ] Command execution over SSH
- [ ] Connection pooling
- [ ] Authentication failures
- [ ] Network timeouts

### 4. Response Validators (`enhanced_response_validator.py`)
**Missing Tests:**
- [ ] Dictionary subset validation
- [ ] Array order handling (ordered vs unordered)
- [ ] Pattern type detection
- [ ] JSON path extraction
- [ ] Deep nesting validation
- [ ] Type mismatch handling

### 5. Mock Server (`enhanced_mock_server.py`)
**Missing Tests:**
- [ ] Sheet/test aware response mapping
- [ ] Query parameter matching
- [ ] Step sequence tracking
- [ ] Fallback response strategies
- [ ] Concurrent request handling

### 6. Curl Builder (`curl_builder.py`)
**Missing Tests:**
- [ ] URL construction with placeholders
- [ ] Header formatting
- [ ] Method validation
- [ ] Special characters in URLs
- [ ] Authentication header handling

### 7. Result Exporters
**Missing Tests:**
- [ ] JSON/CSV format conversion
- [ ] HTML report generation
- [ ] Large result set handling
- [ ] Concurrent export operations
- [ ] File permission errors

### 8. Configuration Management
**Missing Tests:**
- [ ] Environment variable resolution
- [ ] Config file parsing
- [ ] Secure credential handling
- [ ] Missing configuration handling

## Medium Priority Test Cases

### 1. Kubectl Integration
- [ ] Log search functionality
- [ ] Real-time log capture
- [ ] Command construction
- [ ] Large log handling

### 2. Dashboard Components
- [ ] Terminal UI rendering
- [ ] Progress indicators
- [ ] Table formatting
- [ ] Interactive filtering

### 3. Utility Functions
- [ ] JSON diff calculations
- [ ] Response parsing
- [ ] Logger configuration
- [ ] Pattern compilation

## Test Implementation Strategy

### Phase 1: Core Functionality (Week 1)
1. Test execution core
2. Excel parser
3. Validation engine

### Phase 2: Infrastructure (Week 2)
1. SSH connector (with mocked SSH)
2. Mock server components
3. Kubectl integration

### Phase 3: Export & Utilities (Week 3)
1. Result exporters
2. Configuration management
3. Utility functions

### Test Framework Requirements
- Use `pytest` for test execution
- Mock external dependencies (SSH, kubectl, filesystem)
- Parameterized tests for edge cases
- Fixtures for common test data
- Coverage target: 80%+

### Test Data Requirements
- Sample Excel files with various formats
- Mock SSH responses
- Sample kubectl logs
- JSON test payloads
- Configuration templates
