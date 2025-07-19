#!/usr/bin/env python3
"""
Demo script for blessed dashboard
Shows how the blessed terminal dashboard handles rapid test updates
"""

import random
import sys
import time

from blessed_dashboard import create_blessed_dashboard


# Mock test result class
class MockTestResult:
    def __init__(self, test_name, host, status, duration):
        self.test_name = test_name
        self.host = host
        self.sheet = "DemoSheet"
        self.method = random.choice(["GET", "POST", "PUT", "DELETE"])
        self.passed = status == "PASS"
        self.duration = duration
        self.result = status


def generate_test_results(count=25):
    """Generate mock test results"""
    test_names = [
        "User_Authentication",
        "Profile_Update",
        "Product_Creation",
        "Order_Processing",
        "Payment_Gateway",
        "Data_Validation",
        "Cache_Refresh",
        "Health_Check",
        "Load_Balancer",
        "API_Rate_Limit",
        "Session_Management",
        "Database_Connection",
        "File_Upload",
        "Email_Service",
        "Notification_System",
        "Backup_Process",
        "Security_Scan",
        "Performance_Test",
        "Integration_Test",
        "Unit_Test",
    ]

    hosts = ["server-1", "server-2", "server-3", "api-gateway", "db-primary"]

    results = []
    for i in range(count):
        test_name = random.choice(test_names)
        host = random.choice(hosts)

        # 75% pass rate, 20% fail, 5% dry-run
        rand = random.random()
        if rand < 0.75:
            status = "PASS"
        elif rand < 0.95:
            status = "FAIL"
        else:
            status = "DRY-RUN"

        # Simulate realistic test durations
        duration = random.uniform(0.1, 3.0)
        results.append(MockTestResult(test_name, host, status, duration))

    return results


def demo_mode(mode, description):
    """Demo a specific display mode"""
    print(f"\n{'='*60}")
    print(f"BLESSED DASHBOARD DEMO: {description}")
    print(f"Mode: {mode}")
    print(f"{'='*60}")
    print("This demo simulates rapid test execution (0.2-0.8s per test)")
    print("Press Ctrl+C to stop the demo early")
    print("\nStarting in 3 seconds...")

    for i in range(3, 0, -1):
        print(f"{i}...", end="", flush=True)
        time.sleep(1)
    print("\n")

    try:
        # Create dashboard
        if mode == "full":
            dashboard = create_blessed_dashboard(
                mode="full", max_visible_rows=15
            )
        elif mode == "progress":
            dashboard = create_blessed_dashboard(mode="progress")
        else:
            dashboard = create_blessed_dashboard(mode="simple")

        dashboard.start()

        # Generate and add results with realistic timing
        results = generate_test_results(30)

        for i, result in enumerate(results):
            # Simulate test execution time (faster than real tests for demo)
            time.sleep(random.uniform(0.2, 0.8))
            dashboard.add_result(result)

        # Keep dashboard visible for a moment
        time.sleep(2)

        # Final summary
        dashboard.print_final_summary()

    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
        if "dashboard" in locals():
            dashboard.stop()
            print("\nDemo stopped.")

    except Exception as e:
        print(f"\nError in demo: {e}")
        if "dashboard" in locals():
            dashboard.stop()


def main():
    """Main demo function"""
    print("TestPilot Blessed Dashboard Demo")
    print("=" * 50)
    print("This demo showcases the blessed terminal dashboard")
    print("which provides flicker-free, live updating test results.")

    modes = [
        ("full", "Full Dashboard - Live table with progress"),
        ("progress", "Progress Only - Minimal real-time counters"),
        ("simple", "Simple Fallback - Basic line-by-line output"),
    ]

    # Check if blessed is available
    try:
        from blessed_dashboard import BLESSED_AVAILABLE

        if not BLESSED_AVAILABLE:
            print("\n❌ WARNING: blessed library not available")
            print("   Install with: pip install blessed")
            print("   Demos will use fallback mode only\n")
    except ImportError:
        print("\n❌ ERROR: blessed_dashboard module not found")
        return

    print(f"\nAvailable demos:")
    for i, (mode, desc) in enumerate(modes, 1):
        print(f"  {i}. {desc}")
    print("  q. Quit")

    while True:
        try:
            choice = (
                input(f"\nSelect demo (1-{len(modes)}) or 'q' to quit: ")
                .strip()
                .lower()
            )

            if choice == "q":
                break

            try:
                choice_num = int(choice)
                if 1 <= choice_num <= len(modes):
                    mode, description = modes[choice_num - 1]
                    demo_mode(mode, description)
                else:
                    print(f"Please enter a number between 1 and {len(modes)}")
            except ValueError:
                print("Please enter a valid number or 'q'")

        except KeyboardInterrupt:
            print("\nExiting demo...")
            break

    print("\nThanks for trying the blessed dashboard demo!")
    print("\nTo use with TestPilot:")
    print("  python test_pilot.py --file test.xlsx --display-mode blessed")
    print("  python test_pilot.py --file test.xlsx --display-mode progress")
    print("  python test_pilot.py --file test.xlsx --display-mode simple")


if __name__ == "__main__":
    main()
