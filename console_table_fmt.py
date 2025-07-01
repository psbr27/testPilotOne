# =============================================================================
# APPROACH 1: Simple - Headers Once, Then Just Rows
# =============================================================================

import os
import sys
import time
from tabulate import tabulate


class SimpleProgressTable:
    def __init__(self):
        self.headers = [
            "Host",
            "Sheet",
            "Test Name",
            "Method",
            "Result",
            "Duration (s)",
        ]
        self.headers_printed = False

    def print_headers(self):
        """Print table headers once at the beginning"""
        if not self.headers_printed:
            print("\n" + "=" * 100)
            print("TEST EXECUTION PROGRESS")
            print("=" * 100)
            print(tabulate([self.headers], headers=self.headers, tablefmt="github"))
            print("-" * 100)
            self.headers_printed = True

    def add_result(self, test_result):
        """Add a single test result row"""
        self.print_headers()  # Ensure headers are printed

        host = getattr(test_result, "host", "")
        sheet = getattr(test_result, "sheet", "")
        test_name = getattr(test_result, "test_name", "")
        method = (
            getattr(test_result, "method", "") if hasattr(test_result, "method") else ""
        )
        duration = f"{getattr(test_result, 'duration', 0.0):.2f}"

        # Result: DRY-RUN for dry-run, else PASS/FAIL
        if (
            hasattr(test_result, "result")
            and getattr(test_result, "result", "") == "DRY-RUN"
        ):
            result = "DRY-RUN"
        else:
            result = "PASS" if getattr(test_result, "passed", False) else "FAIL"

        row_data = [host, sheet, test_name, method, result, duration]

        # Print just this row with proper spacing to match headers
        print(
            f"| {host:<12} | {sheet:<10} | {test_name:<15} | {method:<8} | {result:<10} | {duration:<12} |"
        )


# =============================================================================
# APPROACH 2: Clear Screen and Reprint (Clean but with potential flicker)
# =============================================================================


class ClearAndReprintTable:
    def __init__(self):
        self.headers = [
            "Host",
            "Sheet",
            "Test Name",
            "Method",
            "Result",
            "Duration (s)",
        ]
        self.all_results = []

    def clear_screen(self):
        """Clear the console screen"""
        os.system("cls" if os.name == "nt" else "clear")

    def add_result(self, test_result):
        """Add result and reprint entire table"""
        self.all_results.append(test_result)

        # Clear screen and reprint everything
        self.clear_screen()

        print("\n" + "=" * 100)
        print(f"TEST EXECUTION PROGRESS - {len(self.all_results)} tests completed")
        print("=" * 100)

        table_data = []
        for r in self.all_results:
            host = getattr(r, "host", "")
            sheet = getattr(r, "sheet", "")
            test_name = getattr(r, "test_name", "")
            method = getattr(r, "method", "") if hasattr(r, "method") else ""
            duration = f"{getattr(r, 'duration', 0.0):.2f}"

            if hasattr(r, "result") and getattr(r, "result", "") == "DRY-RUN":
                result = "DRY-RUN"
            else:
                result = "PASS" if getattr(r, "passed", False) else "FAIL"

            table_data.append([host, sheet, test_name, method, result, duration])

        print(tabulate(table_data, headers=self.headers, tablefmt="github"))

        # Show summary
        passed = sum(1 for r in self.all_results if getattr(r, "passed", False))
        failed = len(self.all_results) - passed
        print(f"\nSUMMARY: {passed} passed, {failed} failed")


# =============================================================================
# APPROACH 3: ANSI Escape Codes for In-Place Updates (Professional)
# =============================================================================


class LiveUpdateTable:
    def __init__(self):
        self.headers = [
            "Host",
            "Sheet",
            "Test Name",
            "Method",
            "Result",
            "Duration (s)",
        ]
        self.all_results = []
        self.table_start_line = None

    def setup_table(self):
        """Setup the initial table structure"""
        print("\n" + "=" * 100)
        print("TEST EXECUTION PROGRESS")
        print("=" * 100)

        # Print headers
        print(tabulate([self.headers], headers=self.headers, tablefmt="github"))

        # Remember where our data starts
        self.table_start_line = self._get_cursor_position()

        # Print empty line for the first result
        print("")

    def _get_cursor_position(self):
        """Get current cursor line position (simplified)"""
        return len(self.all_results) + 6  # Approximate based on header size

    def _move_cursor_to_line(self, line):
        """Move cursor to specific line"""
        print(f"\033[{line};1H", end="")  # Move to line, column 1

    def _clear_line(self):
        """Clear current line"""
        print("\033[K", end="")  # Clear line from cursor to end

    def add_result(self, test_result):
        """Add a new result and update table in place"""
        if self.table_start_line is None:
            self.setup_table()

        self.all_results.append(test_result)

        # Format the new row
        host = getattr(test_result, "host", "")
        sheet = getattr(test_result, "sheet", "")
        test_name = getattr(test_result, "test_name", "")
        method = (
            getattr(test_result, "method", "") if hasattr(test_result, "method") else ""
        )
        duration = f"{getattr(test_result, 'duration', 0.0):.2f}"

        if (
            hasattr(test_result, "result")
            and getattr(test_result, "result", "") == "DRY-RUN"
        ):
            result = "DRY-RUN"
        else:
            result = "PASS" if getattr(test_result, "passed", False) else "FAIL"

        # Print the new row at the current position
        row_data = [host, sheet, test_name, method, result, duration]
        print(tabulate([row_data], tablefmt="github"))

        # Update summary at the bottom
        passed = sum(1 for r in self.all_results if getattr(r, "passed", False))
        failed = len(self.all_results) - passed
        print(f"\nSUMMARY: {passed} passed, {failed} failed, Running...")


# =============================================================================
# APPROACH 4: Rich Library (Best UX - requires pip install rich)
# =============================================================================

try:
    from rich.console import Console
    from rich.table import Table
    from rich.live import Live
    from rich.text import Text
    import threading

    class RichLiveTable:
        def __init__(self):
            self.console = Console()
            self.headers = [
                "Host",
                "Sheet",
                "Test Name",
                "Method",
                "Result",
                "Duration (s)",
            ]
            self.all_results = []
            self.live_display = None
            self.lock = threading.Lock()

        def _create_table(self):
            """Create a Rich table with current results"""
            table = Table(
                title="🚀 Test Execution Progress",
                show_header=True,
                header_style="bold magenta",
            )

            # Add columns
            table.add_column("Host", style="cyan", width=12)
            table.add_column("Sheet", style="blue", width=12)
            table.add_column("Test Name", style="yellow", width=20)
            table.add_column("Method", style="white", width=8)
            table.add_column("Result", width=10)
            table.add_column("Duration (s)", style="green", width=12)

            # Add rows
            for r in self.all_results:
                host = getattr(r, "host", "")
                sheet = getattr(r, "sheet", "")
                test_name = getattr(r, "test_name", "")
                method = getattr(r, "method", "") if hasattr(r, "method") else ""
                duration = f"{getattr(r, 'duration', 0.0):.2f}"

                if hasattr(r, "result") and getattr(r, "result", "") == "DRY-RUN":
                    result = Text("DRY-RUN", style="yellow")
                elif getattr(r, "passed", False):
                    result = Text("PASS", style="green")
                else:
                    result = Text("FAIL", style="red")

                table.add_row(host, sheet, test_name, method, result, duration)

            # Add summary
            if self.all_results:
                passed = sum(1 for r in self.all_results if getattr(r, "passed", False))
                failed = len(self.all_results) - passed
                table.caption = f"Summary: {passed} passed, {failed} failed"

            return table

        def start_live_display(self):
            """Start the live updating display"""
            self.live_display = Live(
                self._create_table(), refresh_per_second=10, console=self.console
            )
            self.live_display.start()

        def add_result(self, test_result):
            """Add a new result and update the live display"""
            with self.lock:
                if self.live_display is None:
                    self.start_live_display()

                self.all_results.append(test_result)
                self.live_display.update(self._create_table())

        def stop(self):
            """Stop the live display"""
            if self.live_display:
                self.live_display.stop()

except ImportError:
    print("Rich library not available. Install with: pip install rich")
    RichLiveTable = None


class LiveProgressTable:
    """Live updating table that prints headers once and adds rows incrementally"""

    def __init__(self, approach="simple"):
        self.headers = [
            "Host",
            "Sheet",
            "Test Name",
            "Method",
            "Result",
            "Duration (s)",
        ]
        self.headers_printed = False
        self.results_count = 0
        self.approach = approach

    def print_headers_once(self):
        """Print table headers once at the beginning"""
        if not self.headers_printed:
            print("\n" + "=" * 120)
            print("TEST EXECUTION PROGRESS")
            print("=" * 120)

            # Print header row with proper formatting
            header_row = (
                "| {:<15} | {:<12} | {:<20} | {:<8} | {:<12} | {:<12} |".format(
                    "Host", "Sheet", "Test Name", "Method", "Result", "Duration (s)"
                )
            )
            print(header_row)
            print(
                "|" + "-" * 15 + "|" + "-" * 20 + "|" + "-" * 30 + "|" + "-" * 8 + "|" + "-" * 12 + "|" + "-" * 12 + "|"
            )
            self.headers_printed = True

    def add_result(self, test_result):
        """Add a single test result row"""
        self.print_headers_once()

        # Extract data
        host = getattr(test_result, "host", "")[:14]  # Truncate if too long
        sheet = getattr(test_result, "sheet", "")[:20]
        test_name = getattr(test_result, "test_name", "")[:30]
        method = (
            getattr(test_result, "method", "") if hasattr(test_result, "method") else ""
        )
        duration = f"{getattr(test_result, 'duration', 0.0):.2f}"

        # Format result with colors
        ANSI_GREEN = "\033[92m"
        ANSI_RED = "\033[91m"
        ANSI_RESET = "\033[0m"
        if (
            hasattr(test_result, "result")
            and getattr(test_result, "result", "") == "DRY-RUN"
        ):
            result = "DRY-RUN"
        elif getattr(test_result, "passed", False):
            result = f"{ANSI_GREEN}PASS{ANSI_RESET}"
        else:
            result = f"{ANSI_RED}FAIL{ANSI_RESET}"

        # Print formatted row
        row = "| {:<15} | {:<20} | {:<30} | {:<8} | {:<12} | {:<12} |".format(
            host, sheet, test_name, method, result, duration
        )
        print(row)
        import time
        time.sleep(0.5)

        self.results_count += 1

        # Print running summary every 5 tests
        if self.results_count % 5 == 0:
            self._print_mini_summary()

    def _print_mini_summary(self):
        """Print a brief summary line"""
        #print(f"    {self.results_count} tests completed...")
        pass

    def print_final_summary(self, all_results):
        """Print final summary at the end"""
        if not all_results:
            return

        passed = sum(1 for r in all_results if getattr(r, "passed", False))
        failed = len(all_results) - passed

        print("\n" + "=" * 120)
        print(
            f"FINAL SUMMARY: {passed} PASSED | {failed} FAILED | {len(all_results)} TOTAL"
        )
        print("=" * 120)
