# TestPilot

A modular, workflow-aware test automation framework for orchestrating multi-step, multi-host API and Kubernetes validation scenarios. Built for flexibility, maintainability, and extensibility in modern cloud-native environments.

## 🔧 Requirements

- **Python 3.8+** (tested on Python 3.8, 3.9, 3.10, 3.11, 3.12)
- Dependencies listed in `requirements.txt`

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
