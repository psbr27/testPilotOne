#!/usr/bin/env python3
"""
Comprehensive Audit Test Runner

Runs all audit tests with detailed reporting and coverage analysis.
Provides different test execution modes and generates test reports.
"""

import json
import os
import sys
import time
import unittest
from io import StringIO

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# Import all test modules
from tests.audit.test_audit_engine import TestAuditEngine
from tests.audit.test_audit_exporter import TestAuditExporter
from tests.audit.test_audit_integration import TestAuditIntegration
from tests.audit.test_audit_processor import TestAuditProcessor


class AuditTestRunner:
    """Comprehensive test runner for audit functionality"""

    def __init__(self):
        self.test_modules = [
            ("Engine Tests", TestAuditEngine),
            ("Exporter Tests", TestAuditExporter),
            ("Processor Tests", TestAuditProcessor),
            ("Integration Tests", TestAuditIntegration),
        ]

        self.results = {}
        self.total_tests = 0
        self.total_failures = 0
        self.total_errors = 0
        self.total_skipped = 0
        self.execution_time = 0

    def run_all_tests(self, verbosity=2):
        """Run all audit tests with specified verbosity"""
        print("=" * 80)
        print("🔍 TESTPILOT AUDIT FUNCTIONALITY - COMPREHENSIVE TEST SUITE")
        print("=" * 80)
        print()

        start_time = time.time()

        # Run each test module
        for module_name, test_class in self.test_modules:
            print(f"📋 Running {module_name}...")
            print("-" * 60)

            # Create test suite for this module
            loader = unittest.TestLoader()
            suite = loader.loadTestsFromTestCase(test_class)

            # Run tests with custom result tracking
            stream = StringIO()
            runner = unittest.TextTestRunner(
                stream=stream, verbosity=verbosity, buffer=True
            )

            module_start = time.time()
            result = runner.run(suite)
            module_time = time.time() - module_start

            # Store results
            self.results[module_name] = {
                "tests_run": result.testsRun,
                "failures": len(result.failures),
                "errors": len(result.errors),
                "skipped": len(result.skipped),
                "success": result.wasSuccessful(),
                "execution_time": module_time,
                "details": stream.getvalue(),
            }

            # Update totals
            self.total_tests += result.testsRun
            self.total_failures += len(result.failures)
            self.total_errors += len(result.errors)
            self.total_skipped += len(result.skipped)

            # Print module summary
            status = "✅ PASSED" if result.wasSuccessful() else "❌ FAILED"
            print(
                f"{status} - {result.testsRun} tests, {len(result.failures)} failures, {len(result.errors)} errors ({module_time:.2f}s)"
            )

            if not result.wasSuccessful() and verbosity > 0:
                print("\nFailures and Errors:")
                print(stream.getvalue())

            print()

        self.execution_time = time.time() - start_time

        # Print overall summary
        self._print_summary()

        # Generate test report
        self._generate_report()

        return self.total_failures == 0 and self.total_errors == 0

    def run_specific_module(self, module_name, verbosity=2):
        """Run tests for a specific module"""
        module_map = dict(self.test_modules)

        if module_name not in module_map:
            print(f"❌ Unknown module: {module_name}")
            print(f"Available modules: {list(module_map.keys())}")
            return False

        print(f"🔍 Running {module_name} only...")
        print("-" * 60)

        test_class = module_map[module_name]
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromTestCase(test_class)

        runner = unittest.TextTestRunner(verbosity=verbosity)
        result = runner.run(suite)

        return result.wasSuccessful()

    def run_performance_tests_only(self, verbosity=1):
        """Run only performance-related tests"""
        print("🚀 Running Performance Tests Only...")
        print("-" * 60)

        # Performance test patterns
        performance_patterns = [
            "performance",
            "stress",
            "large",
            "many",
            "rapid",
            "concurrent",
            "memory",
            "batch",
        ]

        loader = unittest.TestLoader()
        suite = unittest.TestSuite()

        # Find performance tests
        for module_name, test_class in self.test_modules:
            class_suite = loader.loadTestsFromTestCase(test_class)

            for test_group in class_suite:
                for test in test_group:
                    test_name = test._testMethodName.lower()
                    if any(
                        pattern in test_name
                        for pattern in performance_patterns
                    ):
                        suite.addTest(test)

        runner = unittest.TextTestRunner(verbosity=verbosity)
        result = runner.run(suite)

        return result.wasSuccessful()

    def run_edge_cases_only(self, verbosity=1):
        """Run only edge case tests"""
        print("🎯 Running Edge Case Tests Only...")
        print("-" * 60)

        loader = unittest.TestLoader()
        suite = loader.loadTestsFromTestCase(TestAuditEdgeCases)

        runner = unittest.TextTestRunner(verbosity=verbosity)
        result = runner.run(suite)

        return result.wasSuccessful()

    def _print_summary(self):
        """Print comprehensive test summary"""
        print("=" * 80)
        print("📊 COMPREHENSIVE TEST SUMMARY")
        print("=" * 80)

        # Overall statistics
        total_passed = (
            self.total_tests
            - self.total_failures
            - self.total_errors
            - self.total_skipped
        )
        pass_rate = (
            (total_passed / self.total_tests * 100)
            if self.total_tests > 0
            else 0
        )

        print(f"📈 Overall Results:")
        print(f"   Total Tests: {self.total_tests}")
        print(f"   Passed: {total_passed}")
        print(f"   Failed: {self.total_failures}")
        print(f"   Errors: {self.total_errors}")
        print(f"   Skipped: {self.total_skipped}")
        print(f"   Pass Rate: {pass_rate:.1f}%")
        print(f"   Execution Time: {self.execution_time:.2f}s")
        print()

        # Module breakdown
        print("📋 Module Breakdown:")
        for module_name, results in self.results.items():
            status_icon = "✅" if results["success"] else "❌"
            print(
                f"   {status_icon} {module_name:20} - {results['tests_run']:3d} tests ({results['execution_time']:6.2f}s)"
            )
        print()

        # Final status
        overall_success = self.total_failures == 0 and self.total_errors == 0
        if overall_success:
            print(
                "🎉 ALL TESTS PASSED! Audit functionality is working correctly."
            )
        else:
            print("⚠️  SOME TESTS FAILED! Please review the failures above.")

        print("=" * 80)

    def _generate_report(self):
        """Generate detailed test report"""
        report_data = {
            "test_run_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "total_tests": self.total_tests,
                "total_passed": self.total_tests
                - self.total_failures
                - self.total_errors
                - self.total_skipped,
                "total_failures": self.total_failures,
                "total_errors": self.total_errors,
                "total_skipped": self.total_skipped,
                "pass_rate_percent": (
                    (
                        self.total_tests
                        - self.total_failures
                        - self.total_errors
                        - self.total_skipped
                    )
                    / self.total_tests
                    * 100
                    if self.total_tests > 0
                    else 0
                ),
                "execution_time_seconds": self.execution_time,
            },
            "module_results": self.results,
        }

        # Save JSON report
        report_file = f"audit_test_report_{int(time.time())}.json"
        with open(report_file, "w") as f:
            json.dump(report_data, f, indent=2)

        print(f"📄 Detailed test report saved to: {report_file}")


def main():
    """Main test runner entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="TestPilot Audit Test Runner")
    parser.add_argument(
        "--module", "-m", help="Run specific module tests only"
    )
    parser.add_argument(
        "--performance",
        "-p",
        action="store_true",
        help="Run performance tests only",
    )
    parser.add_argument(
        "--edge-cases",
        "-e",
        action="store_true",
        help="Run edge case tests only",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        type=int,
        default=2,
        choices=[0, 1, 2],
        help="Verbosity level",
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Minimal output"
    )

    args = parser.parse_args()

    if args.quiet:
        args.verbose = 0

    runner = AuditTestRunner()

    try:
        if args.module:
            success = runner.run_specific_module(args.module, args.verbose)
        elif args.performance:
            success = runner.run_performance_tests_only(args.verbose)
        elif args.edge_cases:
            success = runner.run_edge_cases_only(args.verbose)
        else:
            success = runner.run_all_tests(args.verbose)

        # Exit with appropriate code
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n⚠️  Test execution interrupted by user")
        sys.exit(2)
    except Exception as e:
        print(f"\n❌ Test runner error: {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()
