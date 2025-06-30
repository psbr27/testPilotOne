# TestPilot Logging Guide

TestPilot now provides comprehensive logging capabilities with both console and file output, including structured failure logging for automated analysis.

## 📊 Logging Overview

### Current Logging Behavior

When TestPilot runs, it creates several types of logs:

1. **Console Output**: Real-time feedback during test execution
2. **General Log File**: All log messages with timestamps
3. **Failure Log File**: Only errors and failures for detailed analysis
4. **Structured Failure Log**: Machine-readable failure data
5. **Excel Results**: Test results exported to spreadsheet format

## 📁 Log File Structure

```
logs/
├── testpilot_YYYYMMDD_HHMMSS.log           # General log file
├── testpilot_failures_YYYYMMDD_HHMMSS.log  # All failures and errors
└── test_failures_YYYYMMDD_HHMMSS.log       # Structured failure data
```

## 🔍 Log File Contents

### 1. General Log File (`testpilot_*.log`)
Contains all logging information:
- INFO: Test progress, configuration, summaries
- ERROR: Test failures, system errors
- DEBUG: Detailed execution information

**Example:**
```
[2024-01-15 10:30:15] [INFO] [TestPilot] [test_pilot.py:25] - TestPilot started with args: ...
[2024-01-15 10:30:16] [ERROR] [TestPilot.Core] [test_pilot_core.py:248] - [FAIL][Sheet1][row 5][host1] Command: curl -X GET https://api.example.com/users
[2024-01-15 10:30:16] [ERROR] [TestPilot.Core] [test_pilot_core.py:249] - Reason: Status mismatch: 404 vs 200
```

### 2. Failure Log File (`testpilot_failures_*.log`)
Contains only ERROR level messages:
- Failed test details
- System error messages
- Configuration issues

### 3. Structured Failure Log (`test_failures_*.log`)
Machine-readable format for automated analysis:
```
2024-01-15 10:30:16|ERROR|SHEET=Sheet1|ROW=5|HOST=host1|TEST_NAME=User_API_Test|COMMAND=curl -X GET https://api.example.com/users|REASON=Status mismatch: 404 vs 200|EXPECTED_STATUS=200|ACTUAL_STATUS=404|PATTERN_MATCH=|PATTERN_FOUND=None|OUTPUT_LENGTH=156|ERROR_LENGTH=0
```

## ⚙️ Command Line Options

Control logging behavior with these options:

```bash
# Default behavior (console + files)
python test_pilot.py --input test.xlsx --module config

# Console only (no files)
python test_pilot.py --input test.xlsx --module config --no-file-logging

# Custom log directory
python test_pilot.py --input test.xlsx --module config --log-dir /var/log/testpilot

# Debug level logging
python test_pilot.py --input test.xlsx --module config --log-level DEBUG
```

### Available Options:
- `--no-file-logging`: Disable file logging (console only)
- `--log-dir DIR`: Specify custom log directory (default: `logs`)
- `--log-level LEVEL`: Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

## 📈 Log Analysis

Use the built-in log analyzer to understand failure patterns:

```bash
# Analyze logs in default directory
python log_analyzer.py

# Analyze logs in custom directory
python log_analyzer.py --log-dir /var/log/testpilot

# Generate Excel report
python log_analyzer.py --export
python log_analyzer.py --export --output failure_report.xlsx
```

### Analysis Features:
- **Failure by Sheet**: Which test sheets have the most failures
- **Failure by Host**: Which hosts are most problematic
- **Top Failure Reasons**: Most common error messages
- **Status Code Issues**: HTTP status code problems
- **Pattern Match Failures**: Pattern matching issues
- **Problematic Commands**: Commands that fail most often

## 🔧 Programmatic Access

### Reading Structured Logs

```python
from log_analyzer import TestPilotLogAnalyzer

analyzer = TestPilotLogAnalyzer("logs")
analyzer.load_failure_logs()
analysis = analyzer.analyze_failure_patterns()

print(f"Total failures: {analysis['total_failures']}")
print(f"Top failing sheet: {analysis['failure_by_sheet'].most_common(1)}")
```

### Custom Log Processing

```python
import pandas as pd

# Load structured failure log
def parse_failure_log(file_path):
    failures = []
    with open(file_path, 'r') as f:
        for line in f:
            parts = line.strip().split('|')
            if len(parts) >= 3:
                failure_data = {}
                for part in parts[2:]:  # Skip timestamp and level
                    if '=' in part:
                        key, value = part.split('=', 1)
                        failure_data[key] = value
                failures.append(failure_data)
    return pd.DataFrame(failures)

df = parse_failure_log('logs/test_failures_20240115_103015.log')
print(df.groupby('SHEET')['ROW'].count())
```

## 📋 Best Practices

### 1. Log Retention
- Clean up old log files periodically
- Archive important failure logs for trend analysis
- Use log rotation for long-running environments

### 2. Monitoring
- Monitor failure logs for recurring issues
- Set up alerts for high failure rates
- Review structured logs for automation opportunities

### 3. Debugging
- Use DEBUG level for troubleshooting specific issues
- Check both general and failure logs for complete context
- Correlate timestamps between different log files

### 4. Analysis
- Run log analysis after each test cycle
- Export to Excel for sharing with team
- Track failure trends over time

## 🚨 Troubleshooting

### Permission Issues
If log files cannot be created:
```bash
# Create logs directory with proper permissions
mkdir -p logs
chmod 755 logs

# Or use console-only logging
python test_pilot.py --input test.xlsx --module config --no-file-logging
```

### Disk Space
Large test runs generate significant logs:
- Monitor disk space in log directory
- Use log rotation for continuous testing
- Clean up old logs regularly

### Log Analysis Issues
If log analyzer fails:
- Check log file permissions
- Verify log file format
- Use --log-dir to specify correct directory

## 📊 Sample Analysis Output

```
================================================================================
TESTPILOT FAILURE ANALYSIS REPORT
================================================================================
Generated: 2024-01-15 14:30:25
Total Failures Analyzed: 23

TOP FAILURE PATTERNS:
----------------------------------------
Failures by Sheet:
  UserAPI_Tests: 8
  ConfigAPI_Tests: 7
  AuthAPI_Tests: 5
  HealthCheck_Tests: 3

Failures by Host:
  prod-server-1: 12
  staging-server-2: 8
  dev-server-1: 3

Top Failure Reasons:
  Status mismatch: 404 vs 200: 9
  Pattern 'success' not found in response: 6
  Connection timeout: 4
  Status mismatch: 500 vs 200: 4

Status Code Issues:
  Status 404: 9
  Status 500: 4
  Status 401: 3
  Status 0: 4

Pattern Match Failures: 6

Most Problematic Commands:
  curl -X GET https://api.example.com/users: 9
  curl -X POST https://api.example.com/auth/login: 6
  kubectl logs pod-name: 4
```

This comprehensive logging system helps you understand test failures, track trends, and improve test reliability over time.