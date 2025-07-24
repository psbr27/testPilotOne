# TestPilot Features

TestPilot is a comprehensive API test automation framework with Excel-based test definitions and support for both production and mock environments.

## Core Features

### Test Execution
- **Excel-based test definitions**: Define tests in `.xlsx` files with structured format
- **Multiple execution modes**: Production (SSH/kubectl) and mock server modes
- **Pattern matching**: Advanced log and response validation with regex support
- **Test sequencing**: NRF instance tracking and request sequence management

### Reporting & Export
- **HTML reports**: NF-style reports with pass rates, glossy bars, and interactive filtering
- **Multiple export formats**: JSON, CSV, Excel output support
- **Real-time dashboards**: Terminal UI with blessed/rich display modes
- **Test results analysis**: Comprehensive validation and failure tracking

### Infrastructure Integration
- **SSH connectivity**: Remote command execution via Paramiko
- **Kubernetes support**: kubectl integration with real-time log capture
- **Mock server**: Enhanced mock server for local testing
- **Multiple sheet support**: Process multiple test sheets via CLI `-s` option

### Recent Enhancements
- **NF instance discovery**: JSON file-based discovery mechanism
- **Double delete scenario analysis**: NRF-specific test scenarios
- **Excel validation module**: Comprehensive test data validation tools
- **Interactive HTML reports**: Filtering and improved UI/UX
- **Real-time log capture**: Fixed kubectl logs to capture in real-time
- **Pattern matching improvements**: Fixed double quote issues and header parsing

### Developer Tools
- **Debug utilities**: Enhanced debugging capabilities
- **Mock data exporter**: Export and manage mock test data
- **Validation engine**: Response validation with JSON matching
- **Console formatting**: Rich table displays and progress indicators
