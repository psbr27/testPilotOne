# TestPilot Deployment Guide

## Quick Start

### 1. Extract and Setup

```bash
# Extract the distribution
tar -xzf testpilot_dist.tar.gz
cd testPilot/

# Run the interactive setup
./setup_testpilot.sh
```

### 2. Run Your First Test

```bash
# Check version and configuration
./testPilot -v

# Run all tests in your Excel file
./testPilot -i your_tests.xlsx -m otp

# Run a specific sheet in excel
./testPilot -i your_tests.xlsx -m otp -s "Sheet_Name"
```

### 3. View Results

Results are automatically generated in:
- `test_results_*.xlsx` - Detailed Excel report
- `test_results/test_results_*.html` - Visual HTML report

## Overview

TestPilot is an automated testing framework designed for 5G Core Network Functions. This guide covers both quick start and detailed deployment instructions.

### What TestPilot Does
- Executes test scenarios defined in Excel spreadsheets
- Connects to Kubernetes clusters via SSH or locally
- Captures kubectl logs during test execution
- Validates responses against expected patterns
- Generates comprehensive test reports in Excel and HTML formats

## Prerequisites

### System Requirements
- Linux system
- Kubernetes cluster access (via kubectl)
- SSH access to cluster nodes (if using SSH mode)
- Excel files with test scenarios

### Required Access
- kubectl configured with appropriate permissions
- SSH keys or passwords for remote hosts (if applicable)
- Namespace access in Kubernetes cluster

## Installation

### Step 1: Extract the Distribution

```bash
# Extract the TestPilot distribution
tar -xzf testpilot_dist.tar.gz
cd testPilot/

# Verify the extraction
ls -la
# You should see:
# - testPilot (executable)
# - _internal/ (dependencies)
# - config/ (configuration directory)
# - setup_testpilot.sh (setup assistant)
```

### Step 2: Run the Setup Assistant

We provide an interactive setup script to help configure TestPilot:

```bash
./setup_testpilot.sh
```

The script will guide you through:
1. Selecting your Network Function type (AMF, SMF, UPF, etc.)
2. Configuring connection settings (SSH or local kubectl)
3. Setting up host configurations
4. Generating the `config/hosts.json` file

### Step 3: Manual Configuration (Optional)

If you prefer manual configuration, edit `config/hosts.json`:

```json
{
    "use_ssh": false,
    "pod_mode": false,
    "nf_name": "my-amf",
    "connect_to": "all",
    "system_under_test": {
        "nf_type": "AMF",
        "version": "v23.4.x",
        "environment": "Test Lab",
        "deployment": "Kubernetes Cluster"
    },
    "hosts": [
        {
            "name": "test-cluster-1",
            "hostname": "10.0.0.100",
            "username": "k8s-user",
            "key_file": "~/.ssh/id_rsa",
            "password": null,
            "namespace": "ocxxx-amf",
            "port": 22
        }
    ]
}
```

#### Key Configuration Fields

- **nf_name**: Name of your Network Function
- **connect_to**: Which hosts to connect to ("all" or specific host name)
- **namespace**: Kubernetes namespace for your NF
- **system_under_test**: Metadata about your deployment


## Running TestPilot

### Basic Usage

```bash
./testPilot -i <excel-file> -m <module>
```

### Command Line Options

| Option | Description | Required | Example |
|--------|-------------|----------|---------|
| `-i, --input` | Path to Excel test file | Yes | `-i tests/amf_tests.xlsx` |
| `-m, --module` | Test module type | Yes | `-m otp` |
| `-s, --sheet` | Specific sheet(s) to run | No | `-s "Sheet1,Sheet2"` |
| `-t, --test-name` | Specific test to run | No | `-t "Test_AMF_Registration"` |
| `-v, --version` | Show version info | No | `-v` |
| `--dry-run` | Preview commands without execution | No | `--dry-run` |
| `--log-level` | Set logging verbosity | No | `--log-level DEBUG` |
| `--display-mode` | UI display mode | No | `--display-mode simple` |
| `--step-delay` | Delay between test steps | No | `--step-delay 2` |
| `--no-table` | Disable result table output | No | `--no-table` |

### Module Types

- **otp**: One-Time Provisioning tests

### Examples

```bash
# Run all tests in an Excel file
./testPilot -i test_scenarios.xlsx -m otp

# Run specific sheet
./testPilot -i test_scenarios.xlsx -m otp -s "AMF_Tests"

# Run specific test with debug logging
./testPilot -i test_scenarios.xlsx -m otp -t "Test_Registration" --log-level DEBUG

# Dry run to preview commands
./testPilot -i test_scenarios.xlsx -m otp --dry-run

# Run with simple display mode (no fancy UI)
./testPilot -i test_scenarios.xlsx -m otp --display-mode simple
```

## Understanding Results

### Directory Structure After Execution

```
testPilot/
├── logs/                    # Execution logs (for debugging)
│   └── testpilot_YYYYMMDD_HHMMSS.log
├── kubectl_logs/           # Captured Kubernetes logs (for debugging)
│   └── <test>_<timestamp>/
├── test_results/           # Main results directory
│   ├── raw_results_YYYYMMDD_HHMMSS.json
│   ├── test_results_YYYYMMDD_HHMMSS.xlsx  # Final report
│   └── test_results_YYYYMMDD_HHMMSS.html  # HTML report
```

### Result Files

1. **Excel Report** (`test_results_*.xlsx`)
   - Comprehensive test results
   - Pass/Fail status for each test
   - Actual vs Expected comparisons
   - Execution timestamps
   - Error details if any

2. **HTML Report** (`test_results_*.html`)
   - Visual representation of results
   - Easy to share with stakeholders
   - Color-coded pass/fail indicators

### Understanding Test Results

- **PASSED**: Test executed successfully and response matched expected pattern
- **FAILED**: Test executed but response didn't match expected pattern
- **ERROR**: Test couldn't execute due to connectivity or command issues
- **SKIPPED**: Test was skipped (dependency failed or dry-run mode)


### Quick Reference

```bash
# Version check
./testPilot -v

# Basic run
./testPilot -i tests.xlsx -m otp

# Run specific sheet
./testPilot -i tests.xlsx -m otp -s "Sheet1"

# Run multiple sheets
./testPilot -i tests.xlsx -m otp -s "Sheet1,Sheet2"

# Run specific test
./testPilot -i tests.xlsx -m otp -t "MyTest"

# Dry run (preview without executing)
./testPilot -i tests.xlsx -m otp --dry-run

# Debug mode
./testPilot -i tests.xlsx -m otp --log-level DEBUG

# Simple display mode (no fancy UI)
./testPilot -i tests.xlsx -m otp --display-mode simple

# Results location
ls test_results/test_results_*.xlsx
```
