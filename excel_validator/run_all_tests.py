#!/usr/bin/env python3
"""
Comprehensive test runner for Excel validator with multiple JSON configurations
Tests ranging from EASY to VERY HARD complexity levels
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path


class TestRunner:
    def __init__(self):
        self.test_configs_dir = Path("test_configs")
        self.excel_file = "nrf_tests_updated_v1.xlsx"
        self.validator_script = "excel_validator.py"
        self.results = {}

    def run_single_test(self, config_file: str) -> dict:
        """Run validation with a single configuration file"""
        print(f"\n🧪 Testing: {config_file}")
        print("=" * 60)

        start_time = time.time()

        try:
            # Run the validation
            result = subprocess.run(
                [
                    "python",
                    self.validator_script,
                    self.excel_file,
                    str(self.test_configs_dir / config_file),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            end_time = time.time()
            duration = end_time - start_time

            # Parse output
            output_lines = result.stdout.split("\n")
            issues_count = 0
            sheets_processed = []

            for line in output_lines:
                if "Total issues found:" in line:
                    try:
                        issues_count = int(line.split(":")[-1].strip())
                    except:
                        issues_count = 0
                elif "Sheets processed:" in line:
                    sheets_text = line.split(":", 1)[-1].strip()
                    sheets_processed = [
                        s.strip() for s in sheets_text.split(",") if s.strip()
                    ]

            test_result = {
                "status": "SUCCESS" if result.returncode == 0 else "FAILED",
                "issues_found": issues_count,
                "sheets_processed": len(sheets_processed),
                "duration_seconds": round(duration, 2),
                "stdout_lines": len(output_lines),
                "stderr": result.stderr.strip() if result.stderr else "",
                "return_code": result.returncode,
            }

            # Print summary
            print(f"✅ Status: {test_result['status']}")
            print(f"📊 Issues found: {test_result['issues_found']}")
            print(f"📄 Sheets processed: {test_result['sheets_processed']}")
            print(f"⏱️  Duration: {test_result['duration_seconds']}s")

            if test_result["stderr"]:
                print(f"⚠️  Error output: {test_result['stderr']}")

            return test_result

        except subprocess.TimeoutExpired:
            return {
                "status": "TIMEOUT",
                "issues_found": 0,
                "sheets_processed": 0,
                "duration_seconds": 30.0,
                "error": "Test timed out after 30 seconds",
            }
        except Exception as e:
            return {
                "status": "ERROR",
                "issues_found": 0,
                "sheets_processed": 0,
                "duration_seconds": 0,
                "error": str(e),
            }

    def categorize_test(self, filename: str) -> str:
        """Categorize test difficulty based on filename"""
        if (
            filename.startswith("01_")
            or filename.startswith("02_")
            or filename.startswith("03_")
        ):
            return "EASY"
        elif (
            filename.startswith("04_")
            or filename.startswith("05_")
            or filename.startswith("06_")
        ):
            return "MEDIUM"
        elif (
            filename.startswith("07_")
            or filename.startswith("08_")
            or filename.startswith("09_")
        ):
            return "HARD"
        elif (
            filename.startswith("10_")
            or filename.startswith("11_")
            or filename.startswith("12_")
        ):
            return "VERY HARD"
        elif (
            filename.startswith("13_")
            or filename.startswith("14_")
            or filename.startswith("15_")
        ):
            return "SPECIAL"
        else:
            return "UNKNOWN"

    def run_all_tests(self):
        """Run all test configurations"""
        print("🚀 STARTING COMPREHENSIVE EXCEL VALIDATOR TESTING")
        print("=" * 80)

        if not self.test_configs_dir.exists():
            print("❌ Error: test_configs directory not found!")
            return

        if not Path(self.excel_file).exists():
            print(f"❌ Error: Excel file '{self.excel_file}' not found!")
            return

        if not Path(self.validator_script).exists():
            print(
                f"❌ Error: Validator script '{self.validator_script}' not found!"
            )
            return

        # Get all JSON config files
        config_files = sorted(
            [
                f
                for f in os.listdir(self.test_configs_dir)
                if f.endswith(".json")
            ]
        )

        print(f"📝 Found {len(config_files)} test configurations")
        print(f"📊 Testing against: {self.excel_file}")

        # Run tests by category
        categories = {}
        for config_file in config_files:
            category = self.categorize_test(config_file)
            if category not in categories:
                categories[category] = []
            categories[category].append(config_file)

        # Test each category
        all_results = {}
        for category in ["EASY", "MEDIUM", "HARD", "VERY HARD", "SPECIAL"]:
            if category in categories:
                print(f"\n\n🎯 === {category} TESTS ===")
                for config_file in categories[category]:
                    result = self.run_single_test(config_file)
                    all_results[config_file] = {**result, "category": category}

        # Final summary
        self.print_final_summary(all_results)

        return all_results

    def print_final_summary(self, results: dict):
        """Print comprehensive test summary"""
        print("\n\n" + "=" * 80)
        print("📊 FINAL TEST SUMMARY")
        print("=" * 80)

        total_tests = len(results)
        successful_tests = sum(
            1 for r in results.values() if r["status"] == "SUCCESS"
        )
        failed_tests = sum(
            1 for r in results.values() if r["status"] == "FAILED"
        )
        timeout_tests = sum(
            1 for r in results.values() if r["status"] == "TIMEOUT"
        )
        error_tests = sum(
            1 for r in results.values() if r["status"] == "ERROR"
        )

        print(f"📈 Total Tests: {total_tests}")
        print(f"✅ Successful: {successful_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"⏱️  Timeouts: {timeout_tests}")
        print(f"💥 Errors: {error_tests}")
        print(f"🎯 Success Rate: {(successful_tests/total_tests)*100:.1f}%")

        # Category breakdown
        categories = {}
        for config, result in results.items():
            cat = result["category"]
            if cat not in categories:
                categories[cat] = {"total": 0, "success": 0}
            categories[cat]["total"] += 1
            if result["status"] == "SUCCESS":
                categories[cat]["success"] += 1

        print("\n📊 By Category:")
        for category, stats in categories.items():
            success_rate = (stats["success"] / stats["total"]) * 100
            print(
                f"  {category}: {stats['success']}/{stats['total']} ({success_rate:.1f}%)"
            )

        # Performance stats
        successful_results = [
            r for r in results.values() if r["status"] == "SUCCESS"
        ]
        if successful_results:
            total_issues = sum(r["issues_found"] for r in successful_results)
            avg_duration = sum(
                r["duration_seconds"] for r in successful_results
            ) / len(successful_results)

            print(f"\n⚡ Performance:")
            print(f"  Total Issues Found: {total_issues}")
            print(f"  Average Duration: {avg_duration:.2f}s")
            print(
                f"  Fastest Test: {min(r['duration_seconds'] for r in successful_results):.2f}s"
            )
            print(
                f"  Slowest Test: {max(r['duration_seconds'] for r in successful_results):.2f}s"
            )

        # Failed tests details
        failed_results = [
            (config, result)
            for config, result in results.items()
            if result["status"] != "SUCCESS"
        ]
        if failed_results:
            print(f"\n❌ Failed Tests Details:")
            for config, result in failed_results:
                print(f"  {config}: {result['status']}")
                if "error" in result:
                    print(f"    Error: {result['error']}")
                if result.get("stderr"):
                    print(f"    Stderr: {result['stderr'][:100]}...")


def main():
    runner = TestRunner()
    results = runner.run_all_tests()

    # Save results to file
    with open("test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Results saved to test_results.json")


if __name__ == "__main__":
    main()
