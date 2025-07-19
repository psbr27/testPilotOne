# =============================================================================
# Blessed Terminal Dashboard - Clean, flicker-free test results display with Auto-Scroll
# =============================================================================

import threading
import time
from dataclasses import dataclass
from typing import Any, List, Optional

try:
    from blessed import Terminal

    BLESSED_AVAILABLE = True
except ImportError:
    BLESSED_AVAILABLE = False
    Terminal = None


@dataclass
class TestDisplayRow:
    """Data structure for a test result row"""

    host: str
    sheet: str
    test_name: str
    method: str
    status: str  # PASS, FAIL, DRY-RUN
    duration: float
    fail_reason: str = ""  # Add fail_reason

    @classmethod
    def from_result(cls, result):
        """Create from a test result object"""
        # Determine status
        if (
            hasattr(result, "result")
            and getattr(result, "result", "") == "DRY-RUN"
        ):
            status = "DRY-RUN"
        elif getattr(result, "passed", False):
            status = "PASS"
        else:
            status = "FAIL"
        fail_reason = getattr(result, "fail_reason", "") or ""
        return cls(
            host=getattr(result, "host", "")[:12],  # Truncate for display
            sheet=getattr(result, "sheet", "")[:10],
            test_name=getattr(result, "test_name", "")[:25],
            method=getattr(result, "method", "GET")[:6],
            status=status,
            duration=getattr(result, "duration", 0.0),
            fail_reason=fail_reason[:40],  # Truncate for display
        )


class BlessedDashboard:
    """Terminal dashboard using blessed library for flicker-free updates with auto-scroll"""

    def __init__(self, auto_scroll=True, scroll_buffer_size=1000):
        if not BLESSED_AVAILABLE:
            raise ImportError(
                "blessed library not available. Install with: pip install blessed"
            )

        self.term = Terminal()
        self.auto_scroll = auto_scroll
        self.scroll_buffer_size = scroll_buffer_size
        self.results: List[TestDisplayRow] = []
        self.start_time = time.time()
        self.lock = threading.Lock()
        self.running = False

        # Dynamic layout calculation
        self.header_height = 6  # Header + progress + separator + table header
        self.footer_height = 1  # Status line
        self.last_terminal_height = 0
        self.max_visible_rows = 0
        self.scroll_offset = 0  # For manual scrolling (future feature)

        # Statistics
        self.passed = 0
        self.failed = 0
        self.dry_run = 0
        self.total = 0

        # Performance optimization
        self.last_displayed_count = 0
        self.force_full_redraw = True

    def _calculate_layout(self):
        """Calculate dynamic layout based on current terminal size"""
        current_height = self.term.height

        if current_height != self.last_terminal_height:
            self.last_terminal_height = current_height
            self.max_visible_rows = max(
                1, current_height - self.header_height - self.footer_height
            )
            self.force_full_redraw = True

        return self.max_visible_rows

    def start(self):
        """Initialize the dashboard display"""
        with self.lock:
            self.running = True
            # Clear screen and hide cursor
            print(self.term.clear + self.term.hide_cursor, end="")
            self._calculate_layout()
            self._render_full_screen()

    def stop(self):
        """Clean up the dashboard"""
        with self.lock:
            self.running = False
            # Show cursor and move to bottom
            print(
                self.term.move(self.term.height - 1, 0) + self.term.show_cursor
            )

    def add_result(self, test_result):
        """Add a new test result and update display with auto-scroll"""
        with self.lock:
            if not self.running:
                return

            # Convert result to display row
            row = TestDisplayRow.from_result(test_result)
            self.results.append(row)

            # Maintain scroll buffer size to prevent memory issues
            if len(self.results) > self.scroll_buffer_size:
                self.results = self.results[-self.scroll_buffer_size :]

            # Update statistics
            self.total += 1
            if row.status == "PASS":
                self.passed += 1
            elif row.status == "FAIL":
                self.failed += 1
            elif row.status == "DRY-RUN":
                self.dry_run += 1

            # Update display with auto-scroll
            self._update_display_with_autoscroll()

    def _get_visible_results(self):
        """Get the results that should be visible based on auto-scroll settings"""
        max_rows = self._calculate_layout()

        if self.auto_scroll:
            # Always show the most recent results
            if len(self.results) <= max_rows:
                return self.results, 0  # Show all, no scroll
            else:
                visible_results = self.results[-max_rows:]
                scroll_position = len(self.results) - max_rows
                return visible_results, scroll_position
        else:
            # Manual scroll mode (for future enhancement)
            start_idx = max(
                0, len(self.results) - max_rows - self.scroll_offset
            )
            end_idx = len(self.results) - self.scroll_offset
            visible_results = self.results[start_idx:end_idx]
            return visible_results, start_idx

    def _render_full_screen(self):
        """Render the complete dashboard"""
        output = []
        # Header
        output.append(self.term.move(0, 0) + self.term.bold + self.term.blue)
        output.append("=" * self.term.width)
        output.append(
            self.term.move(1, 0)
            + "TestPilot - Live Test Results (Auto-Scroll)".center(
                self.term.width
            )
        )
        output.append(
            self.term.move(2, 0) + "=" * self.term.width + self.term.normal
        )
        # Progress line
        progress_line = self._format_progress_line()
        output.append(self.term.move(3, 0) + progress_line)
        # Table header (single line, no duplicate)
        output.append(self.term.move(4, 0) + self.term.bold)
        header = f"{'Index':<6} {'Host':<12} {'Sheet':<10} {'Test Name':<25} {'Method':<6} {'Status':<8} {'Duration':<8} {'Fail Reason':<40}"
        output.append(header + self.term.normal)
        output.append(self.term.move(5, 0) + "-" * len(header))
        # Get visible results
        visible_results, scroll_pos = self._get_visible_results()
        # Test results (visible window)
        for i, row in enumerate(visible_results):
            line_num = self.header_height + i
            if line_num < self.term.height - 1:  # Leave space for status line
                output.append(
                    self.term.move(line_num, 0)
                    + self._format_result_row(row, index=i + 1 + scroll_pos)
                )
        # Clear any remaining lines in the results area
        max_rows = self._calculate_layout()
        for i in range(len(visible_results), max_rows):
            line_num = self.header_height + i
            if line_num < self.term.height - 1:
                output.append(
                    self.term.move(line_num, 0) + self.term.clear_eol
                )
        # Status line at bottom with scroll info
        status_line = self._format_status_line_with_scroll(scroll_pos)
        output.append(
            self.term.move(self.term.height - 1, 0)
            + self.term.bold
            + status_line
            + self.term.normal
        )
        # Print all at once to reduce flicker
        print("".join(output), end="", flush=True)
        self.force_full_redraw = False

    def _update_display_with_autoscroll(self):
        """Update display with intelligent scrolling"""
        if not self.running:
            return

        max_rows = self._calculate_layout()
        visible_results, scroll_pos = self._get_visible_results()

        # Check if we need a full redraw
        need_full_redraw = (
            self.force_full_redraw
            or len(visible_results) != self.last_displayed_count
            or len(self.results) > max_rows
            and len(self.results) % max_rows == 1
        )

        if need_full_redraw:
            self._render_full_screen()
        else:
            # Fast update: just update the progress, new result line, and status
            self._fast_update(visible_results, scroll_pos)

        self.last_displayed_count = len(visible_results)

    def _fast_update(self, visible_results, scroll_pos):
        """Fast update for new results without full redraw"""
        # Update progress line
        progress_line = self._format_progress_line()
        print(
            self.term.move(3, 0) + self.term.clear_eol + progress_line, end=""
        )

        # Update the newest result line (always the last visible line when auto-scrolling)
        if visible_results and self.auto_scroll:
            newest_result = visible_results[-1]
            line_num = self.header_height + len(visible_results) - 1
            index = (
                len(self.results) - len(visible_results) + len(visible_results)
            )
            if line_num < self.term.height - 1:
                # Highlight the newest result briefly
                highlighted_row = self._format_result_row(
                    newest_result, highlight=True, index=index
                )
                print(
                    self.term.move(line_num, 0)
                    + self.term.clear_eol
                    + highlighted_row,
                    end="",
                )

        # Update status line with scroll info
        status_line = self._format_status_line_with_scroll(scroll_pos)
        print(
            self.term.move(self.term.height - 1, 0)
            + self.term.clear_eol
            + self.term.bold
            + status_line
            + self.term.normal,
            end="",
            flush=True,
        )

        # Remove highlight after brief moment (non-blocking)
        if visible_results and self.auto_scroll:

            def remove_highlight():
                time.sleep(0.2)
                if self.running:
                    index = (
                        len(self.results)
                        - len(visible_results)
                        + len(visible_results)
                    )
                    normal_row = self._format_result_row(
                        visible_results[-1], highlight=False, index=index
                    )
                    line_num = self.header_height + len(visible_results) - 1
                    if line_num < self.term.height - 1:
                        print(
                            self.term.move(line_num, 0)
                            + self.term.clear_eol
                            + normal_row,
                            end="",
                            flush=True,
                        )

            threading.Thread(target=remove_highlight, daemon=True).start()

    def _format_progress_line(self):
        """Format the progress line with scroll info"""
        elapsed = time.time() - self.start_time
        rate = self.total / elapsed if elapsed > 0 else 0

        progress = (
            f"Elapsed: {elapsed:.1f}s | "
            f"Rate: {rate:.1f}/sec | "
            f"Total: {self.total}"
        )

        # Add scroll indicator if results exceed visible area
        max_rows = self._calculate_layout()
        if len(self.results) > max_rows:
            hidden_count = len(self.results) - max_rows
            progress += (
                f" | Showing latest {max_rows} (+ {hidden_count} hidden)"
            )

        return progress

    def _format_result_row(
        self, row: TestDisplayRow, highlight=False, index=None
    ):
        """Format a single result row with colors and optional highlight"""
        # Choose color based on status
        if row.status == "PASS":
            status_colored = self.term.green + "✓ PASS " + self.term.normal
        elif row.status == "FAIL":
            status_colored = self.term.red + "✗ FAIL " + self.term.normal
        elif row.status == "DRY-RUN":
            status_colored = self.term.yellow + "◦ DRY  " + self.term.normal
        else:
            status_colored = f"{row.status:<8}"
        # Apply highlight if requested (for newest result)
        row_style = self.term.reverse if highlight else ""
        reset_style = self.term.normal if highlight else ""
        return (
            f"{row_style}{str(index) if index is not None else '':<6} "
            f"{row.host:<12} "
            f"{row.sheet:<10} "
            f"{row.test_name:<25} "
            f"{row.method:<6} "
            f"{status_colored:<8} "
            f"{row.duration:>6.2f}s "
            f"{row.fail_reason:<40}{reset_style}"
        )

    def _format_status_line_with_scroll(self, scroll_pos=0):
        """Format the bottom status line with scroll information"""
        base_status = self._format_status_line()

        # Add scroll information
        max_rows = self._calculate_layout()
        if len(self.results) > max_rows:
            if self.auto_scroll:
                scroll_info = f" | 📜 Auto-scroll: ON (latest {max_rows}/{len(self.results)})"
            else:
                showing_start = scroll_pos + 1
                showing_end = min(scroll_pos + max_rows, len(self.results))
                scroll_info = f" | 📜 Showing {showing_start}-{showing_end}/{len(self.results)}"

            return base_status + self.term.dim + scroll_info + self.term.normal

        return base_status

    def _format_status_line(self):
        """Format the bottom status line"""
        if self.dry_run > 0:
            return (
                f"Results: "
                f"{self.term.green}{self.passed} PASS{self.term.normal} | "
                f"{self.term.red}{self.failed} FAIL{self.term.normal} | "
                f"{self.term.yellow}{self.dry_run} DRY-RUN{self.term.normal} | "
                f"Total: {self.total}"
            )
        else:
            return (
                f"Results: "
                f"{self.term.green}{self.passed} PASS{self.term.normal} | "
                f"{self.term.red}{self.failed} FAIL{self.term.normal} | "
                f"Total: {self.total}"
            )

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

        success_rate = (
            (self.passed / self.total * 100) if self.total > 0 else 0
        )
        print(f"Success Rate: {success_rate:.1f}%")

        # Show failed tests if any
        if self.failed > 0:
            print(f"\nFailed Tests:")
            failed_results = [r for r in self.results if r.status == "FAIL"]
            for result in failed_results:
                print(
                    f"  ✗ {result.test_name} on {result.host} ({result.method})"
                )

        print("=" * 80)


class BlessedProgressOnly:
    """Minimal progress display using blessed - single line updates with auto-scroll awareness"""

    def __init__(self):
        if not BLESSED_AVAILABLE:
            raise ImportError(
                "blessed library not available. Install with: pip install blessed"
            )

        self.term = Terminal()
        self.start_time = time.time()
        self.passed = 0
        self.failed = 0
        self.dry_run = 0
        self.total = 0
        self.all_results = []
        self.running = False
        self.last_progress_length = 0

    def start(self):
        """Start progress display"""
        self.running = True
        print(self.term.hide_cursor, end="")
        print("\nTestPilot - Progress Mode (Auto-Scroll)")
        print("=" * 60)

    def stop(self):
        """Stop progress display"""
        self.running = False
        print(self.term.show_cursor, end="")

    def add_result(self, test_result):
        """Add result and update progress line with smart formatting"""
        if not self.running:
            return

        self.all_results.append(test_result)
        self.total += 1

        # Determine status
        if (
            hasattr(test_result, "result")
            and getattr(test_result, "result", "") == "DRY-RUN"
        ):
            self.dry_run += 1
            status_char = "◦"
        elif getattr(test_result, "passed", False):
            self.passed += 1
            status_char = "✓"
        else:
            self.failed += 1
            status_char = "✗"

        # Update progress line with current test info
        elapsed = time.time() - self.start_time
        rate = self.total / elapsed if elapsed > 0 else 0

        # Get current test info
        test_name = getattr(test_result, "test_name", "Unknown")[:20]
        host = getattr(test_result, "host", "")[:8]

        # Create progress line with colors and current test
        progress = (
            f"\r{self.term.clear_eol}"
            f"[{elapsed:>6.1f}s] "
            f"{status_char} {test_name:<20} on {host:<8} | "
            f"Total: {self.total:>3} | "
            f"{self.term.green}✓ {self.passed:>3}{self.term.normal} | "
            f"{self.term.red}✗ {self.failed:>3}{self.term.normal}"
        )

        if self.dry_run > 0:
            progress += (
                f" | {self.term.yellow}◦ {self.dry_run:>3}{self.term.normal}"
            )

        progress += f" | {rate:>4.1f}/sec"

        # Ensure line fits in terminal width
        if (
            len(
                progress.replace(self.term.green, "")
                .replace(self.term.red, "")
                .replace(self.term.yellow, "")
                .replace(self.term.normal, "")
            )
            > self.term.width
        ):
            # Truncate test name if line is too long
            test_name = test_name[:10] + "..."
            progress = (
                f"\r{self.term.clear_eol}"
                f"[{elapsed:>6.1f}s] "
                f"{status_char} {test_name:<13} | "
                f"T:{self.total} | "
                f"{self.term.green}✓{self.passed}{self.term.normal} | "
                f"{self.term.red}✗{self.failed}{self.term.normal}"
            )
            if self.dry_run > 0:
                progress += (
                    f" | {self.term.yellow}◦{self.dry_run}{self.term.normal}"
                )
            progress += f" | {rate:.1f}/s"

        print(progress, end="", flush=True)
        self.last_progress_length = len(progress)

    def print_final_summary(self):
        """Print final summary"""
        print("\n\n" + "=" * 60)
        print("FINAL SUMMARY")
        print("=" * 60)

        total_time = time.time() - self.start_time
        print(f"Total Time: {total_time:.2f}s")
        print(f"Total Tests: {self.total}")
        print(f"✓ Passed: {self.passed}")
        print(f"✗ Failed: {self.failed}")
        if self.dry_run > 0:
            print(f"◦ Dry-Run: {self.dry_run}")

        success_rate = (
            (self.passed / self.total * 100) if self.total > 0 else 0
        )
        print(f"Success Rate: {success_rate:.1f}%")
        print("=" * 60)


# Factory function for dashboard creation
def create_blessed_dashboard(mode="full", **kwargs):
    """Create appropriate blessed dashboard based on mode"""
    if not BLESSED_AVAILABLE:
        # Fallback to simple print-based display
        return SimpleFallbackDisplay()

    if mode == "full":
        return BlessedDashboard(**kwargs)
    elif mode == "progress":
        return BlessedProgressOnly()
    else:
        return BlessedDashboard(**kwargs)


class SimpleFallbackDisplay:
    """Fallback display when blessed is not available"""

    def __init__(self):
        self.results = []
        self.start_time = time.time()

    def start(self):
        print("\nTestPilot - Simple Display Mode (Auto-Scroll)")
        print("=" * 50)

    def stop(self):
        pass

    def add_result(self, test_result):
        self.results.append(test_result)

        # Simple one-line display with auto-scroll info
        status = (
            "DRY-RUN"
            if hasattr(test_result, "result")
            and getattr(test_result, "result", "") == "DRY-RUN"
            else ("PASS" if getattr(test_result, "passed", False) else "FAIL")
        )
        test_name = getattr(test_result, "test_name", "Unknown")[:20]
        host = getattr(test_result, "host", "Unknown")[:10]
        duration = getattr(test_result, "duration", 0.0)

        # Show only recent results (auto-scroll simulation)
        if len(self.results) > 50:  # Keep last 50 visible
            print(
                f"\n[Scrolled: showing latest 50 of {len(self.results)} results]"
            )

        print(
            f"[{len(self.results):>3}] {status:<7} {test_name:<20} on {host:<10} ({duration:.2f}s)"
        )

    def print_final_summary(self):
        passed = sum(1 for r in self.results if getattr(r, "passed", False))
        failed = len(self.results) - passed

        print(
            f"\nFinal: {len(self.results)} total | {passed} passed | {failed} failed"
        )
