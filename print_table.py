import time
import textwrap # Import the textwrap module for easy wrapping
import threading
from typing import List, Any, Optional
from dataclasses import dataclass

def display_test_results_with_fixed_and_wrapped_alignment(results_data, delay_seconds=1, max_entries=100):
    """
    Displays test results one at a time with a delay, maintaining fixed column alignment
    and wrapping text that exceeds the column width.

    Args:
        results_data (list of dict): A list where each dictionary represents
                                     a test result.
        delay_seconds (int/float): The delay in seconds between displaying each entry.
        max_entries (int): The maximum number of entries to display.
    """
    if not results_data:
        print("No test results to display.")
        return

    # Define the desired fixed widths for each column
    # Adjust these values based on your expected maximum content lengths
    fixed_col_widths = {
        "Index": 5,
        "Sheet Name": 20,
        "Test Name": 25, # Example: increased to allow more space before wrapping
        "Duration (s)": 12,
        "Result": 8,
        "Fail Reason": 35 # Example: increased to allow more space for error messages
    }

    headers_list = ["Index", "Sheet Name", "Test Name", "Duration (s)", "Result", "Fail Reason"]

    # --- Step 1: Print Header Row ---
    header_line = "|"
    separator_line = "+"
    for header in headers_list:
        width = fixed_col_widths.get(header, len(header)) # Use fixed width, fallback to header length
        header_line += f" {header:<{width}} |"
        separator_line += f"-{'-'*width}-+"
    
    print(separator_line)
    print(header_line)
    print(separator_line.replace('-', '='))

    # --- Step 2: Stream Data Rows with Wrapping ---
    def colorize_and_pad(text, width):
        # Pad first, then colorize only non-empty lines
        padded = f"{text:<{width}}"
        if text == 'PASS' and text.strip():
            return f"\033[92m{padded}\033[0m"  # Green color for PASS
        elif text == 'FAIL' and text.strip():
            return f"\033[91m{padded}\033[0m"  # Red color for FAIL
        elif text == 'DRY-RUN' and text.strip():
            return f"\033[93m{padded}\033[0m"  # Yellow color for DRY-RUN
        else:
            return padded

    for i, row_data in enumerate(results_data):
        if i >= max_entries:
            print(f"\nDisplaying {max_entries} entries. Stopping.")
            break

        # Get data with defaults (ensure string types)
        index_val = str(i)
        sheet_name_val = str(row_data.get('sheet_name', 'N/A'))
        test_name_val = str(row_data.get('test_name', 'N/A'))

        # Format duration with 2 decimal places if it's a number
        duration_raw = row_data.get('duration', 'N/A')
        if isinstance(duration_raw, (int, float)):
            duration_val = f'{float(duration_raw):.2f}'
        else:
            duration_val = str(duration_raw)

        result_val = str(row_data.get('result', 'N/A'))
        fail_reason_val = str(row_data.get('fail_reason', ''))

        # Apply wrapping to fields that might exceed fixed width
        wrapped_index = textwrap.wrap(index_val, width=fixed_col_widths["Index"])
        wrapped_sheet_name = textwrap.wrap(sheet_name_val, width=fixed_col_widths["Sheet Name"])
        wrapped_test_name = textwrap.wrap(test_name_val, width=fixed_col_widths["Test Name"])
        wrapped_duration = textwrap.wrap(duration_val, width=fixed_col_widths["Duration (s)"])
        wrapped_result = textwrap.wrap(result_val, width=fixed_col_widths["Result"])
        wrapped_fail_reason = textwrap.wrap(fail_reason_val, width=fixed_col_widths["Fail Reason"])

        # Determine the maximum number of lines for this row after wrapping
        max_lines = max(
            len(wrapped_index),
            len(wrapped_sheet_name),
            len(wrapped_test_name),
            len(wrapped_duration),
            len(wrapped_result),
            len(wrapped_fail_reason)
        )

        # Print each line of the wrapped row
        for line_num in range(max_lines):
            line_parts = []

            line_parts.append(f" {wrapped_index[line_num] if line_num < len(wrapped_index) else '':<{fixed_col_widths['Index']}}")
            line_parts.append(f" {wrapped_sheet_name[line_num] if line_num < len(wrapped_sheet_name) else '':<{fixed_col_widths['Sheet Name']}}")
            line_parts.append(f" {wrapped_test_name[line_num] if line_num < len(wrapped_test_name) else '':<{fixed_col_widths['Test Name']}}")
            line_parts.append(f" {wrapped_duration[line_num] if line_num < len(wrapped_duration) else '':<{fixed_col_widths['Duration (s)']}}")
            # For result, colorize and pad only the actual text, not the padding
            if line_num < len(wrapped_result):
                line_parts.append(colorize_and_pad(wrapped_result[line_num], fixed_col_widths['Result']))
            else:
                line_parts.append(' ' * (fixed_col_widths['Result'] + 1))
            line_parts.append(f" {wrapped_fail_reason[line_num] if line_num < len(wrapped_fail_reason) else '':<{fixed_col_widths['Fail Reason']}}")

            print("|" + "|".join(line_parts) + "|")

        print(separator_line) # Print separator after each logical row (which might be multi-line)

        time.sleep(delay_seconds) # Pause for the specified delay

# if __name__ == "__main__":
#     test_results = []
#     for i in range(15):
#         reason = ''
#         if i % 3 == 0:
#             result = 'FAIL'
#             reason = f'Error during step {i+1}. This is a very long and detailed explanation of why this particular test failed and it absolutely needs to wrap to multiple lines to fit the console width nicely.'
#         else:
#             result = 'PASS'
#             reason = ''
        
#         test_name_val = f'Test Case {i + 1}'
#         if i % 2 == 0:
#             test_name_val += ' - This is a rather long test name that might cause overflow if not handled properly and needs to wrap.'

#         test_results.append({
#             'sheet_name': f'Suite {i // 5 + 1}',
#             'test_name': test_name_val,
#             'duration': round(2.0 + (i * 0.1), 2),
#             'result': result,
#             'fail_reason': reason
#         })

#     print("--- Displaying Test Results One by One with Fixed Alignment and Text Wrapping ---")
#     display_test_results_with_fixed_and_wrapped_alignment(test_results, delay_seconds=0.5, max_entries=10)
#     print("\n" + "="*80 + "\n")


@dataclass
class TestDisplayRow:
    """Represents a row in the test results table"""
    
    host: str = ""
    sheet: str = ""
    test_name: str = ""
    method: str = "GET"
    status: str = ""  # PASS, FAIL, DRY-RUN
    duration: float = 0.0
    fail_reason: str = ""
    _original_test_name: str = ""  # Store the original test name before truncation
    
    @classmethod
    def from_result(cls, result):
        """Create from a test result object"""
        # Determine status
        if hasattr(result, "result") and getattr(result, "result", "") == "DRY-RUN":
            status = "DRY-RUN"
        elif getattr(result, "passed", False):
            status = "PASS"
        else:
            status = "FAIL"
        fail_reason = getattr(result, "fail_reason", "") or ""
        original_test_name = getattr(result, "test_name", "")
        return cls(
            host=getattr(result, "host", "")[:12],  # Truncate for display
            sheet=getattr(result, "sheet", ""),  # Don't truncate sheet name
            test_name=original_test_name[:25],  # Truncate for display
            method=getattr(result, "method", "GET")[:6],
            status=status,
            duration=getattr(result, "duration", 0.0),
            fail_reason=fail_reason[:40],  # Truncate for display
            _original_test_name=original_test_name  # Store the full test name
        )


class PrintTableDashboard:
    """Table dashboard using print_table functionality for displaying test results"""
    
    def __init__(self, mode="full", auto_scroll=True, max_entries=100, delay_seconds=0.1):
        self.mode = mode
        self.auto_scroll = auto_scroll
        self.max_entries = max_entries
        self.delay_seconds = delay_seconds
        self.results = []
        self.start_time = time.time()
        self.lock = threading.Lock()
        self.running = False
        
        # Statistics
        self.passed = 0
        self.failed = 0
        self.dry_run = 0
        self.total = 0
    
    def start(self):
        """Initialize the dashboard display"""
        with self.lock:
            self.running = True
            print("\n" + "=" * 80)
            print("TestPilot - Test Results")
            print("=" * 80)
    
    def stop(self):
        """Clean up the dashboard"""
        with self.lock:
            self.running = False
    
    def add_result(self, test_result):
        """Add a new test result and update display"""
        with self.lock:
            if not self.running:
                return
                
            # Convert result to display row
            row = TestDisplayRow.from_result(test_result)
            self.results.append(row)
            
            # Update statistics
            self.total += 1
            if row.status == "PASS":
                self.passed += 1
            elif row.status == "FAIL":
                self.failed += 1
            elif row.status == "DRY-RUN":
                self.dry_run += 1
            
            # Convert to dictionary format for display
            result_dict = {
                'sheet_name': row.sheet,
                'test_name': row.test_name,
                'duration': f'{row.duration:.2f}',  # Format with 2 decimal places
                'result': row.status,
                'fail_reason': row.fail_reason
            }
            
            # Display based on mode
            if self.mode == "full":
                # For full mode, display the single new result
                if len(self.results) == 1:  # First result, show header
                    self._display_single_result(result_dict)
                else:
                    self._display_single_result(result_dict, show_header=False)
            elif self.mode == "progress":
                # For progress mode, just show a simple progress indicator
                self._display_progress(row)
            else:  # simple mode
                # For simple mode, just print a simple line
                self._display_simple(row)
    
    def _display_single_result(self, result_dict, show_header=True):
        """Display a single result using the display_test_results_with_fixed_and_wrapped_alignment function"""
        if show_header:
            display_test_results_with_fixed_and_wrapped_alignment([result_dict], delay_seconds=0, max_entries=1)
        else:
            # Get data with defaults (ensure string types)
            index_val = str(len(self.results) - 1)
            sheet_name_val = str(result_dict.get('sheet_name', 'N/A'))
            test_name_val = str(result_dict.get('test_name', 'N/A'))
            
            # Format duration with 2 decimal places if it's a number
            duration_raw = result_dict.get('duration', 'N/A')
            if isinstance(duration_raw, (int, float)) or (isinstance(duration_raw, str) and duration_raw.replace('.', '', 1).isdigit()):
                try:
                    duration_val = f'{float(duration_raw):.2f}'
                except ValueError:
                    duration_val = str(duration_raw)
            else:
                duration_val = str(duration_raw)
                
            result_val = str(result_dict.get('result', 'N/A'))
            fail_reason_val = str(result_dict.get('fail_reason', ''))
            
            # Define the fixed widths for each column (same as in display_test_results_with_fixed_and_wrapped_alignment)
            fixed_col_widths = {
                "Index": 5,
                "Sheet Name": 20,
                "Test Name": 25,
                "Duration (s)": 12,
                "Result": 8,
                "Fail Reason": 35
            }
            
            # Apply wrapping to fields that might exceed fixed width
            wrapped_index = textwrap.wrap(index_val, width=fixed_col_widths["Index"])
            wrapped_sheet_name = textwrap.wrap(sheet_name_val, width=fixed_col_widths["Sheet Name"])
            wrapped_test_name = textwrap.wrap(test_name_val, width=fixed_col_widths["Test Name"])
            wrapped_duration = textwrap.wrap(duration_val, width=fixed_col_widths["Duration (s)"])
            wrapped_result = textwrap.wrap(result_val, width=fixed_col_widths["Result"])
            wrapped_fail_reason = textwrap.wrap(fail_reason_val, width=fixed_col_widths["Fail Reason"])
            
            # Determine the maximum number of lines for this row after wrapping
            max_lines = max(
                len(wrapped_index),
                len(wrapped_sheet_name),
                len(wrapped_test_name),
                len(wrapped_duration),
                len(wrapped_result),
                len(wrapped_fail_reason)
            )
            
            # Print each line of the wrapped row
            for line_num in range(max_lines):
                line_parts = []
                
                line_parts.append(f" {wrapped_index[line_num] if line_num < len(wrapped_index) else '':<{fixed_col_widths['Index']}}")
                line_parts.append(f" {wrapped_sheet_name[line_num] if line_num < len(wrapped_sheet_name) else '':<{fixed_col_widths['Sheet Name']}}")
                line_parts.append(f" {wrapped_test_name[line_num] if line_num < len(wrapped_test_name) else '':<{fixed_col_widths['Test Name']}}")
                line_parts.append(f" {wrapped_duration[line_num] if line_num < len(wrapped_duration) else '':<{fixed_col_widths['Duration (s)']}}") 
                # Colorize the result field (PASS in green, FAIL in red)
                if line_num < len(wrapped_result):
                    result_text = wrapped_result[line_num]
                    if result_text == 'PASS':
                        line_parts.append(f" \033[92m{result_text:{fixed_col_widths['Result']}}\033[0m")
                    elif result_text == 'FAIL':
                        line_parts.append(f" \033[91m{result_text:{fixed_col_widths['Result']}}\033[0m")
                    else:
                        line_parts.append(f" {result_text:<{fixed_col_widths['Result']}}")
                else:
                    line_parts.append(f" {'':{fixed_col_widths['Result']}}")
                line_parts.append(f" {wrapped_fail_reason[line_num] if line_num < len(wrapped_fail_reason) else '':<{fixed_col_widths['Fail Reason']}}")
                
                print("|" + "|".join(line_parts) + "|")
            
            # Print separator after each logical row
            separator_line = "+"
            for header in ["Index", "Sheet Name", "Test Name", "Duration (s)", "Result", "Fail Reason"]:
                width = fixed_col_widths.get(header, len(header))
                separator_line += f"-{'-'*width}-+"
            print(separator_line)
            
            time.sleep(self.delay_seconds)  # Pause for the specified delay
    
    def _display_progress(self, row):
        """Display a simple progress indicator"""
        status_char = "✓" if row.status == "PASS" else "✗" if row.status == "FAIL" else "◦"
        status_color = "\033[92m" if row.status == "PASS" else "\033[91m" if row.status == "FAIL" else "\033[93m"
        reset_color = "\033[0m"
        elapsed = time.time() - self.start_time
        rate = self.total / elapsed if elapsed > 0 else 0
        
        print(f"\r{status_color}{status_char}{reset_color} Test {self.total}: {row.test_name} - {status_color}{row.status}{reset_color} ({row.duration:.2f}s) | Total: {self.total} | Rate: {rate:.1f}/sec", end="")
        
        if row.status == "FAIL":
            print(f" | {status_color}Fail: {row.fail_reason}{reset_color}")
        else:
            print()
    
    def _display_simple(self, row):
        """Display a simple line for each test result"""
        status_color = "\033[92m" if row.status == "PASS" else "\033[91m" if row.status == "FAIL" else "\033[93m"
        reset_color = "\033[0m"
        
        print(f"{status_color}{row.status}{reset_color} - {row.test_name} ({row.duration:.2f}s)")
        if row.status == "FAIL" and row.fail_reason:
            print(f"  {status_color}Fail reason: {row.fail_reason}{reset_color}")
    
    def print_final_summary(self):
        """Print final summary after stopping"""
        self.stop()
        
        # Print comprehensive final summary
        print("\n" + "=" * 80)
        print("FINAL TEST RESULTS SUMMARY")
        print("=" * 80)
        
        total_time = time.time() - self.start_time
        avg_time = total_time / self.total if self.total > 0 else 0
        
        print(f"Execution Time: {total_time:.2f} seconds")
        print(f"Average per test: {avg_time:.2f} seconds")
        print(f"Total Tests: {self.total}")
        print(f"✓ Passed: {self.passed}")
        print(f"✗ Failed: {self.failed}")
        if self.dry_run > 0:
            print(f"◦ Dry-Run: {self.dry_run}")
        
        success_rate = (self.passed / self.total * 100) if self.total > 0 else 0
        print(f"Success Rate: {success_rate:.1f}%")
        
        # Group results by sheet name
        sheet_results = {}
        for result in self.results:
            sheet_name = result.sheet
            if sheet_name not in sheet_results:
                sheet_results[sheet_name] = {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "failed_tests": []
                }
            
            sheet_results[sheet_name]["total"] += 1
            if result.status == "PASS":
                sheet_results[sheet_name]["passed"] += 1
            elif result.status == "FAIL":
                sheet_results[sheet_name]["failed"] += 1
                sheet_results[sheet_name]["failed_tests"].append(result)
        
        # Print summary by sheet
        print("\n" + "-" * 80)
        print("SUMMARY BY SHEET")
        print("-" * 80)
        
        for sheet_name, stats in sheet_results.items():
            # Calculate sheet success rate
            sheet_success_rate = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
            
            # Print sheet summary with color coding
            if stats["failed"] == 0:
                status_color = "\033[92m"  # Green for all passed
            elif stats["passed"] == 0:
                status_color = "\033[91m"  # Red for all failed
            else:
                status_color = "\033[93m"  # Yellow for mixed results
            
            reset_color = "\033[0m"
            print(f"\n{status_color}{sheet_name}{reset_color}: {stats['passed']}/{stats['total']} -- {stats['passed']} pass out of {stats['total']} ({sheet_success_rate:.1f}%)")
            
            # List failed tests for this sheet
            if stats["failed"] > 0:
                print(f"  Failed tests in this sheet:")
                for result in stats["failed_tests"]:
                    # Use the full test name instead of the potentially truncated one stored in the TestDisplayRow
                    full_test_name = getattr(result, "_original_test_name", result.test_name)
                    print(f"    ✗ {full_test_name}")
                    if result.fail_reason:
                        print(f"      Reason: {result.fail_reason}")
            else:
                print(f"  {status_color}All tests passed!{reset_color}")
        
        print("\n" + "=" * 80)


def create_print_table_dashboard(mode="full", **kwargs):
    """Create a PrintTableDashboard instance with the specified mode"""
    return PrintTableDashboard(mode=mode, **kwargs)
