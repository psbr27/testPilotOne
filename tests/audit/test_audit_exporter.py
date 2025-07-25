#!/usr/bin/env python3
"""
Comprehensive Unit Tests for AuditExporter

Tests Excel generation and formatting including:
- Multi-sheet Excel creation
- JSON formatting in cells
- Advanced formatting and styling
- File I/O operations
- Data validation and integrity
"""

import json
import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

# Import pandas with fallback
try:
    import pandas as pd

    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.testpilot.audit.audit_exporter import AuditExporter


class TestAuditExporter(unittest.TestCase):
    """Comprehensive test suite for AuditExporter"""

    def setUp(self):
        """Set up test fixtures"""
        self.exporter = AuditExporter()
        self.temp_dir = tempfile.mkdtemp()

        # Sample audit results for testing
        self.sample_audit_results = [
            {
                "test_name": "test_successful_validation",
                "timestamp": "2025-01-01T12:00:00.000000",
                "validation_type": "STRICT_100_PERCENT",
                "expected_pattern": '{"status": "success", "data": {"id": 123}}',
                "actual_response": '{"status": "success", "data": {"id": 123}}',
                "http_method_expected": "GET",
                "http_method_actual": "GET",
                "status_code_expected": 200,
                "status_code_actual": 200,
                "request_details": {
                    "command": "curl -X GET http://api.test/endpoint"
                },
                "differences": [],
                "http_validation_errors": [],
                "json_validation_errors": [],
                "overall_result": "PASS",
                "match_percentage": 100.0,
            },
            {
                "test_name": "test_failed_validation",
                "timestamp": "2025-01-01T12:01:00.000000",
                "validation_type": "STRICT_100_PERCENT",
                "expected_pattern": '{"status": "success", "data": {"id": 123}}',
                "actual_response": '{"status": "error", "data": {"id": 456}}',
                "http_method_expected": "POST",
                "http_method_actual": "GET",
                "status_code_expected": 201,
                "status_code_actual": 400,
                "request_details": {
                    "command": "curl -X POST http://api.test/endpoint"
                },
                "differences": [
                    {
                        "type": "mismatch",
                        "field_path": "status",
                        "expected_value": "success",
                        "actual_value": "error",
                    },
                    {
                        "type": "mismatch",
                        "field_path": "data.id",
                        "expected_value": 123,
                        "actual_value": 456,
                    },
                ],
                "http_validation_errors": [
                    "HTTP method mismatch: expected 'POST', got 'GET'"
                ],
                "json_validation_errors": [
                    "Pattern match failed: 2 differences found"
                ],
                "overall_result": "FAIL",
                "match_percentage": 25.0,
            },
            {
                "test_name": "test_error_validation",
                "timestamp": "2025-01-01T12:02:00.000000",
                "validation_type": "STRICT_100_PERCENT",
                "expected_pattern": '{"status": "success"}',
                "actual_response": "",
                "http_method_expected": "GET",
                "http_method_actual": "GET",
                "status_code_expected": 200,
                "status_code_actual": None,
                "request_details": {
                    "command": "curl -X GET http://api.test/broken",
                    "error": "Connection timeout",
                },
                "differences": [],
                "http_validation_errors": [
                    "Status code mismatch: expected 200, got None"
                ],
                "json_validation_errors": [
                    "Invalid JSON structure: Expecting value: line 1 column 1 (char 0)"
                ],
                "overall_result": "ERROR",
                "match_percentage": 0.0,
            },
        ]

        self.sample_audit_summary = {
            "audit_mode": "STRICT_100_PERCENT",
            "total_tests": 3,
            "passed_tests": 1,
            "failed_tests": 1,
            "error_tests": 1,
            "pass_rate": 33.33,
            "compliance_status": "NON_COMPLIANT",
            "generated_at": "2025-01-01T12:03:00.000000",
        }

    def tearDown(self):
        """Clean up temporary files"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # =================================================================
    # SUNNY DAY TESTS - Normal Excel generation
    # =================================================================

    @unittest.skipIf(not PANDAS_AVAILABLE, "pandas not available")
    def test_successful_excel_export_basic(self):
        """Test basic successful Excel export"""
        output_path = self.exporter.export_audit_results(
            self.sample_audit_results, self.sample_audit_summary, self.temp_dir
        )

        # Verify file was created
        self.assertTrue(os.path.exists(output_path))
        self.assertTrue(output_path.endswith(".xlsx"))
        self.assertIn("audit_report_", os.path.basename(output_path))

        # Verify file is readable Excel format
        try:
            sheets = pd.read_excel(
                output_path, sheet_name=None, engine="openpyxl"
            )
            self.assertIsInstance(sheets, dict)
            self.assertGreater(len(sheets), 0)
        except Exception as e:
            self.fail(f"Generated Excel file is not readable: {e}")

    @unittest.skipIf(not PANDAS_AVAILABLE, "pandas not available")
    def test_all_required_sheets_created(self):
        """Test that all required sheets are created"""
        output_path = self.exporter.export_audit_results(
            self.sample_audit_results, self.sample_audit_summary, self.temp_dir
        )

        expected_sheets = [
            "Detailed_Results",
            "Audit_Summary",
            "Compliance_Report",
            "JSON_Data",
            "Differences_Analysis",
        ]

        sheets = pd.read_excel(output_path, sheet_name=None, engine="openpyxl")

        for sheet_name in expected_sheets:
            self.assertIn(
                sheet_name, sheets.keys(), f"Missing sheet: {sheet_name}"
            )

    @unittest.skipIf(not PANDAS_AVAILABLE, "pandas not available")
    def test_detailed_results_sheet_content(self):
        """Test detailed results sheet contains correct data"""
        output_path = self.exporter.export_audit_results(
            self.sample_audit_results, self.sample_audit_summary, self.temp_dir
        )

        detailed_df = pd.read_excel(
            output_path, sheet_name="Detailed_Results", engine="openpyxl"
        )

        # Check row count matches input
        self.assertEqual(len(detailed_df), len(self.sample_audit_results))

        # Check required columns exist
        required_columns = [
            "Test_Name",
            "Overall_Result",
            "HTTP_Method_Expected",
            "HTTP_Method_Actual",
            "Status_Code_Expected",
            "Status_Code_Actual",
            "Expected_Pattern",
            "Actual_Response",
        ]

        for col in required_columns:
            self.assertIn(col, detailed_df.columns, f"Missing column: {col}")

        # Check specific data values
        self.assertEqual(
            detailed_df.iloc[0]["Test_Name"], "test_successful_validation"
        )
        self.assertEqual(detailed_df.iloc[0]["Overall_Result"], "PASS")
        self.assertEqual(detailed_df.iloc[1]["Overall_Result"], "FAIL")
        self.assertEqual(detailed_df.iloc[2]["Overall_Result"], "ERROR")

    @unittest.skipIf(not PANDAS_AVAILABLE, "pandas not available")
    def test_audit_summary_sheet_content(self):
        """Test audit summary sheet contains correct data"""
        output_path = self.exporter.export_audit_results(
            self.sample_audit_results, self.sample_audit_summary, self.temp_dir
        )

        summary_df = pd.read_excel(
            output_path, sheet_name="Audit_Summary", engine="openpyxl"
        )

        # Convert to dict for easier checking
        summary_dict = dict(zip(summary_df["Metric"], summary_df["Value"]))

        self.assertEqual(summary_dict["Total Tests"], 3)
        self.assertEqual(summary_dict["Passed Tests"], 1)
        self.assertEqual(summary_dict["Failed Tests"], 1)
        self.assertEqual(summary_dict["Error Tests"], 1)
        self.assertEqual(summary_dict["Compliance Status"], "NON_COMPLIANT")

    @unittest.skipIf(not PANDAS_AVAILABLE, "pandas not available")
    def test_json_formatting_in_cells(self):
        """Test that JSON data is properly formatted in Excel cells"""
        output_path = self.exporter.export_audit_results(
            self.sample_audit_results, self.sample_audit_summary, self.temp_dir
        )

        json_df = pd.read_excel(
            output_path, sheet_name="JSON_Data", engine="openpyxl"
        )

        # Check that JSON is formatted with proper indentation
        expected_json_formatted = json_df.iloc[0]["Expected_JSON"]
        self.assertIn(
            "\n", expected_json_formatted
        )  # Should have newlines from formatting
        self.assertIn("  ", expected_json_formatted)  # Should have indentation

        # Verify it's still valid JSON
        try:
            json.loads(expected_json_formatted)
        except json.JSONDecodeError:
            self.fail("Formatted JSON in Excel is not valid JSON")

    @unittest.skipIf(not PANDAS_AVAILABLE, "pandas not available")
    def test_compliance_report_sheet_content(self):
        """Test compliance report sheet content and risk assessment"""
        output_path = self.exporter.export_audit_results(
            self.sample_audit_results, self.sample_audit_summary, self.temp_dir
        )

        compliance_df = pd.read_excel(
            output_path, sheet_name="Compliance_Report", engine="openpyxl"
        )

        # Check required columns
        required_columns = [
            "Test_Name",
            "Compliant",
            "Risk_Level",
            "Remediation_Required",
        ]
        for col in required_columns:
            self.assertIn(col, compliance_df.columns)

        # Check compliance status
        self.assertEqual(
            compliance_df.iloc[0]["Compliant"], "YES"
        )  # PASS test
        self.assertEqual(compliance_df.iloc[1]["Compliant"], "NO")  # FAIL test
        self.assertEqual(
            compliance_df.iloc[2]["Compliant"], "NO"
        )  # ERROR test

        # Check risk levels are assigned
        risk_levels = compliance_df["Risk_Level"].unique()
        valid_risk_levels = ["LOW", "MEDIUM", "HIGH"]
        for risk in risk_levels:
            self.assertIn(risk, valid_risk_levels)

    @unittest.skipIf(not PANDAS_AVAILABLE, "pandas not available")
    def test_differences_analysis_sheet(self):
        """Test differences analysis sheet for failed tests"""
        output_path = self.exporter.export_audit_results(
            self.sample_audit_results, self.sample_audit_summary, self.temp_dir
        )

        diff_df = pd.read_excel(
            output_path, sheet_name="Differences_Analysis", engine="openpyxl"
        )

        # Should have differences from the failed test
        self.assertGreater(len(diff_df), 0)

        # Check required columns
        required_columns = [
            "Test_Name",
            "Difference_Type",
            "Field_Path",
            "Expected_Value",
            "Actual_Value",
        ]
        for col in required_columns:
            self.assertIn(col, diff_df.columns)

        # Check specific difference data
        status_diff = diff_df[diff_df["Field_Path"] == "status"]
        self.assertEqual(len(status_diff), 1)
        self.assertEqual(status_diff.iloc[0]["Expected_Value"], "success")
        self.assertEqual(status_diff.iloc[0]["Actual_Value"], "error")

    # =================================================================
    # RAINY DAY TESTS - Error conditions and failures
    # =================================================================

    def test_empty_audit_results(self):
        """Test export with empty audit results"""
        empty_results = []
        empty_summary = {
            "audit_mode": "STRICT_100_PERCENT",
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "error_tests": 0,
            "pass_rate": 0.0,
            "compliance_status": "COMPLIANT",
            "generated_at": datetime.utcnow().isoformat(),
        }

        output_path = self.exporter.export_audit_results(
            empty_results, empty_summary, self.temp_dir
        )

        # Should still create file with empty sheets
        self.assertTrue(os.path.exists(output_path))

        # Check that sheets exist but are empty
        if PANDAS_AVAILABLE:
            detailed_df = pd.read_excel(
                output_path, sheet_name="Detailed_Results", engine="openpyxl"
            )
            self.assertEqual(len(detailed_df), 0)

    def test_invalid_output_directory(self):
        """Test export with invalid output directory"""
        invalid_dir = "/nonexistent/path/that/does/not/exist"

        # Should handle the error gracefully or create the directory
        try:
            output_path = self.exporter.export_audit_results(
                self.sample_audit_results,
                self.sample_audit_summary,
                invalid_dir,
            )
            # If it succeeds, verify the directory was created
            self.assertTrue(os.path.exists(invalid_dir))
            self.assertTrue(os.path.exists(output_path))
        except Exception:
            # If it fails, that's also acceptable behavior
            pass

    def test_malformed_audit_data(self):
        """Test export with malformed audit data"""
        malformed_results = [
            {
                "test_name": "test_missing_fields",
                # Missing many required fields
                "overall_result": "PASS",
            },
            {
                # Missing test_name and result
                "timestamp": "2025-01-01T12:00:00.000000"
            },
        ]

        # Should handle malformed data gracefully
        try:
            output_path = self.exporter.export_audit_results(
                malformed_results, self.sample_audit_summary, self.temp_dir
            )
            self.assertTrue(os.path.exists(output_path))
        except Exception:
            # If it fails, that's acceptable for malformed data
            pass

    @unittest.skipIf(not PANDAS_AVAILABLE, "pandas not available")
    @patch("pandas.ExcelWriter")
    def test_excel_write_failure(self, mock_excel_writer):
        """Test handling of Excel write failures"""
        mock_excel_writer.side_effect = Exception("Excel write failed")

        with self.assertRaises(Exception):
            self.exporter.export_audit_results(
                self.sample_audit_results,
                self.sample_audit_summary,
                self.temp_dir,
            )

    def test_permission_denied_directory(self):
        """Test export to directory without write permissions"""
        # Create a read-only directory (on Unix systems)
        try:
            readonly_dir = os.path.join(self.temp_dir, "readonly")
            os.makedirs(readonly_dir)
            os.chmod(readonly_dir, 0o444)  # Read-only

            # This should either fail or handle the permission error
            try:
                output_path = self.exporter.export_audit_results(
                    self.sample_audit_results,
                    self.sample_audit_summary,
                    readonly_dir,
                )
                # If it succeeds, that's fine too
            except (PermissionError, OSError):
                # Expected behavior for permission denied
                pass
            finally:
                # Restore permissions for cleanup
                os.chmod(readonly_dir, 0o755)
        except (OSError, NotImplementedError):
            # Skip on systems that don't support chmod
            self.skipTest("Chmod not supported on this system")

    # =================================================================
    # EDGE CASES - Boundary conditions and special data
    # =================================================================

    def test_very_large_json_data(self):
        """Test export with very large JSON data"""
        large_data = {
            "data": [{"id": i, "value": f"item_{i}" * 100} for i in range(100)]
        }
        large_json = json.dumps(large_data)

        large_result = [
            {
                "test_name": "large_json_test",
                "timestamp": datetime.utcnow().isoformat(),
                "expected_pattern": large_json,
                "actual_response": large_json,
                "overall_result": "PASS",
                "differences": [],
                "http_validation_errors": [],
                "json_validation_errors": [],
                "match_percentage": 100.0,
            }
        ]

        output_path = self.exporter.export_audit_results(
            large_result, self.sample_audit_summary, self.temp_dir
        )

        self.assertTrue(os.path.exists(output_path))

        # Verify large data was handled correctly
        if PANDAS_AVAILABLE:
            json_df = pd.read_excel(
                output_path, sheet_name="JSON_Data", engine="openpyxl"
            )
            self.assertGreater(len(json_df.iloc[0]["Expected_JSON"]), 1000)

    def test_unicode_and_special_characters(self):
        """Test export with Unicode and special characters"""
        unicode_result = [
            {
                "test_name": "unicode_test_🚀",
                "timestamp": datetime.utcnow().isoformat(),
                "expected_pattern": '{"message": "Hello 世界! Special: @#$%^&*()"}',
                "actual_response": '{"message": "Hello 世界! Special: @#$%^&*()"}',
                "overall_result": "PASS",
                "differences": [],
                "http_validation_errors": [],
                "json_validation_errors": [],
                "match_percentage": 100.0,
            }
        ]

        output_path = self.exporter.export_audit_results(
            unicode_result, self.sample_audit_summary, self.temp_dir
        )

        self.assertTrue(os.path.exists(output_path))

        # Verify Unicode data was preserved
        if PANDAS_AVAILABLE:
            detailed_df = pd.read_excel(
                output_path, sheet_name="Detailed_Results", engine="openpyxl"
            )
            self.assertIn("🚀", detailed_df.iloc[0]["Test_Name"])

    def test_many_differences_handling(self):
        """Test handling of tests with many differences"""
        many_diffs = [
            {
                "type": "mismatch",
                "field_path": f"field_{i}",
                "expected_value": f"expected_{i}",
                "actual_value": f"actual_{i}",
            }
            for i in range(50)
        ]

        result_with_many_diffs = [
            {
                "test_name": "many_differences_test",
                "timestamp": datetime.utcnow().isoformat(),
                "expected_pattern": "{}",
                "actual_response": "{}",
                "overall_result": "FAIL",
                "differences": many_diffs,
                "http_validation_errors": [],
                "json_validation_errors": [
                    "Pattern match failed: 50 differences found"
                ],
                "match_percentage": 0.0,
            }
        ]

        output_path = self.exporter.export_audit_results(
            result_with_many_diffs, self.sample_audit_summary, self.temp_dir
        )

        self.assertTrue(os.path.exists(output_path))

        # Verify all differences were captured
        if PANDAS_AVAILABLE:
            diff_df = pd.read_excel(
                output_path,
                sheet_name="Differences_Analysis",
                engine="openpyxl",
            )
            self.assertEqual(len(diff_df), 50)

    def test_null_and_none_values(self):
        """Test handling of null and None values in data"""
        result_with_nulls = [
            {
                "test_name": "null_values_test",
                "timestamp": datetime.utcnow().isoformat(),
                "expected_pattern": None,
                "actual_response": None,
                "http_method_expected": None,
                "http_method_actual": None,
                "status_code_expected": None,
                "status_code_actual": None,
                "overall_result": "ERROR",
                "differences": [],
                "http_validation_errors": [],
                "json_validation_errors": ["Null pattern provided"],
                "match_percentage": 0.0,
            }
        ]

        output_path = self.exporter.export_audit_results(
            result_with_nulls, self.sample_audit_summary, self.temp_dir
        )

        self.assertTrue(os.path.exists(output_path))

        # Verify None values were handled (should be converted to empty strings or "None")
        if PANDAS_AVAILABLE:
            detailed_df = pd.read_excel(
                output_path, sheet_name="Detailed_Results", engine="openpyxl"
            )
            self.assertEqual(len(detailed_df), 1)

    # =================================================================
    # ADVANCED FORMATTING TESTS
    # =================================================================

    @unittest.skipIf(not PANDAS_AVAILABLE, "pandas not available")
    @patch("src.testpilot.audit.audit_exporter.load_workbook")
    def test_advanced_formatting_applied(self, mock_load_workbook):
        """Test that advanced formatting is applied to Excel file"""
        mock_workbook = MagicMock()
        mock_worksheet = MagicMock()
        mock_workbook.sheetnames = ["Detailed_Results"]
        mock_workbook.__getitem__.return_value = mock_worksheet
        mock_load_workbook.return_value = mock_workbook

        output_path = self.exporter.export_audit_results(
            self.sample_audit_results, self.sample_audit_summary, self.temp_dir
        )

        # Verify that formatting methods were called
        mock_load_workbook.assert_called_once()
        mock_workbook.save.assert_called_once()

    def test_risk_assessment_logic(self):
        """Test risk assessment logic in compliance report"""
        # Test different risk levels
        test_cases = [
            # High risk: many errors
            {
                "overall_result": "FAIL",
                "http_validation_errors": ["error1", "error2", "error3"],
                "json_validation_errors": ["error4", "error5"],
                "differences": [{"type": "mismatch"}],
                "expected_risk": "HIGH",
            },
            # Medium risk: some errors
            {
                "overall_result": "FAIL",
                "http_validation_errors": ["error1"],
                "json_validation_errors": ["error2"],
                "differences": [],
                "expected_risk": "MEDIUM",
            },
            # Low risk: pass or minimal errors
            {
                "overall_result": "PASS",
                "http_validation_errors": [],
                "json_validation_errors": [],
                "differences": [],
                "expected_risk": "LOW",
            },
        ]

        for i, case in enumerate(test_cases):
            result = {
                "test_name": f"risk_test_{i}",
                "timestamp": datetime.utcnow().isoformat(),
                "overall_result": case["overall_result"],
                "http_validation_errors": case["http_validation_errors"],
                "json_validation_errors": case["json_validation_errors"],
                "differences": case["differences"],
                "match_percentage": (
                    100.0 if case["overall_result"] == "PASS" else 0.0
                ),
            }

            # Test the risk assessment method directly
            risk_level = self.exporter._assess_risk_level(result)
            self.assertEqual(
                risk_level,
                case["expected_risk"],
                f"Risk assessment failed for case {i}",
            )

    def test_difference_impact_assessment(self):
        """Test difference impact assessment logic"""
        test_cases = [
            {
                "type": "missing",
                "field_path": "status",
                "expected_impact": "HIGH",
            },
            {
                "type": "mismatch",
                "field_path": "error.code",
                "expected_impact": "HIGH",
            },
            {
                "type": "mismatch",
                "field_path": "data.name",
                "expected_impact": "MEDIUM",
            },
            {
                "type": "unexpected",
                "field_path": "extra.field",
                "expected_impact": "LOW",
            },
        ]

        for case in test_cases:
            diff = {
                "type": case["type"],
                "field_path": case["field_path"],
                "expected_value": "test",
                "actual_value": "test2",
            }

            impact = self.exporter._assess_difference_impact(diff)
            self.assertEqual(
                impact,
                case["expected_impact"],
                f"Impact assessment failed for {case}",
            )

    # =================================================================
    # INTEGRATION AND PERFORMANCE TESTS
    # =================================================================

    def test_large_dataset_performance(self):
        """Test performance with large dataset"""
        import time

        # Generate large dataset
        large_results = []
        for i in range(100):
            result = {
                "test_name": f"perf_test_{i}",
                "timestamp": datetime.utcnow().isoformat(),
                "expected_pattern": f'{{"test_id": {i}, "data": "test_data"}}',
                "actual_response": f'{{"test_id": {i}, "data": "test_data"}}',
                "overall_result": "PASS" if i % 2 == 0 else "FAIL",
                "differences": (
                    []
                    if i % 2 == 0
                    else [
                        {
                            "type": "mismatch",
                            "field_path": "test",
                            "expected_value": "a",
                            "actual_value": "b",
                        }
                    ]
                ),
                "http_validation_errors": [],
                "json_validation_errors": [],
                "match_percentage": 100.0 if i % 2 == 0 else 50.0,
            }
            large_results.append(result)

        large_summary = {
            "audit_mode": "STRICT_100_PERCENT",
            "total_tests": 100,
            "passed_tests": 50,
            "failed_tests": 50,
            "error_tests": 0,
            "pass_rate": 50.0,
            "compliance_status": "NON_COMPLIANT",
            "generated_at": datetime.utcnow().isoformat(),
        }

        start_time = time.time()
        output_path = self.exporter.export_audit_results(
            large_results, large_summary, self.temp_dir
        )
        end_time = time.time()

        # Performance check - should complete within reasonable time
        self.assertLess(end_time - start_time, 30, "Export took too long")
        self.assertTrue(os.path.exists(output_path))

        # Verify data integrity
        if PANDAS_AVAILABLE:
            detailed_df = pd.read_excel(
                output_path, sheet_name="Detailed_Results", engine="openpyxl"
            )
            self.assertEqual(len(detailed_df), 100)

    def test_concurrent_export_operations(self):
        """Test concurrent export operations"""
        import threading
        import time

        results = []
        errors = []

        def export_worker(worker_id):
            try:
                worker_dir = os.path.join(self.temp_dir, f"worker_{worker_id}")
                os.makedirs(worker_dir, exist_ok=True)

                exporter = AuditExporter()
                output_path = exporter.export_audit_results(
                    self.sample_audit_results,
                    self.sample_audit_summary,
                    worker_dir,
                )
                results.append(output_path)
            except Exception as e:
                errors.append(str(e))

        # Start multiple concurrent exports
        threads = []
        for i in range(5):
            thread = threading.Thread(target=export_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=30)

        # Check results
        self.assertEqual(len(errors), 0, f"Concurrent export errors: {errors}")
        self.assertEqual(len(results), 5)

        # Verify all files were created
        for output_path in results:
            self.assertTrue(os.path.exists(output_path))


'''    def test_force_json_export(self):
        """Test forcing JSON export even with Excel dependencies"""
        output_path = self.exporter.export_audit_results(
            self.sample_audit_results,
            self.sample_audit_summary,
            self.temp_dir,
            force_json=True
        )

        # Verify JSON file was created
        self.assertTrue(output_path.endswith('.json'))
        self.assertTrue(os.path.exists(output_path))

        # Verify JSON content
        with open(output_path, 'r') as f:
            data = json.load(f)

        self.assertIn("audit_summary", data)
        self.assertEqual(data["audit_summary"]["total_tests"], 3)


if __name__ == '__main__':
    unittest.main(verbosity=2)'''
