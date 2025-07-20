# TestPilot

TestPilot is a comprehensive test automation framework designed for API testing with Excel-based test definitions.

## Features

- **Excel-based test definitions**: Define tests using structured Excel spreadsheets
- **Mock server support**: Built-in mock server for testing without live services
- **Multiple execution modes**: Production (SSH/kubectl) and mock execution modes
- **Rich reporting**: Export results to HTML, JSON, CSV, and Excel formats
- **Pattern matching**: Advanced pattern matching for log analysis
- **Dashboard displays**: Multiple display modes including blessed terminal UI

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
├── src/testpilot/          # Main package
│   ├── core/               # Core test execution
│   ├── mock/               # Mock server components
│   ├── exporters/          # Export functionality
│   ├── ui/                 # User interface components
│   └── utils/              # Utility functions
├── tests/                  # Test files
├── examples/               # Example data and scripts
├── config/                 # Configuration files
└── docs/                   # Documentation
```

## Requirements

- Python 3.8+
- See `requirements.txt` for dependencies

## License

MIT License
