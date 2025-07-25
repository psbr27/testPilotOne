# TestPilot - Comprehensive Test Automation Framework

A comprehensive framework for API testing, mock server management, and test result analysis with Excel-based test definitions.

## 🏗️ Project Structure

```
testPilotOne/
├── src/
│   └── testpilot/                      # Main package
│       ├── core/                       # Core test execution
│       │   ├── test_pilot_core.py      # Main test execution engine
│       │   ├── validation_engine.py    # Test validation logic
│       │   └── test_result.py          # Test result classes
│       ├── mock/                       # Mock server components
│       │   ├── enhanced_mock_server.py # Advanced mock server
│       │   ├── enhanced_mock_exporter.py # Mock data exporter
│       │   ├── mock_integration.py     # Mock integration utilities
│       │   └── generic_mock_server.py  # Basic mock server
│       ├── exporters/                  # Export functionality
│       │   ├── test_results_exporter.py # Enhanced test results export
│       │   └── html_report_generator.py # HTML report generation
│       ├── utils/                      # Utility functions
│       │   ├── excel_parser.py         # Excel test definition parsing
│       │   ├── response_parser.py      # HTTP response parsing
│       │   ├── pattern_match.py        # Pattern matching utilities
│       │   ├── curl_builder.py         # cURL command construction
│       │   ├── ssh_connector.py        # SSH connectivity
│       │   └── logger.py               # Logging utilities
│       └── ui/                         # User interface components
│           ├── blessed_dashboard.py    # Terminal-based dashboard
│           ├── rich_dashboard.py       # Rich text dashboard
│           └── console_table_fmt.py    # Console table formatting
├── tests/                              # Test files
│   ├── test_enhanced_exporter.py       # Enhanced exporter tests
│   ├── test_mock_integration.py        # Mock integration tests
│   └── test_validation_engine.py       # Validation engine tests
├── examples/                           # Example data and scripts
│   ├── data/                           # Sample data files
│   │   ├── example_enhanced_data.json  # Enhanced mock data example
│   │   ├── sample_test_results.json    # Sample test results
│   │   └── enhanced_test_export.json   # Enhanced export example
│   └── scripts/                        # Example scripts
│       ├── quick_mock_test.py          # Quick mock server test
│       └── run_mock_tests.py           # Mock testing script
├── data/                               # Runtime data storage
│   ├── test_results/                   # Test execution results
│   ├── logs/                           # Application logs
│   └── kubectl_logs/                   # Kubernetes logs
├── scripts/                            # Build and utility scripts
├── docs/                               # Documentation
├── config/                             # Configuration files
├── requirements.txt                    # Python dependencies
├── setup.py                            # Package installation
└── README.md                           # This file
```

## 🚀 Quick Start

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd testPilotOne
   ```

2. **Set up virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install package in development mode:**
   ```bash
   pip install -e .
   ```

### Basic Usage

#### 1. Enhanced Test Results Export

```python
from testpilot.exporters.test_results_exporter import TestResultsExporter

# Export test results with enhanced fields
exporter = TestResultsExporter()
json_file = exporter.export_to_json(test_results)  # Includes row_index, pattern_match, response_body
csv_file = exporter.export_to_csv(test_results)    # Excel column support
```

#### 2. Enhanced Mock Server

```python
from testpilot.mock.enhanced_mock_server import EnhancedMockServer

# Start mock server with dictionary format support
server = EnhancedMockServer(
    enhanced_data_file="examples/data/example_enhanced_data.json",
    port=8082
)
server.run()
```

#### 3. Enhanced Mock Data Export

```python
from testpilot.mock.enhanced_mock_exporter import EnhancedMockExporter

# Export test results to enhanced mock data format
exporter = EnhancedMockExporter()
enhanced_file = exporter.export_enhanced_mock_data(
    "test_results.json",
    use_dictionary_format=True  # Test names as keys
)
```

## 🎯 Key Features

### Enhanced Test Results Export
- **Row Index**: 1-based indexing for easy reference
- **Pattern Match**: Direct from Excel `Pattern_Match` column
- **Response Body**: Direct from Excel `Response_Payload` column
- **Content Analysis**: Automatic JSON parsing and content type detection
- **Summary Statistics**: Pattern matching and response analysis metrics

### Enhanced Mock Server
- **Dictionary Format**: Test names as keys in `enhanced_results`
- **Dual Format Support**: Both list and dictionary formats
- **Primary Mapping**: `sheet_name::test_name` combinations
- **API Endpoints**:
  - `GET /mock/test/<test_name>` - Retrieve by test name
  - `GET /mock/test/<sheet_name>/<test_name>` - Retrieve by sheet + test
  - `GET /mock/tests` - List all tests
  - `GET /mock/sheets` - List all sheets

### Excel Integration
- **Pattern_Match Column**: Direct pattern matching data
- **Response_Payload Column**: Direct response body data
- **Intelligent Parsing**: Handles various Excel data formats
- **Content Type Detection**: Automatic JSON/HTML/text classification

## 📊 Enhanced Data Formats

### Enhanced JSON Export Structure
```json
{
  "row_index": 1,
  "pattern_match": {
    "raw_pattern_match": "subscription_creation_pattern",
    "matched": true,
    "pattern_type": "subscription",
    "confidence_score": 0.8,
    "from_excel_column": true
  },
  "response_body": {
    "raw_payload": "{\"subscription_id\":\"sub_67890\"}",
    "parsed_json": {"subscription_id": "sub_67890"},
    "content_type": "application/json",
    "size_bytes": 85,
    "from_excel_column": true
  }
}
```

### Enhanced Mock Data Format
```json
{
  "enhanced_results": {
    "test_auto_create_subs_1": {
      "sheet_name": "AutoCreateSubs",
      "test_name": "test_auto_create_subs_1",
      "request": {...},
      "expected_response": {...}
    }
  }
}
```

## 🧪 Testing

Run the test suite to verify the installation:

```bash
# Test enhanced exporter
python tests/test_enhanced_exporter.py

# Test mock integration
python tests/test_mock_integration.py
```

## 📝 Excel Column Support

The enhanced exporter now reads directly from Excel columns:

| Excel Column | Usage | Description |
|-------------|-------|-------------|
| `Pattern_Match` | Pattern matching data | YES/NO, pattern names, custom values |
| `Response_Payload` | Response body data | JSON, HTML, text responses |
| Standard columns | Test metadata | Host, Sheet, Test Name, Method, etc. |

## 🔧 Command Line Tools

After installation, you can use:

```bash
# Main test execution
testpilot

# Start enhanced mock server
testpilot-mock --port 8082 --data-file examples/data/example_enhanced_data.json

# Export enhanced mock data
testpilot-export input_results.json --format dictionary
```

## 📖 Documentation

- [Enhanced Mock Server Guide](docs/ENHANCED_MOCK_SERVER.md)
- [Test Results Export Guide](docs/TEST_RESULTS_EXPORT.md)
- [Excel Integration Guide](docs/EXCEL_INTEGRATION.md)
- [API Reference](docs/API_REFERENCE.md)

## 🤝 Contributing

1. Follow the established directory structure
2. Update imports when moving files
3. Add tests for new functionality
4. Update documentation

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**TestPilot** - Making API testing comprehensive, reliable, and Excel-friendly! 🚀
