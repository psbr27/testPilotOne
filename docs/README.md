# TestPilot

A modular, workflow-aware test automation framework for orchestrating multi-step, multi-host API and Kubernetes validation scenarios. Built for flexibility, maintainability, and extensibility in modern cloud-native environments.

## 🔧 Requirements

- **Python 3.8+** (tested on Python 3.8, 3.9, 3.10, 3.11, 3.12)
- Dependencies listed in `requirements.txt`

## 🎨 Code Formatting

This project uses automated code formatting tools to maintain consistent code style:

- **Black**: Python code formatter with 79-character line length
- **isort**: Import sorting and organization
- **pre-commit**: Git hooks for automatic formatting

### Setup Pre-commit Hooks

To set up the pre-commit hooks for development:

```bash
# Install dependencies (if not already installed)
pip install -r requirements.txt

# Install pre-commit hooks
pre-commit install

# Optionally, run on all files to format existing code
pre-commit run --all-files
```

The pre-commit hooks will automatically run Black and isort on your code before each commit, ensuring consistent formatting across the project.

---

## Features

- **Multi-Step Workflow Execution:**
  - Supports complex test flows with stateful context sharing between steps.
  - Each test flow is composed of multiple steps (API calls, pod log checks, etc.).

- **Dynamic Kubernetes CLI Detection:**
  - Detects and uses `kubectl` or `oc` per host, supporting mixed clusters.

- **Excel-Driven Test Authoring:**
  - Test cases are authored in Excel with flexible columns for HTTP, curl, or Kubernetes commands.
  - Robust parsing extracts method, URL, headers, and payload from both structured and free-form command columns.

- **Remote and Local Execution:**
  - Executes commands on remote hosts via SSH or locally, as configured.

- **Advanced Validation:**
  - Workflow-aware payload validation, pod log pattern matching, and flexible status checks.
  - JSON diffing for deep payload comparisons.

- **Rich Logging and Reporting:**
  - Detailed logs with context (host, step, command, etc.) using Python logging.
  - Live console progress tables and exportable result summaries.

- **Extensible and Modular:**
  - Core logic split into `test_pilot_core.py` for easy testing and extension.
  - CLI orchestration and helpers in `test_pilot.py`.

---

## 🚀 Quickstart

### Installation

**Option 1: Direct Installation**
```bash
# Install dependencies
pip install -r requirements.txt

# Test compatibility
python compatibility_test.py
```

---

## CLI Usage

```bash
python test_pilot.py -i <input.xlsx> -m <module> [options]
```

**Options:**
- `-i, --input <file>`: Path to Excel file (required)
- `-m, --module <otp|config|audit>`: Module to use (required)
- `-s, --sheet <sheetname>`: Only run tests for the specified sheet
- `--test-name <testname>`: Only run the test with this name in the selected sheet (case sensitive)
- `--dry-run`: Only display commands, do not execute
- `--no-table`: Disable table output
- `--log-level <level>`: Set log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) (default: `INFO`)
- `--no-file-logging`: Disable file logging (console only)
- `--log-dir <dir>`: Directory for log files (default: `logs`)

### Example: Run a Specific Test

Run only the test named `MyTestName` in the sheet `Sheet1`:
```bash
python test_pilot.py -i Oracle_VzW_OCSLF_25.1.x_Auto_OTP_v1.2.xlsx -m otp -s Sheet1 --test-name "MyTestName"
```

Suppress all logs (show only critical errors):
```bash
python test_pilot.py -i input.xlsx -m otp --log-level CRITICAL
```

Show debug-level logs:
```bash
python test_pilot.py -i input.xlsx -m otp --log-level DEBUG
```


**Option 2: Package Installation**
```bash
# Install as package
pip install -e .
```

### Setup

1. **Prepare Configuration**
   - Edit `config/hosts.json` to specify your hosts, SSH credentials, and namespaces.

2. **Prepare Test Cases**
   - Author your test scenarios in Excel (`.xlsx`), one sheet per workflow.
   - See `examples/` or below for template.

3. **Run TestPilot**
   ```bash
   python test_pilot.py --input path/to/testcases.xlsx --module your_module

   # Or if installed as package
   testpilot --input path/to/testcases.xlsx --module your_module
   ```

### Compatibility Check

Before running TestPilot, you can verify your environment:
```bash
python compatibility_test.py
```

---

## Excel Test Case Format

| Command | Method | URL | Headers | Payload | Pattern_Match | Expected_Status | Save_As | Compare_With |
|---------|--------|-----|---------|---------|---------------|----------------|---------|--------------|
| curl ... | POST   | ... | ...     | ...     | ...           | 200            | ...     | ...          |

- You can use either a single `Command` column (with curl/kubectl/oc) or explicit columns.
- `Pattern_Match` can be a regex or string to search in pod logs or responses.
- `Save_As` and `Compare_With` enable workflow-aware state sharing between steps.

---

## Main Components

- `test_pilot.py`: CLI and main orchestration logic.
- `test_pilot_core.py`: All core logic for parsing, command building, execution, validation, and logging.
- `excel_parser.py`: Excel parsing utilities.
- `response_parser.py`: Response and log parsing/validation.
- `curl_builder.py`: Command construction for API calls and pod execs.
- `logger.py`: Logging setup and utilities.
- `console_table_fmt.py`: Live/progress table formatting (optional, for console output).
- `dry_run.py`: Dry-run utilities for command preview.

---

## Extending TestPilotOne

- Add new validation logic in `response_parser.py`.
- Add new command patterns in `curl_builder.py`.
- Add new reporting/export formats in `test_pilot.py` or helpers.
- Write unit tests for helpers in `test_pilot_core.py`.

---

## Example Usage

```bash
python test_pilot.py --input tests/example_workflows.xlsx --module my_module
```

---

## License

MIT License. See `LICENSE` file for details.

---

## Acknowledgements

- Built with Python 3.8+
- Uses pandas, tabulate, jsondiff, and standard libraries.
- Inspired by real-world needs for robust, flexible, and workflow-aware cloud test automation.

## Type Checking and mypy Usage

To run mypy and avoid duplicate module errors:

1. Always run mypy from the project root (the parent directory of `testPilotOne/`).
   ```sh
   mypy testPilotOne/
   ```
2. If you encounter errors like `Source file found twice under different module names`, ensure you are not running mypy from inside the `testPilotOne/` directory.
3. If the error persists, try using the `--explicit-package-bases` flag:
   ```sh
   mypy --explicit-package-bases testPilotOne/
   ```
4. Make sure your imports are consistent (prefer absolute imports within the package).

## Type Stubs for Third-Party Libraries

For better type checking with mypy, install stubs for third-party libraries:

```sh
python3 -m pip install types-tabulate pandas-stubs
```
