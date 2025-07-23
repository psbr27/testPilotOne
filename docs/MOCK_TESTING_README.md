# TestPilot Mock Testing System

## 🎯 Overview

The TestPilot Mock Testing System allows you to run tests locally using mock servers instead of connecting to remote systems. This enables fast, reliable testing without external dependencies.

## 📋 Prerequisites

- Python 3.8+
- Required packages: `flask`, `requests`, `pandas`, `openpyxl`
- TestPilot project setup

## 🔧 Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Ensure Test Results Data
You need original test results JSON file from a real TestPilot run:
```
mock_data/test_results_20250719_122220.json
```

## 🚀 Quick Start

### Complete Workflow (3 Steps)

```bash
# 1. Generate Enhanced Mock Data
python3 enhanced_mock_exporter.py mock_data/test_results_20250719_122220.json

# 2. Start Enhanced Mock Server
python3 enhanced_mock_server.py --port 8082 &

# 3. Run TestPilot with Mock Mode
python3 test_pilot.py -i Oracle_VzW_OCSLF_23.4.x_Auto_OTP_v1.2.xlsx -m otp --execution-mode mock -s oAuthValidation-igw
```

## 📊 Mock Data Generation

### Enhanced Mock Exporter

**Purpose:** Converts raw test results into structured mock data with accurate HTTP status codes.

**Command:**
```bash
python3 enhanced_mock_exporter.py <input_file> [output_file]
```

**Examples:**
```bash
# Basic usage (auto-generates output filename)
python3 enhanced_mock_exporter.py mock_data/test_results_20250719_122220.json

# Specify custom output file
python3 enhanced_mock_exporter.py mock_data/test_results_20250719_122220.json mock_data/my_enhanced_data.json
```

**Output:**
- Creates: `mock_data/enhanced_test_results_20250719_122220.json`
- Structured data with sheet names, test names, actual HTTP status codes
- Ready for enhanced mock server

## 🖥️ Mock Servers

### Enhanced Mock Server (Recommended)

**Features:**
- Sheet-aware response targeting
- Test-specific response mapping
- Accurate HTTP status codes
- Enhanced debugging

**Command:**
```bash
python3 enhanced_mock_server.py [options]
```

**Options:**
```bash
--port PORT               Port to run server (default: 8082)
--host HOST              Host to bind to (default: 0.0.0.0)
--data-file FILE         Enhanced mock data file
--debug                  Enable Flask debug mode
```

**Examples:**
```bash
# Start with default settings
python3 enhanced_mock_server.py --port 8082

# Start with custom data file
python3 enhanced_mock_server.py --port 8082 --data-file mock_data/my_enhanced_data.json

# Start in background
python3 enhanced_mock_server.py --port 8082 > mock_server.log 2>&1 &
```

### Generic Mock Server (Legacy)

**Features:**
- Basic endpoint matching
- Generic response generation
- Simpler setup

**Command:**
```bash
python3 generic_mock_server.py [options]
```

**Options:**
```bash
--port PORT               Port to run server (default: 8081)
--host HOST              Host to bind to (default: 0.0.0.0)
--data-file FILE         Original test results file
--debug                  Enable Flask debug mode
```

**Example:**
```bash
python3 generic_mock_server.py --port 8081 --data-file mock_data/test_results_20250719_122220.json
```

## 🧪 Running Tests with Mock Mode

### TestPilot Mock Mode

**Command:**
```bash
python3 test_pilot.py [options] --execution-mode mock
```

**Key Options:**
```bash
-i, --input FILE          Excel file with test cases
-m, --model MODEL         Model/pattern to use
-s, --sheet SHEET         Specific sheet(s) to test. Supports comma-separated values: 'sheet1,sheet2' or bracket format: '[sheet1,sheet2]'
--execution-mode mock     Enable mock mode
--mock-server-url URL     Mock server URL (default: http://localhost:8082)
--log-level LEVEL         Logging level (DEBUG, INFO, WARNING, ERROR)
```

### Examples

#### Test Specific Sheet
```bash
python3 test_pilot.py -i Oracle_VzW_OCSLF_23.4.x_Auto_OTP_v1.2.xlsx -m otp --execution-mode mock -s oAuthValidation-igw
```

#### Test Multiple Sheets
```bash
# Comma-separated format
python3 test_pilot.py -i Oracle_VzW_OCSLF_23.4.x_Auto_OTP_v1.2.xlsx -m otp --execution-mode mock -s oAuthValidation-igw,Registration-igw

# Bracket format
python3 test_pilot.py -i Oracle_VzW_OCSLF_23.4.x_Auto_OTP_v1.2.xlsx -m otp --execution-mode mock -s "[oAuthValidation-igw, Registration-igw]"
```

#### Test All Sheets
```bash
python3 test_pilot.py -i Oracle_VzW_OCSLF_23.4.x_Auto_OTP_v1.2.xlsx -m otp --execution-mode mock
```

#### Use Custom Mock Server
```bash
python3 test_pilot.py -i Oracle_VzW_OCSLF_23.4.x_Auto_OTP_v1.2.xlsx -m otp --execution-mode mock --mock-server-url http://localhost:8081
```

#### Debug Mode
```bash
python3 test_pilot.py -i Oracle_VzW_OCSLF_23.4.x_Auto_OTP_v1.2.xlsx -m otp --execution-mode mock -s oAuthValidation-igw --log-level DEBUG
```

## 🔍 Debugging and Monitoring

### Mock Server Health Check
```bash
curl http://localhost:8082/health
```

### View Available Sheets
```bash
curl http://localhost:8082/mock/sheets
```

### View Tests for Specific Sheet
```bash
curl http://localhost:8082/mock/tests?sheet=oAuthValidation-igw
```

### View All Response Mappings
```bash
curl http://localhost:8082/mock/mappings
```

### Monitor Server Logs
```bash
# If running in background
tail -f mock_server.log

# Real-time logs
python3 enhanced_mock_server.py --port 8082  # (foreground)
```

## 📋 Process Management

### Start Mock Server in Background
```bash
python3 enhanced_mock_server.py --port 8082 > mock_server.log 2>&1 &
echo $! > mock_server.pid  # Save process ID
```

### Stop Mock Server
```bash
# If you saved the PID
kill $(cat mock_server.pid)

# Kill by process name
pkill -f "enhanced_mock_server.py"

# Kill specific port
lsof -ti:8082 | xargs kill
```

### Check Running Servers
```bash
# Check what's running on port 8082
lsof -i :8082

# List all mock server processes
ps aux | grep mock_server
```

## 🎯 Advanced Usage

### Multiple Servers
```bash
# Enhanced server (recommended)
python3 enhanced_mock_server.py --port 8082 > enhanced.log 2>&1 &

# Generic server (fallback)
python3 generic_mock_server.py --port 8081 > generic.log 2>&1 &

# Use enhanced server
python3 test_pilot.py -i tests.xlsx -m otp --execution-mode mock --mock-server-url http://localhost:8082
```

### Custom Data Pipeline
```bash
# 1. Export from real run
python3 test_pilot.py -i tests.xlsx -m otp  # Creates test_results_YYYYMMDD_HHMMSS.json

# 2. Generate enhanced data
python3 enhanced_mock_exporter.py test_results_YYYYMMDD_HHMMSS.json

# 3. Start server with new data
python3 enhanced_mock_server.py --port 8082 --data-file enhanced_test_results_YYYYMMDD_HHMMSS.json

# 4. Run mock tests
python3 test_pilot.py -i tests.xlsx -m otp --execution-mode mock
```

## 🔧 Configuration

### Default Ports
- **Enhanced Mock Server:** 8082 (recommended)
- **Generic Mock Server:** 8081 (legacy)
- **TestPilot Default:** http://localhost:8082

### Default Files
- **Input Data:** `mock_data/test_results_20250719_122220.json`
- **Enhanced Data:** `mock_data/enhanced_test_results_20250719_122220.json`
- **Logs:** `mock_server.log`

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Check what's using the port
lsof -i :8082

# Kill the process
lsof -ti:8082 | xargs kill

# Use different port
python3 enhanced_mock_server.py --port 8083
python3 test_pilot.py ... --mock-server-url http://localhost:8083
```

### Server Not Responding
```bash
# Check if server is running
curl http://localhost:8082/health

# Check logs
tail -f mock_server.log

# Restart server
pkill -f "enhanced_mock_server.py"
python3 enhanced_mock_server.py --port 8082 &
```

### Wrong Status Codes
```bash
# Regenerate enhanced data (fixes HTTP status codes)
python3 enhanced_mock_exporter.py mock_data/test_results_20250719_122220.json

# Restart server with new data
pkill -f "enhanced_mock_server.py"
python3 enhanced_mock_server.py --port 8082 &
```

### Data File Not Found
```bash
# Check if file exists
ls -la mock_data/

# Generate enhanced data if missing
python3 enhanced_mock_exporter.py mock_data/test_results_20250719_122220.json
```

## 📊 Expected Results

### Success Rates
- **Original (no mock):** Variable based on environment
- **Generic Mock Server:** ~40-50% (basic matching)
- **Enhanced Mock Server:** ~80%+ (accurate status codes and targeting)

### Log Output
```
🔄 Mock request: GET http://localhost:8082/nudr-group-id-map/v1/nf-group-ids?subscriber-id=imsi-302720603940001&nf-type=UDM&{sheet=oAuthValidation-igw & test=test_oauth_validation_igw_1}
✅ Mock response: 200 (0.001s)
```

### Test Results
```
Total Tests: 10
✓ Passed: 8
✗ Failed: 2
Success Rate: 80.0%
```

## 🔗 Related Files

- `enhanced_mock_exporter.py` - Enhanced data generator
- `enhanced_mock_server.py` - Advanced mock server
- `generic_mock_server.py` - Basic mock server
- `mock_integration.py` - TestPilot mock integration
- `test_pilot.py` - Main test runner
- `mock_data/` - Mock data directory

## ✅ Best Practices

1. **Always use Enhanced Mock Server** for better accuracy
2. **Regenerate enhanced data** when test results change
3. **Monitor server logs** for debugging
4. **Use specific sheets** (`-s`) for focused testing
5. **Check health endpoint** before running tests
6. **Clean up processes** when done testing

---

## 🎉 Quick Reference

### Essential Commands
```bash
# Generate enhanced data
python3 enhanced_mock_exporter.py mock_data/test_results_20250719_122220.json

# Start enhanced server
python3 enhanced_mock_server.py --port 8082 &

# Run specific test sheet
python3 test_pilot.py -i Oracle_VzW_OCSLF_23.4.x_Auto_OTP_v1.2.xlsx -m otp --execution-mode mock -s oAuthValidation-igw

# Health check
curl http://localhost:8082/health

# Stop server
pkill -f "enhanced_mock_server.py"
```

**Happy Mock Testing! 🚀**
