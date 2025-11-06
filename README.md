# TestPilot

TestPilot is a comprehensive test automation framework designed for API testing with Excel-based test definitions, specifically built for 5G network function testing and validation.

## Features

- **Excel-based test definitions**: Define tests using structured Excel spreadsheets with support for complex API workflows
- **Mock server support**: Enhanced mock server with pattern matching and response validation
- **Multiple execution modes**: Production (SSH/kubectl), mock, and dry-run execution modes
- **Rich reporting**: Export results to HTML (NF-style and standard), JSON, CSV, and Excel formats
- **Advanced pattern matching**: Complex pattern matching for log analysis and response validation
- **Dashboard displays**: Multiple display modes including blessed terminal UI and rich console output
- **NRF integration**: Specialized support for Network Repository Function testing with instance tracking
- **Enhanced validation**: Comprehensive response validation with array matching and nested key validation
- **Kubectl integration**: Built-in support for Kubernetes log retrieval and analysis
- **Rate limiting**: Configurable requests/second rate limiting with Excel column, CLI, and config support

## Installation

Install in development mode:
```bash
pip install -e .
```

## Usage

### Main Test Runner
```bash
python test_pilot.py -i your_test_file.xlsx -m otp
```

### Rate Limiting
Control request rates using Excel columns, CLI arguments, or configuration:

```bash
# CLI rate limiting (5 requests per second)
python test_pilot.py -i tests.xlsx -m config --rate-limit 5.0

# Excel column: add 'reqs_sec' column with desired rate
# Config: enable in config/hosts.json
```

### CLI Interface
```bash
testpilot -i your_test_file.xlsx -m otp
```

### Mock Server
```bash
testpilot-mock --port 8082 --data-file mock_data.json
```

### Export Tool
```bash
testpilot-export input_results.json -o enhanced_output.json
```

## Project Structure

```
testPilotOne/
├── src/testpilot/               # Main package
│   ├── core/                    # Core test execution and validation
│   │   ├── test_pilot_core.py   # Main test execution engine
│   │   ├── enhanced_response_validator.py # Advanced response validation
│   │   ├── validation_engine.py # Validation engine
│   │   └── json_match.py        # JSON matching utilities
│   ├── mock/                    # Mock server components
│   │   ├── enhanced_mock_server.py # Enhanced mock server
│   │   ├── mock_integration.py  # Mock integration utilities
│   │   └── enhanced_mock_exporter.py # Mock data export
│   ├── exporters/               # Export functionality
│   │   ├── html_report_generator.py # HTML report generation
│   │   └── test_results_exporter.py # Results export
│   ├── ui/                      # User interface components
│   │   ├── blessed_dashboard.py # Terminal-based dashboard
│   │   ├── rich_dashboard.py    # Rich console dashboard
│   │   └── console_table_fmt.py # Table formatting
│   └── utils/                   # Utility functions
│       ├── excel_parser.py      # Excel file parsing
│       ├── kubectl_logs_search.py # Kubernetes log utilities
│       ├── pattern_match.py     # Pattern matching engine
│       ├── rate_limiter.py      # Rate limiting utilities
│       ├── ssh_connector.py     # SSH connectivity
│       └── nrf/                 # NRF-specific utilities
│           ├── instance_tracker.py # NF instance tracking
│           └── sequence_manager.py # Test sequence management
├── tests/                       # Comprehensive test suite
│   ├── core/                    # Core functionality tests
│   ├── mock/                    # Mock server tests
│   ├── nrf/                     # NRF-specific tests
│   ├── utils/                   # Utility tests
│   └── validation/              # Validation tests
├── examples/                    # Example data and scripts
├── config/                      # Configuration files
├── docs/                        # Comprehensive documentation
└── excel_validator/             # Excel validation utilities
```

## Key Components

### Core Engine
- **Test Execution**: Robust test execution with error handling and retry logic
- **Response Validation**: Advanced JSON response validation with pattern matching
- **Rate Limiting**: Token bucket algorithm for controlling request rates per host or globally
- **Result Processing**: Comprehensive result processing and analysis

### Mock Server
- **Enhanced Mock Server**: Full-featured mock server with dynamic response generation
- **Pattern Matching**: Advanced pattern matching for request/response validation
- **Data Export**: Mock data export capabilities for analysis

### Reporting
- **HTML Reports**: NF-style and standard HTML reports with rich formatting
- **Multiple Formats**: Support for JSON, CSV, Excel, and custom formats
- **Dashboard Views**: Real-time test execution dashboards

### NRF Support
- **Instance Tracking**: Track NF instances across test sequences
- **Sequence Management**: Manage complex test sequences for NRF testing
- **Registration Flows**: Support for NF registration and discovery flows

## Rate Limiting Configuration

### Excel Column Support
Add a `reqs_sec` column to your Excel test files:

| Test_Name | URL | Method | reqs_sec |
|-----------|-----|--------|----------|
| Login API | /api/login | POST | 3 |
| Get Users | /api/users | GET | 10 |

### Configuration File
Enable in `config/hosts.json`:
```json
{
  "rate_limiting": {
    "enabled": true,
    "default_reqs_per_sec": 10,
    "per_host": false,
    "burst_size": null
  }
}
```

### Priority Order
1. Excel `reqs_sec` column (highest priority)
2. CLI `--rate-limit` argument
3. Config `default_reqs_per_sec`
4. Default `--step-delay` behavior (when disabled)

## Requirements

- Python 3.8+ (tested on 3.8, 3.9, 3.10, 3.11, 3.12)
- See `requirements.txt` for complete dependency list
- Optional: Kubernetes CLI (kubectl) for production testing
- Optional: SSH access for remote testing

## Testing

Run the comprehensive test suite:
```bash
pytest tests/
```

Run specific test categories:
```bash
pytest tests/core/          # Core functionality
pytest tests/mock/          # Mock server tests
pytest tests/nrf/           # NRF-specific tests
pytest tests/validation/    # Validation tests
```

## Recent Updates

- **Rate limiting support**: Added configurable requests/second rate limiting with Excel, CLI, and config support
- Enhanced NRF testing capabilities with instance tracking
- Improved HTML report generation with NF-style formatting
- Advanced pattern matching for complex validation scenarios
- Comprehensive test coverage with organized test structure
- GitHub Actions integration for automated testing
- Enhanced mock server with pattern matching capabilities

## License

MIT License
