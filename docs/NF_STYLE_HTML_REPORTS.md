# NF-Style HTML Reports

## Overview

The TestPilot framework now supports two HTML report styles:

1. **Standard Style** - The original interactive HTML reports with detailed charts and filtering
2. **NF-Style** - A new Network Function focused layout designed for telecommunications testing

## Features

### NF-Style Report Layout

The NF-style reports provide a cleaner, more focused layout specifically designed for Network Function testing:

- **Header Section**: `<NF> Test Report` title with timestamp
- **System Under Test**: Configurable information about the NF being tested
- **Overall Summary**: Simple Pass/Fail counts (`Pass = xx, fail = xx` format)
- **Bar Chart**: Primary visualization showing test results by sheet
- **Sheet Results**: Simplified table showing sheet names with pass/fail status
- **Test Details**: Focused layout with specific fields for telecommunications testing

### Key Differences from Standard Reports

| Feature | Standard Style | NF-Style |
|---------|---------------|----------|
| **Title** | "Test Results Report" | "`<NF>` Test Report" |
| **Charts** | Pie charts + bar chart | Bar chart primary |
| **Summary** | Multiple metrics | Simple Pass/Fail counts |
| **Layout** | Complex tabbed interface | Linear, focused layout |
| **Test Details** | Generic fields | Telecom-specific fields |
| **Filtering** | Yes (All/Pass/Fail) | No (simplified) |
| **System Info** | Not shown | Configurable NF details |

## Configuration

### Enabling NF-Style Reports

Edit your `config/hosts.json` file to enable NF-style reports:

```json
{
    "html_generator": {
        "use_nf_style": true,
        "_comment": "Set to true for NF-style HTML reports, false for standard reports"
    },
    "system_under_test": {
        "nf_type": "AMF (Access and Mobility Management Function)",
        "version": "v23.4.x",
        "environment": "5G Core Test Lab Environment",
        "deployment": "Kubernetes Cluster - Test Environment",
        "description": "5G Core Network Function - Access and Mobility Management Function responsible for handling UE registration, authentication, and mobility management"
    }
}
```

### Configuration Options

#### html_generator
- **use_nf_style** (boolean): Enable/disable NF-style reports
  - `true`: Use NF-style layout
  - `false`: Use standard layout (default)

#### system_under_test
- **nf_type**: Type of Network Function (e.g., "AMF", "SMF", "UPF")
- **version**: Software version (e.g., "v23.4.x")
- **environment**: Test environment description
- **deployment**: Deployment type (e.g., "Kubernetes", "Docker")
- **description**: Detailed description of the NF

## Test Details Layout

### NF-Style Test Details

The NF-style reports show test details in a structured grid format:

```
┌─────────────────────┬─────────────────────────────┐
│ Command             │ HTTP Response From Server   │
├─────────────────────┼─────────────────────────────┤
│ Pattern to match    │ Expected HTTP status        │
├─────────────────────┼─────────────────────────────┤
│ HTTP status from    │ HTTP status Validation      │
│ server              │ result (with green for PASS)│
├─────────────────────┴─────────────────────────────┤
│ Output from server (full width section)          │
└───────────────────────────────────────────────────┘
```

### Field Descriptions

- **Command**: The HTTP request/curl command executed
- **HTTP Response From Server**: Raw response data from the server
- **Pattern to match**: Expected pattern for validation
- **Expected HTTP status**: Expected HTTP status code
- **HTTP status from server**: Actual HTTP status received
- **HTTP status Validation result**: Pass/Fail result (green background for PASS)
- **Output from server**: Complete server response output

## Usage Examples

### Programmatic Usage

```python
from testpilot.exporters.html_report_generator import HTMLReportGenerator

# Create generator
html_generator = HTMLReportGenerator("test_results")

# Load config
config = html_generator._load_config()

# Generate NF-style report
if config.get("html_generator", {}).get("use_nf_style", False):
    html_file = html_generator.export_to_nf_html(test_results, "nf_report.html", config)
else:
    html_file = html_generator.export_to_html(test_results, "standard_report.html")
```

### Automatic Selection

The TestResultsExporter automatically selects the appropriate style based on configuration:

```python
from testpilot.exporters.test_results_exporter import TestResultsExporter

exporter = TestResultsExporter("test_results")
# Automatically uses NF-style if configured
html_file = exporter.export_to_html(test_results, open_browser=True)
```

## Demo Script

A demo script is provided to test both report styles:

```bash
python3 test_nf_html_demo.py
```

This generates sample test results and creates both NF-style and standard reports for comparison.

## Interactive Features

### Retained Features
- **Collapsible sections**: Click sheet names to expand/collapse detailed results
- **Test group expansion**: Click test groups to view detailed test steps
- **Bar chart visualization**: Interactive chart showing pass/fail by sheet

### Removed Features (for simplicity)
- **Filter buttons**: No All/Pass/Fail filtering in NF-style
- **Pie charts**: Replaced with bar chart focus
- **Complex tabbed interface**: Simplified to linear layout

## Browser Compatibility

NF-style reports are compatible with:
- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+

## File Structure

```
src/testpilot/exporters/
├── html_report_generator.py    # Both standard and NF-style generators
├── test_results_exporter.py    # Automatic style selection
└── __init__.py

config/
├── hosts.json                  # Configuration file
└── hosts.json.template         # Template with examples

test_results/
├── nf_style_report_*.html      # Generated NF-style reports
└── standard_report_*.html      # Generated standard reports
```

## Best Practices

1. **Use NF-style for**: Telecommunications testing, 5G core testing, formal test reports
2. **Use Standard style for**: General API testing, development testing, detailed analysis
3. **Configure system_under_test**: Provide meaningful information about your NF
4. **Test both styles**: Use the demo script to compare layouts
5. **Version control**: Keep separate configs for different environments

## Troubleshooting

### Common Issues

**Q: NF-style not showing despite configuration**
A: Check that `use_nf_style` is set to `true` (boolean, not string)

**Q: System Under Test section empty**
A: Verify `system_under_test` object exists in config with required fields

**Q: Charts not displaying**
A: Ensure Chart.js CDN is accessible (requires internet connection)

**Q: HTML file empty or corrupted**
A: Check file permissions and disk space in test_results directory

### Debug Steps

1. Run demo script to verify installation
2. Check config file syntax with JSON validator
3. Verify test_results directory permissions
4. Test with minimal config first

## Migration Guide

### From Standard to NF-Style

1. Add `html_generator` section to config
2. Add `system_under_test` section with your NF details
3. Set `use_nf_style: true`
4. Test with existing test results
5. Compare outputs and adjust as needed

### Maintaining Both Styles

Keep two config files:
- `config/hosts_standard.json` (use_nf_style: false)
- `config/hosts_nf.json` (use_nf_style: true)

Switch between them as needed for different testing scenarios.
