#!/usr/bin/env python3
"""
Demo script showing different table display libraries with test data
Run different demos by uncommenting the sections at the bottom
"""

import time
import sys
import os
from dataclasses import dataclass
from typing import List

# Sample test data
@dataclass
class TestResult:
    host: str
    sheet: str
    test_name: str
    method: str
    result: str
    duration: float
    
    @property
    def passed(self):
        return self.result == "PASS"

# Your test data
test_data = [
    TestResult("G11", "AutoCreateSubs", "test_auto_create_subs_1", "GET", "PASS", 0.21),
    TestResult("G11", "SLFGroups", "test_add_slf_group", "PUT", "PASS", 0.23),
    TestResult("G11", "SLFGroups", "test_add_slf_group", "GET", "PASS", 0.21),
    TestResult("G11", "SLFGroups", "test_modify_slf_group", "PUT", "PASS", 0.22),
    TestResult("G11", "SLFGroups", "test_modify_slf_group", "GET", "PASS", 0.22),
    TestResult("G11", "SLFGroups", "test_delete_slf_group", "DELETE", "FAIL", 0.21),
    TestResult("G11", "SLFGroups", "test_delete_slf_group", "GET", "FAIL", 0.25),
    TestResult("G11", "DefaultGroupId", "test_default_group_id_1", "PUT", "PASS", 0.21),
    TestResult("G11", "DefaultGroupId", "test_default_group_id_1", "GET", "PASS", 0.24),
    TestResult("G11", "DefaultGroupId", "test_default_group_id_2", "GET", "PASS", 0.22),
    TestResult("G11", "DefaultGroupId", "test_default_group_id_3", "GET", "FAIL", 0.23),
    TestResult("G11", "DefaultGroupId", "test_default_group_id_4", "PUT", "PASS", 0.24),
]

def simulate_live_tests():
    """Generator that yields test results one by one to simulate live testing"""
    for result in test_data:
        yield result
        time.sleep(0.3)  # Simulate test execution time

# =============================================================================
# 1. RICH LIBRARY (Original but optimized)
# =============================================================================
def demo_rich_optimized():
    try:
        from rich.live import Live
        from rich.table import Table
        from rich.console import Console
        
        print("=== RICH (Optimized) Demo ===")
        console = Console()
        results = []
        
        def create_table(results_list):
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Host", style="cyan", width=8)
            table.add_column("Sheet", style="yellow", width=15)
            table.add_column("Test Name", style="white", width=25)
            table.add_column("Method", style="blue", width=8)
            table.add_column("Result", width=8)
            table.add_column("Duration (s)", justify="right", width=12)
            
            for result in results_list[-15:]:  # Show last 15 results
                result_style = "green" if result.passed else "red"
                table.add_row(
                    result.host,
                    result.sheet,
                    result.test_name,
                    result.method,
                    f"[{result_style}]{result.result}[/{result_style}]",
                    f"{result.duration:.2f}"
                )
            return table
        
        with Live(create_table([]), refresh_per_second=4, screen=True) as live:
            for result in simulate_live_tests():
                results.append(result)
                live.update(create_table(results))
                
    except ImportError:
        print("Rich not installed. Run: pip install rich")

# =============================================================================
# 2. BLESSED (Lightweight)
# =============================================================================
def demo_blessed():
    try:
        from blessed import Terminal
        
        print("=== BLESSED Demo ===")
        term = Terminal()
        results = []
        
        def display_tests(results_list):
            print(term.home + term.clear)
            print(term.bold("Test Results - Live Updates"))
            print("=" * 100)
            
            # Header
            header = f"{'Host':<8} {'Sheet':<15} {'Test Name':<25} {'Method':<8} {'Result':<8} {'Duration':<10}"
            print(term.bold(header))
            print("-" * 100)
            
            # Results
            for result in results_list[-20:]:
                color = term.green if result.passed else term.red
                row = f"{result.host:<8} {result.sheet:<15} {result.test_name:<25} {result.method:<8} {color}{result.result:<8}{term.normal} {result.duration:<10.2f}"
                print(row)
            
            print(f"\nTotal tests: {len(results_list)} | "
                  f"Passed: {sum(1 for r in results_list if r.passed)} | "
                  f"Failed: {sum(1 for r in results_list if not r.passed)}")
        
        with term.cbreak(), term.hidden_cursor():
            for result in simulate_live_tests():
                results.append(result)
                display_tests(results)
                time.sleep(0.1)
                
    except ImportError:
        print("Blessed not installed. Run: pip install blessed")

# =============================================================================
# 3. TABULATE with Clear Screen (Simple but effective)
# =============================================================================
def demo_tabulate():
    try:
        from tabulate import tabulate
        
        print("=== TABULATE Demo ===")
        results = []
        
        def display_results(results_list):
            os.system('clear' if os.name == 'posix' else 'cls')
            
            table_data = []
            for result in results_list[-15:]:
                # Add color indicators
                status_indicator = "✓" if result.passed else "✗"
                table_data.append([
                    result.host,
                    result.sheet,
                    result.test_name,
                    result.method,
                    f"{status_indicator} {result.result}",
                    f"{result.duration:.2f}s"
                ])
            
            print("🧪 Live Test Results")
            print("=" * 80)
            print(tabulate(table_data, 
                         headers=["Host", "Sheet", "Test Name", "Method", "Result", "Duration"],
                         tablefmt="grid",
                         colalign=("left", "left", "left", "center", "center", "right")))
            
            # Summary
            passed = sum(1 for r in results_list if r.passed)
            failed = len(results_list) - passed
            print(f"\n📊 Summary: {len(results_list)} total | {passed} passed | {failed} failed")
        
        for result in simulate_live_tests():
            results.append(result)
            display_results(results)
            
    except ImportError:
        print("Tabulate not installed. Run: pip install tabulate")

# =============================================================================
# 4. PRETTYTABLE (Classic)
# =============================================================================
def demo_prettytable():
    try:
        from prettytable import PrettyTable
        
        print("=== PRETTYTABLE Demo ===")
        results = []
        
        def create_table(results_list):
            table = PrettyTable()
            table.field_names = ["Host", "Sheet", "Test Name", "Method", "Result", "Duration (s)"]
            table.align["Test Name"] = "l"
            table.align["Sheet"] = "l"
            table.align["Result"] = "c"
            table.align["Duration (s)"] = "r"
            
            for result in results_list[-15:]:
                status = f"{'✓' if result.passed else '✗'} {result.result}"
                table.add_row([
                    result.host,
                    result.sheet,
                    result.test_name,
                    result.method,
                    status,
                    f"{result.duration:.2f}"
                ])
            
            return table
        
        for result in simulate_live_tests():
            results.append(result)
            os.system('clear' if os.name == 'posix' else 'cls')
            print("Live Test Results")
            print("=" * 80)
            print(create_table(results))
            print(f"\nProgress: {len(results)}/{len(test_data)} tests completed")
            
    except ImportError:
        print("PrettyTable not installed. Run: pip install prettytable")

# =============================================================================
# 5. SIMPLE ANSI ESCAPE CODES (No dependencies)
# =============================================================================
def demo_ansi_simple():
    print("=== SIMPLE ANSI CODES Demo (No Dependencies) ===")
    results = []
    
    def clear_screen():
        sys.stdout.write('\033[2J\033[H')  # Clear screen, move cursor to top
        
    def print_table(results_list):
        clear_screen()
        print("🧪 Live Test Results")
        print("=" * 100)
        
        # Header
        header = f"{'Host':<8} {'Sheet':<15} {'Test Name':<30} {'Method':<8} {'Result':<10} {'Duration':<10}"
        print(f"\033[1m{header}\033[0m")  # Bold header
        print("-" * 100)
        
        # Results with colors
        for result in results_list[-15:]:
            if result.passed:
                color = '\033[92m'  # Green
                status = "✓ PASS"
            else:
                color = '\033[91m'  # Red
                status = "✗ FAIL"
            
            reset = '\033[0m'
            row = f"{result.host:<8} {result.sheet:<15} {result.test_name:<30} {result.method:<8} {color}{status:<10}{reset} {result.duration:<10.2f}"
            print(row)
        
        # Summary
        passed = sum(1 for r in results_list if r.passed)
        failed = len(results_list) - passed
        print(f"\n📊 Total: {len(results_list)} | ✓ {passed} | ✗ {failed}")
        sys.stdout.flush()
    
    for result in simulate_live_tests():
        results.append(result)
        print_table(results)

# =============================================================================
# 6. TERMCOLOR (Colored simple output)
# =============================================================================
def demo_termcolor():
    try:
        from termcolor import colored
        
        print("=== TERMCOLOR Demo ===")
        results = []
        
        def print_colored_table(results_list):
            os.system('clear' if os.name == 'posix' else 'cls')
            
            print(colored("🧪 Live Test Results", "white", attrs=["bold"]))
            print("=" * 100)
            
            # Header
            header = f"{'Host':<8} {'Sheet':<15} {'Test Name':<30} {'Method':<8} {'Result':<10} {'Duration':<10}"
            print(colored(header, "white", attrs=["bold"]))
            print("-" * 100)
            
            for result in results_list[-15:]:
                color = "green" if result.passed else "red"
                status = "✓ PASS" if result.passed else "✗ FAIL"
                
                row = f"{result.host:<8} {result.sheet:<15} {result.test_name:<30} {result.method:<8} "
                print(row + colored(f"{status:<10}", color) + f" {result.duration:<10.2f}")
            
            # Summary
            passed = sum(1 for r in results_list if r.passed)
            failed = len(results_list) - passed
            summary = f"\n📊 Total: {len(results_list)} | "
            summary += colored(f"✓ {passed}", "green") + " | "
            summary += colored(f"✗ {failed}", "red")
            print(summary)
        
        for result in simulate_live_tests():
            results.append(result)
            print_colored_table(results)
            
    except ImportError:
        print("Termcolor not installed. Run: pip install termcolor")

# =============================================================================
# 7. TEXTUAL (Full-screen terminal app)
# =============================================================================
def demo_textual():
    try:
        from textual.app import App, ComposeResult
        from textual.widgets import DataTable, Header, Footer
        import asyncio
        
        class TestRunnerApp(App):
            """Live test results display using Textual"""
            
            def compose(self) -> ComposeResult:
                yield Header()
                yield DataTable()
                yield Footer()
            
            def on_mount(self) -> None:
                table = self.query_one(DataTable)
                table.add_columns("Host", "Sheet", "Test Name", "Method", "Result", "Duration (s)")
                
                # Add initial data
                self.add_test_results()
            
            def add_test_results(self):
                table = self.query_one(DataTable)
                
                def add_result_async():
                    for result in test_data:
                        status_symbol = "✓" if result.passed else "✗"
                        result_text = f"{status_symbol} {result.result}"
                        
                        table.add_row(
                            result.host,
                            result.sheet,
                            result.test_name,
                            result.method,
                            result_text,
                            f"{result.duration:.2f}s"
                        )
                        time.sleep(0.3)  # Simulate live updates
                
                import threading
                threading.Thread(target=add_result_async, daemon=True).start()
        
        print("=== TEXTUAL Demo ===")
        print("Starting full-screen app... (Press Ctrl+C to exit)")
        app = TestRunnerApp()
        app.run()
        
    except ImportError:
        print("Textual not installed. Run: pip install textual")
    except KeyboardInterrupt:
        print("\nTextual demo stopped")

# =============================================================================
# Main Demo Runner
# =============================================================================
def main():
    demos = {
        "1": ("Rich (Optimized)", demo_rich_optimized),
        "2": ("Blessed", demo_blessed),
        "3": ("Tabulate", demo_tabulate),
        "4": ("PrettyTable", demo_prettytable),
        "5": ("Simple ANSI (No deps)", demo_ansi_simple),
        "6": ("Termcolor", demo_termcolor),
        "7": ("Textual (Full-screen)", demo_textual),
    }
    
    print("📊 Live Table Display Demo")
    print("=" * 40)
    print("Available demos:")
    for key, (name, _) in demos.items():
        print(f"  {key}. {name}")
    print("  0. Run all (except Textual)")
    print("  q. Quit")
    
    choice = input("\nSelect demo (1-7, 0, q): ").strip()
    
    if choice == "q":
        return
    elif choice == "0":
        # Run all except Textual (since it's full-screen)
        for key in ["1", "2", "3", "4", "5", "6"]:
            if key in demos:
                print(f"\n{'='*50}")
                print(f"Running {demos[key][0]}...")
                print("="*50)
                try:
                    demos[key][1]()
                    input("\nPress Enter to continue to next demo...")
                except KeyboardInterrupt:
                    print("\nDemo interrupted, moving to next...")
                except Exception as e:
                    print(f"Error running demo: {e}")
                    input("Press Enter to continue...")
    elif choice in demos:
        print(f"\nRunning {demos[choice][0]}...")
        try:
            demos[choice][1]()
        except KeyboardInterrupt:
            print("\nDemo stopped by user")
    else:
        print("Invalid choice!")

if __name__ == "__main__":
    main()

# Uncomment below to run specific demos directly:
# demo_rich_optimized()
# demo_blessed()
# demo_tabulate()
# demo_prettytable()
# demo_ansi_simple()
# demo_termcolor()
# demo_textual()
