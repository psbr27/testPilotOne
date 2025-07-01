# =============================================================================
# Blessed Terminal Dashboard - Clean, flicker-free test results display
# =============================================================================

import time
import threading
from typing import List, Any, Optional
from dataclasses import dataclass

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
            
        return cls(
            host=getattr(result, "host", "")[:12],  # Truncate for display
            sheet=getattr(result, "sheet", "")[:10],
            test_name=getattr(result, "test_name", "")[:25],
            method=getattr(result, "method", "GET")[:6],
            status=status,
            duration=getattr(result, "duration", 0.0)
        )


class BlessedDashboard:
    """Terminal dashboard using blessed library for flicker-free updates"""
    
    def __init__(self, max_visible_rows=20):
        if not BLESSED_AVAILABLE:
            raise ImportError("blessed library not available. Install with: pip install blessed")
        
        self.term = Terminal()
        self.max_visible_rows = max_visible_rows
        self.results: List[TestDisplayRow] = []
        self.start_time = time.time()
        self.lock = threading.Lock()
        self.header_height = 6  # Header + progress + separator
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
            # Clear screen and hide cursor
            print(self.term.clear + self.term.hide_cursor, end='')
            self._render_full_screen()
    
    def stop(self):
        """Clean up the dashboard"""
        with self.lock:
            self.running = False
            # Show cursor and move to bottom
            print(self.term.move(self.term.height - 1, 0) + self.term.show_cursor)
    
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
            
            # Update display
            self._update_display()
    
    def _render_full_screen(self):
        """Render the complete dashboard"""
        output = []
        
        # Header
        output.append(self.term.move(0, 0) + self.term.bold + self.term.blue)
        output.append("=" * self.term.width)
        output.append(self.term.move(1, 0) + "TestPilot - Live Test Results".center(self.term.width))
        output.append(self.term.move(2, 0) + "=" * self.term.width + self.term.normal)
        
        # Progress line
        progress_line = self._format_progress_line()
        output.append(self.term.move(3, 0) + progress_line)
        
        # Table header
        output.append(self.term.move(4, 0) + self.term.bold)
        header = f"{'Host':<12} {'Sheet':<10} {'Test Name':<25} {'Method':<6} {'Status':<8} {'Duration':<8}"
        output.append(header + self.term.normal)
        output.append(self.term.move(5, 0) + "-" * len(header))
        
        # Test results (visible window)
        visible_results = self.results[-self.max_visible_rows:]
        for i, row in enumerate(visible_results):
            line_num = self.header_height + i
            if line_num < self.term.height - 1:  # Leave space for status line
                output.append(self.term.move(line_num, 0) + self._format_result_row(row))
        
        # Clear any remaining lines in the results area
        for i in range(len(visible_results), self.max_visible_rows):
            line_num = self.header_height + i
            if line_num < self.term.height - 1:
                output.append(self.term.move(line_num, 0) + self.term.clear_eol)
        
        # Status line at bottom
        status_line = self._format_status_line()
        output.append(self.term.move(self.term.height - 1, 0) + self.term.bold + status_line + self.term.normal)
        
        # Print all at once to reduce flicker
        print(''.join(output), end='', flush=True)
    
    def _update_display(self):
        """Update only the changing parts of the display"""
        if not self.running:
            return
            
        # Update progress line
        progress_line = self._format_progress_line()
        print(self.term.move(3, 0) + self.term.clear_eol + progress_line, end='')
        
        # Update only the last few result lines (most recent)
        visible_results = self.results[-self.max_visible_rows:]
        
        # Update the newest result (last line that changed)
        if visible_results:
            row = visible_results[-1]
            line_num = self.header_height + len(visible_results) - 1
            if line_num < self.term.height - 1:
                print(self.term.move(line_num, 0) + self.term.clear_eol + self._format_result_row(row), end='')
        
        # Update status line
        status_line = self._format_status_line()
        print(self.term.move(self.term.height - 1, 0) + self.term.clear_eol + self.term.bold + status_line + self.term.normal, end='', flush=True)
    
    def _format_progress_line(self):
        """Format the progress line"""
        elapsed = time.time() - self.start_time
        rate = self.total / elapsed if elapsed > 0 else 0
        
        return (
            f"Elapsed: {elapsed:.1f}s | "
            f"Rate: {rate:.1f}/sec | "
            f"Total: {self.total}"
        )
    
    def _format_result_row(self, row: TestDisplayRow):
        """Format a single result row with colors"""
        # Choose color based on status
        if row.status == "PASS":
            status_colored = self.term.green + "✓ PASS " + self.term.normal
        elif row.status == "FAIL":
            status_colored = self.term.red + "✗ FAIL " + self.term.normal
        elif row.status == "DRY-RUN":
            status_colored = self.term.yellow + "◦ DRY  " + self.term.normal
        else:
            status_colored = f"{row.status:<8}"
        
        return (
            f"{row.host:<12} "
            f"{row.sheet:<10} "
            f"{row.test_name:<25} "
            f"{row.method:<6} "
            f"{status_colored:<8} "
            f"{row.duration:>6.2f}s"
        )
    
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
        
        success_rate = (self.passed / self.total * 100) if self.total > 0 else 0
        print(f"Success Rate: {success_rate:.1f}%")
        
        # Show failed tests if any
        if self.failed > 0:
            print(f"\nFailed Tests:")
            failed_results = [r for r in self.results if r.status == "FAIL"]
            for result in failed_results:
                print(f"  ✗ {result.test_name} on {result.host} ({result.method})")
        
        print("=" * 80)


class BlessedProgressOnly:
    """Minimal progress display using blessed - single line updates"""
    
    def __init__(self):
        if not BLESSED_AVAILABLE:
            raise ImportError("blessed library not available. Install with: pip install blessed")
        
        self.term = Terminal()
        self.start_time = time.time()
        self.passed = 0
        self.failed = 0
        self.dry_run = 0
        self.total = 0
        self.all_results = []
        self.running = False
    
    def start(self):
        """Start progress display"""
        self.running = True
        print(self.term.hide_cursor, end='')
        print("\nTestPilot - Progress Only Mode")
        print("=" * 50)
    
    def stop(self):
        """Stop progress display"""
        self.running = False
        print(self.term.show_cursor, end='')
    
    def add_result(self, test_result):
        """Add result and update progress line"""
        if not self.running:
            return
            
        self.all_results.append(test_result)
        self.total += 1
        
        # Determine status
        if hasattr(test_result, "result") and getattr(test_result, "result", "") == "DRY-RUN":
            self.dry_run += 1
        elif getattr(test_result, "passed", False):
            self.passed += 1
        else:
            self.failed += 1
        
        # Update progress line
        elapsed = time.time() - self.start_time
        rate = self.total / elapsed if elapsed > 0 else 0
        
        # Create progress line with colors
        progress = (
            f"\r{self.term.clear_eol}"
            f"[{elapsed:>6.1f}s] "
            f"Tests: {self.total:>3} | "
            f"{self.term.green}✓ {self.passed:>3}{self.term.normal} | "
            f"{self.term.red}✗ {self.failed:>3}{self.term.normal}"
        )
        
        if self.dry_run > 0:
            progress += f" | {self.term.yellow}◦ {self.dry_run:>3}{self.term.normal}"
        
        progress += f" | Rate: {rate:>4.1f}/sec"
        
        print(progress, end='', flush=True)
    
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
        
        success_rate = (self.passed / self.total * 100) if self.total > 0 else 0
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
        print("\nTestPilot - Simple Display Mode")
        print("=" * 50)
    
    def stop(self):
        pass
    
    def add_result(self, test_result):
        self.results.append(test_result)
        
        # Simple one-line display
        status = "DRY-RUN" if hasattr(test_result, "result") and getattr(test_result, "result", "") == "DRY-RUN" else ("PASS" if getattr(test_result, "passed", False) else "FAIL")
        test_name = getattr(test_result, "test_name", "Unknown")[:20]
        host = getattr(test_result, "host", "Unknown")[:10]
        duration = getattr(test_result, "duration", 0.0)
        
        print(f"[{len(self.results):>3}] {status:<7} {test_name:<20} on {host:<10} ({duration:.2f}s)")
    
    def print_final_summary(self):
        passed = sum(1 for r in self.results if getattr(r, "passed", False))
        failed = len(self.results) - passed
        
        print(f"\nFinal: {len(self.results)} total | {passed} passed | {failed} failed")