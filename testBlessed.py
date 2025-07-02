#!/usr/bin/env python3
"""
Fixed Blessed implementation that properly handles terminal height and auto-scrolling
"""

import time
from dataclasses import dataclass
from typing import List

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

# Sample test data (extended for demo)
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
] * 20  # Multiply to create many test results for scrolling demo

def demo_blessed_fixed():
    """Blessed with proper terminal height handling"""
    try:
        from blessed import Terminal
        
        term = Terminal()
        results = []
        
        def display_tests(results_list):
            print(term.home + term.clear)
            
            # Calculate available space
            header_lines = 4  # Title, separator, header, separator
            footer_lines = 2  # Summary and blank line
            available_height = term.height - header_lines - footer_lines
            
            # Show only what fits in terminal
            visible_results = results_list[-(available_height):] if len(results_list) > available_height else results_list
            
            print(term.bold("🧪 Test Results - Auto Scroll Fixed"))
            print("=" * min(100, term.width - 1))
            
            # Header
            header = f"{'Host':<8} {'Sheet':<15} {'Test Name':<25} {'Method':<8} {'Result':<8} {'Duration':<10}"
            print(term.bold(header))
            print("-" * min(100, term.width - 1))
            
            # Results (limited to terminal height)
            for result in visible_results:
                color = term.green if result.passed else term.red
                row = f"{result.host:<8} {result.sheet:<15} {result.test_name:<25} {result.method:<8} {color}{result.result:<8}{term.normal} {result.duration:<10.2f}"
                print(row)
            
            # Summary
            passed = sum(1 for r in results_list if r.passed)
            failed = len(results_list) - passed
            showing = len(visible_results)
            total = len(results_list)
            
            summary = f"📊 Showing {showing}/{total} | Passed: {passed} | Failed: {failed}"
            if total > showing:
                summary += f" | {term.yellow}(Scroll: showing last {showing}){term.normal}"
            print(summary)
        
        print("Starting demo with many test results...")
        print("Notice how it automatically shows only the last N results that fit in your terminal")
        time.sleep(2)
        
        with term.cbreak(), term.hidden_cursor():
            for i, result in enumerate(test_data):
                results.append(result)
                display_tests(results)
                time.sleep(0.1)  # Faster for demo
                
                # Stop at reasonable point for demo
                if i > 50:
                    break
                    
    except ImportError:
        print("Blessed not installed. Run: pip install blessed")
    except KeyboardInterrupt:
        print("\nDemo stopped")

def demo_blessed_with_scrollback():
    """Blessed with scrollback buffer (shows more advanced scrolling)"""
    try:
        from blessed import Terminal
        
        term = Terminal()
        results = []
        scroll_offset = 0
        
        def display_tests(results_list, offset=0):
            print(term.home + term.clear)
            
            # Calculate display parameters
            header_lines = 5
            footer_lines = 3
            available_height = term.height - header_lines - footer_lines
            
            # Calculate slice with offset
            start_idx = max(0, len(results_list) - available_height - offset)
            end_idx = len(results_list) - offset
            visible_results = results_list[start_idx:end_idx]
            
            print(term.bold("🧪 Test Results - With Scrollback"))
            print("=" * min(100, term.width - 1))
            print(f"{term.dim}Use ↑/↓ arrows to scroll, 'q' to quit{term.normal}")
            
            # Header
            header = f"{'Host':<8} {'Sheet':<15} {'Test Name':<25} {'Method':<8} {'Result':<8} {'Duration':<10}"
            print(term.bold(header))
            print("-" * min(100, term.width - 1))
            
            # Results
            for result in visible_results:
                color = term.green if result.passed else term.red
                row = f"{result.host:<8} {result.sheet:<15} {result.test_name:<25} {result.method:<8} {color}{result.result:<8}{term.normal} {result.duration:<10.2f}"
                print(row)
            
            # Summary with scroll info
            passed = sum(1 for r in results_list if r.passed)
            failed = len(results_list) - passed
            total = len(results_list)
            
            scroll_info = ""
            if offset > 0:
                scroll_info = f" | {term.yellow}Scrolled up {offset} lines{term.normal}"
            elif total > available_height:
                scroll_info = f" | {term.yellow}Showing latest results{term.normal}"
                
            summary = f"📊 Total: {total} | Passed: {passed} | Failed: {failed}{scroll_info}"
            print(summary)
        
        print("Demo with scrollback capability...")
        print("This will show how to handle large result sets with user scrolling")
        time.sleep(2)
        
        # Add all results first
        results.extend(test_data)
        
        with term.cbreak(), term.hidden_cursor():
            while True:
                display_tests(results, scroll_offset)
                
                key = term.inkey(timeout=1)
                if key.name == 'KEY_UP':
                    scroll_offset = min(scroll_offset + 1, len(results) - 1)
                elif key.name == 'KEY_DOWN':
                    scroll_offset = max(scroll_offset - 1, 0)
                elif key == 'q':
                    break
                    
    except ImportError:
        print("Blessed not installed. Run: pip install blessed")
    except KeyboardInterrupt:
        print("\nDemo stopped")

def demo_blessed_live_with_autoscroll():
    """Live updates with proper auto-scroll"""
    try:
        from blessed import Terminal
        
        term = Terminal()
        results = []
        
        def display_tests(results_list):
            print(term.home + term.clear)
            
            # Smart height calculation
            available_height = term.height - 6  # Reserve space for headers/footers
            
            # Always show the most recent results
            if len(results_list) > available_height:
                visible_results = results_list[-available_height:]
                scroll_indicator = f" (showing last {available_height} of {len(results_list)})"
            else:
                visible_results = results_list
                scroll_indicator = ""
            
            print(term.bold(f"🧪 Live Test Results{scroll_indicator}"))
            print("=" * min(100, term.width - 1))
            
            # Header
            header = f"{'Host':<8} {'Sheet':<15} {'Test Name':<25} {'Method':<8} {'Result':<8} {'Duration':<10}"
            print(term.bold(header))
            print("-" * min(100, term.width - 1))
            
            # Results
            for i, result in enumerate(visible_results):
                color = term.green if result.passed else term.red
                
                # Highlight the newest result
                style = term.reverse if i == len(visible_results) - 1 and len(results_list) > 1 else ""
                
                row = f"{style}{result.host:<8} {result.sheet:<15} {result.test_name:<25} {result.method:<8} {color}{result.result:<8}{term.normal}{style} {result.duration:<10.2f}{term.normal}"
                print(row)
            
            # Summary
            passed = sum(1 for r in results_list if r.passed)
            failed = len(results_list) - passed
            print(f"\n📊 Total: {len(results_list)} | ✅ {passed} | ❌ {failed}")
        
        print("Live demo with auto-scroll...")
        print("The table will automatically scroll as new results come in")
        time.sleep(2)
        
        with term.cbreak(), term.hidden_cursor():
            for result in test_data:
                results.append(result)
                display_tests(results)
                time.sleep(0.3)
                
    except ImportError:
        print("Blessed not installed. Run: pip install blessed")
    except KeyboardInterrupt:
        print("\nDemo stopped")

def main():
    demos = {
        "1": ("Fixed Auto-Scroll", demo_blessed_fixed),
        "2": ("With Scrollback Controls", demo_blessed_with_scrollback), 
        "3": ("Live with Auto-Scroll", demo_blessed_live_with_autoscroll),
    }
    
    print("🔧 Blessed Auto-Scroll Fixes")
    print("=" * 40)
    for key, (name, _) in demos.items():
        print(f"  {key}. {name}")
    print("  q. Quit")
    
    choice = input("\nSelect demo (1-3, q): ").strip()
    
    if choice == "q":
        return
    elif choice in demos:
        print(f"\nRunning {demos[choice][0]}...")
        try:
            demos[choice][1]()
        except KeyboardInterrupt:
            print("\nDemo stopped")
    else:
        print("Invalid choice!")

if __name__ == "__main__":
    main()
