#!/usr/bin/env python3
"""
Demo script to showcase different display modes for test results
This simulates rapid test execution to demonstrate flicker reduction
"""

import time
import random
from flicker_free_table import create_display

# Mock test result class
class MockTestResult:
    def __init__(self, test_name, host, status, duration):
        self.test_name = test_name
        self.host = host
        self.sheet = "DemoSheet"
        self.method = "GET"
        self.passed = status == "PASS"
        self.duration = duration
        self.result = status

def generate_test_results(count=20):
    """Generate mock test results"""
    test_names = [
        "Auth_Login", "User_Profile", "Create_Product", "Update_Product", 
        "Delete_Product", "Search_API", "Health_Check", "Payment_Flow",
        "Order_History", "User_Logout", "Admin_Access", "Data_Export",
        "Cache_Test", "Rate_Limit", "Error_Handling"
    ]
    
    hosts = ["host-1", "host-2", "host-3"]
    
    results = []
    for i in range(count):
        test_name = random.choice(test_names)
        host = random.choice(hosts)
        # 80% pass rate, 15% fail, 5% dry-run
        rand = random.random()
        if rand < 0.8:
            status = "PASS"
        elif rand < 0.95:
            status = "FAIL"
        else:
            status = "DRY-RUN"
        
        duration = random.uniform(0.1, 2.0)  # Random duration between 0.1-2.0 seconds
        results.append(MockTestResult(test_name, host, status, duration))
    
    return results

def demo_display_mode(display_type, description):
    """Demo a specific display mode"""
    print(f"\n{'='*60}")
    print(f"DEMO: {description}")
    print(f"Display Type: {display_type}")
    print(f"{'='*60}")
    
    # Create display
    if display_type == "batched":
        display = create_display(display_type, batch_size=3)
    elif display_type == "static_live":
        display = create_display(display_type, live_window_size=3)
    else:
        display = create_display(display_type)
    
    # Generate and add results with realistic timing
    results = generate_test_results(15)
    
    print(f"Starting demo with {len(results)} test results...")
    print("(Each test completes in 0.3-0.5 seconds to simulate real conditions)")
    
    for i, result in enumerate(results):
        # Simulate test execution time
        time.sleep(random.uniform(0.3, 0.5))
        display.add_result(result)
        
        # Show progress for non-visual modes
        if display_type == "progress_only" and (i + 1) % 5 == 0:
            print(f" (demo progress: {i+1}/{len(results)})")
    
    # Final summary
    display.print_final_summary()
    
    print(f"\nDemo of {display_type} completed!")
    input("Press Enter to continue to next demo...")

def main():
    """Main demo function"""
    print("TestPilot Display Modes Demo")
    print("This demo shows different ways to display test results")
    print("to reduce flickering during rapid test execution.")
    
    demos = [
        ("progress_only", "Progress Counter Only"),
        ("batched", "Batched Table Updates (every 3 results)"),
        ("static_live", "Static Summary + Live Recent Results"),
    ]
    
    for display_type, description in demos:
        try:
            demo_display_mode(display_type, description)
        except KeyboardInterrupt:
            print("\nDemo interrupted by user")
            break
        except Exception as e:
            print(f"Error in demo: {e}")
            continue
    
    print("\n" + "="*60)
    print("All demos completed!")
    print("\nTo use these modes with TestPilot:")
    print("  --display-mode progress_only   # Shows only counters during execution")
    print("  --display-mode batched         # Updates table in batches")
    print("  --display-mode static_live     # Static summary + recent results")
    print("  --display-mode standard        # Original table (default)")
    print("="*60)

if __name__ == "__main__":
    main()