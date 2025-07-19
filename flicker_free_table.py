# =============================================================================
# Flicker-Free Table Display Alternatives
# Solutions to reduce flickering during rapid test execution updates
# =============================================================================

import os
import sys
import threading
import time
from typing import Any, List

from console_table_fmt import DEFAULT_COLUMN_WIDTHS, SEPARATOR_WIDTH


class ProgressOnlyDisplay:
    """Shows only progress counters, no individual test results during execution"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.total = 0
        self.start_time = time.time()
        self.all_results = []

    def add_result(self, test_result):
        """Add result and update progress counters"""
        self.all_results.append(test_result)
        self.total += 1

        if (
            hasattr(test_result, "result")
            and getattr(test_result, "result", "") == "DRY-RUN"
        ):
            # Count dry-run as passed for progress
            self.passed += 1
        elif getattr(test_result, "passed", False):
            self.passed += 1
        else:
            self.failed += 1

        # Update progress line (overwrites previous line)
        elapsed = time.time() - self.start_time
        rate = self.total / elapsed if elapsed > 0 else 0

        progress_line = (
            f"\r[{elapsed:.1f}s] Tests: {self.total} | "
            f"✅ {self.passed} | ❌ {self.failed} | "
            f"Rate: {rate:.1f}/sec"
        )

        print(progress_line, end="", flush=True)

    def print_final_summary(self, all_results=None):
        """Print final detailed results"""
        print("\n" + "=" * SEPARATOR_WIDTH)
        print("FINAL TEST RESULTS")
        print("=" * SEPARATOR_WIDTH)

        # Group by status
        passed_tests = []
        failed_tests = []
        dry_run_tests = []

        for result in self.all_results:
            if (
                hasattr(result, "result")
                and getattr(result, "result", "") == "DRY-RUN"
            ):
                dry_run_tests.append(result)
            elif getattr(result, "passed", False):
                passed_tests.append(result)
            else:
                failed_tests.append(result)

        print(f"\n✅ PASSED ({len(passed_tests)}):")
        for result in passed_tests[:10]:  # Show first 10
            print(
                f"  {getattr(result, 'test_name', 'Unknown')} on {getattr(result, 'host', 'Unknown')}"
            )
        if len(passed_tests) > 10:
            print(f"  ... and {len(passed_tests) - 10} more")

        print(f"\n❌ FAILED ({len(failed_tests)}):")
        for result in failed_tests:
            print(
                f"  {getattr(result, 'test_name', 'Unknown')} on {getattr(result, 'host', 'Unknown')}"
            )

        if dry_run_tests:
            print(f"\n🔍 DRY-RUN ({len(dry_run_tests)}):")
            for result in dry_run_tests[:10]:
                print(
                    f"  {getattr(result, 'test_name', 'Unknown')} on {getattr(result, 'host', 'Unknown')}"
                )
            if len(dry_run_tests) > 10:
                print(f"  ... and {len(dry_run_tests) - 10} more")

        print("\n" + "=" * SEPARATOR_WIDTH)


class BatchedTable:
    """Updates table in batches to reduce flickering"""

    def __init__(self, batch_size=5, column_widths=None):
        self.batch_size = batch_size
        self.pending_results = []
        self.all_results = []
        self.headers_printed = False
        self.column_widths = column_widths or DEFAULT_COLUMN_WIDTHS.copy()
        self.supports_ansi = self._check_ansi_support()

    def _check_ansi_support(self):
        """Check if terminal supports ANSI color codes"""
        try:
            if not sys.stdout.isatty():
                return False
            if os.environ.get("NO_COLOR"):
                return False
            term = os.environ.get("TERM", "").lower()
            if term in ["dumb", "unknown"]:
                return False
            if os.name == "nt":
                import platform

                if platform.version() >= "10.0.10586":
                    return True
                return False
            return True
        except:
            return False

    def print_headers_once(self):
        """Print table headers once at the beginning"""
        if not self.headers_printed:
            print("\n" + "=" * SEPARATOR_WIDTH)
            print("TEST EXECUTION PROGRESS (Batched Updates)")
            print("=" * SEPARATOR_WIDTH)

            header_row = (
                f"| {{:<{self.column_widths['host']}}} | "
                f"{{:<{self.column_widths['sheet']}}} | "
                f"{{:<{self.column_widths['test_name']}}} | "
                f"{{:<{self.column_widths['method']}}} | "
                f"{{:<{self.column_widths['result']}}} | "
                f"{{:<{self.column_widths['duration']}}} |".format(
                    "Host",
                    "Sheet",
                    "Test Name",
                    "Method",
                    "Result",
                    "Duration (s)",
                )
            )
            print(header_row)

            separator = (
                "|"
                + "-" * self.column_widths["host"]
                + "|"
                + "-" * self.column_widths["sheet"]
                + "|"
                + "-" * self.column_widths["test_name"]
                + "|"
                + "-" * self.column_widths["method"]
                + "|"
                + "-" * self.column_widths["result"]
                + "|"
                + "-" * self.column_widths["duration"]
                + "|"
            )
            print(separator)
            self.headers_printed = True

    def add_result(self, test_result):
        """Add result to batch and update when batch is full"""
        self.pending_results.append(test_result)
        self.all_results.append(test_result)

        # Update when batch is full or force update after delay
        if len(self.pending_results) >= self.batch_size:
            self._flush_batch()

    def _flush_batch(self):
        """Print all pending results"""
        if not self.pending_results:
            return

        self.print_headers_once()

        for test_result in self.pending_results:
            self._print_single_result(test_result)

        # Show progress
        passed = sum(
            1 for r in self.all_results if getattr(r, "passed", False)
        )
        failed = len(self.all_results) - passed
        print(
            f"\nProgress: {len(self.all_results)} completed | {passed} passed | {failed} failed"
        )

        self.pending_results.clear()

    def _print_single_result(self, test_result):
        """Print a single result row"""
        host = getattr(test_result, "host", "")[
            : self.column_widths["host"] - 1
        ]
        sheet = getattr(test_result, "sheet", "")[
            : self.column_widths["sheet"] - 1
        ]
        test_name = getattr(test_result, "test_name", "")[
            : self.column_widths["test_name"] - 1
        ]
        method = getattr(test_result, "method", "")[
            : self.column_widths["method"] - 1
        ]
        duration = f"{getattr(test_result, 'duration', 0.0):.2f}"

        # Format result with colors
        if self.supports_ansi:
            ANSI_GREEN = "\033[92m"
            ANSI_RED = "\033[91m"
            ANSI_YELLOW = "\033[93m"
            ANSI_RESET = "\033[0m"
        else:
            ANSI_GREEN = ANSI_RED = ANSI_YELLOW = ANSI_RESET = ""

        if (
            hasattr(test_result, "result")
            and getattr(test_result, "result", "") == "DRY-RUN"
        ):
            result = (
                f"{ANSI_YELLOW}DRY-RUN{ANSI_RESET}"
                if self.supports_ansi
                else "DRY-RUN"
            )
        elif getattr(test_result, "passed", False):
            result = (
                f"{ANSI_GREEN}PASS{ANSI_RESET}"
                if self.supports_ansi
                else "PASS"
            )
        else:
            result = (
                f"{ANSI_RED}FAIL{ANSI_RESET}" if self.supports_ansi else "FAIL"
            )

        row = (
            f"| {{:<{self.column_widths['host']}}} | "
            f"{{:<{self.column_widths['sheet']}}} | "
            f"{{:<{self.column_widths['test_name']}}} | "
            f"{{:<{self.column_widths['method']}}} | "
            f"{{:<{self.column_widths['result']}}} | "
            f"{{:<{self.column_widths['duration']}}} |".format(
                host, sheet, test_name, method, result, duration
            )
        )
        print(row)

    def print_final_summary(self, all_results=None):
        """Print final summary and flush any remaining results"""
        self._flush_batch()  # Flush any remaining results

        passed = sum(
            1 for r in self.all_results if getattr(r, "passed", False)
        )
        failed = len(self.all_results) - passed

        print("\n" + "=" * SEPARATOR_WIDTH)
        print(
            f"FINAL SUMMARY: {passed} PASSED | {failed} FAILED | {len(self.all_results)} TOTAL"
        )
        print("=" * SEPARATOR_WIDTH)


class StaticPlusLiveTable:
    """Shows static summary + live updating last few results"""

    def __init__(self, live_window_size=3, column_widths=None):
        self.live_window_size = live_window_size
        self.all_results = []
        self.recent_results = []
        self.column_widths = column_widths or DEFAULT_COLUMN_WIDTHS.copy()
        self.supports_ansi = self._check_ansi_support()
        self.start_time = time.time()

    def _check_ansi_support(self):
        """Check if terminal supports ANSI color codes"""
        return sys.stdout.isatty() and not os.environ.get("NO_COLOR")

    def add_result(self, test_result):
        """Add result and update display"""
        self.all_results.append(test_result)
        self.recent_results.append(test_result)

        # Keep only recent results in live window
        if len(self.recent_results) > self.live_window_size:
            self.recent_results.pop(0)

        self._update_display()

    def _update_display(self):
        """Update the entire display"""
        # Clear screen and show updated info
        if self.supports_ansi:
            print(
                "\033[2J\033[H", end=""
            )  # Clear screen and move cursor to top

        # Show header
        elapsed = time.time() - self.start_time
        passed = sum(
            1 for r in self.all_results if getattr(r, "passed", False)
        )
        failed = len(self.all_results) - passed
        rate = len(self.all_results) / elapsed if elapsed > 0 else 0

        print("=" * 80)
        print(f"TEST EXECUTION STATUS - {elapsed:.1f}s elapsed")
        print("=" * 80)
        print(
            f"Total: {len(self.all_results)} | Passed: {passed} | Failed: {failed} | Rate: {rate:.1f}/sec"
        )
        print()

        # Show recent results
        print("Recent Results:")
        print("-" * 80)
        for result in self.recent_results:
            status = (
                "✅ PASS" if getattr(result, "passed", False) else "❌ FAIL"
            )
            if (
                hasattr(result, "result")
                and getattr(result, "result", "") == "DRY-RUN"
            ):
                status = "🔍 DRY-RUN"

            test_name = getattr(result, "test_name", "Unknown")[:30]
            host = getattr(result, "host", "Unknown")[:15]
            duration = getattr(result, "duration", 0.0)

            print(f"{status} {test_name:<30} on {host:<15} ({duration:.2f}s)")

        print("\n" + "=" * 80)

    def print_final_summary(self, all_results=None):
        """Print final summary"""
        passed = sum(
            1 for r in self.all_results if getattr(r, "passed", False)
        )
        failed = len(self.all_results) - passed

        print("\n" + "=" * SEPARATOR_WIDTH)
        print("FINAL TEST RESULTS")
        print("=" * SEPARATOR_WIDTH)
        print(
            f"SUMMARY: {passed} PASSED | {failed} FAILED | {len(self.all_results)} TOTAL"
        )
        print("=" * SEPARATOR_WIDTH)


# Factory function to create the appropriate display type
def create_display(display_type="progress_only", **kwargs):
    """Create a display instance based on type"""
    if display_type == "progress_only":
        return ProgressOnlyDisplay()
    elif display_type == "batched":
        return BatchedTable(**kwargs)
    elif display_type == "static_live":
        return StaticPlusLiveTable(**kwargs)
    else:
        # Fallback to existing LiveProgressTable
        from console_table_fmt import LiveProgressTable

        return LiveProgressTable(**kwargs)
