#!/usr/bin/env python3
"""
Test Fixtures and Mock Data for Audit Tests

Provides comprehensive test data, fixtures, and utilities for audit testing:
- Sample JSON patterns and responses
- Mock Excel data
- Test result generators
- Utility functions for test setup
- Performance testing data generators
"""

import json
import os
import tempfile
from datetime import datetime, timedelta
from typing import Any, Dict, List

try:
    import pandas as pd

    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


class AuditTestFixtures:
    """Comprehensive test fixtures for audit testing"""

    # =================================================================
    # BASIC JSON PATTERNS
    # =================================================================

    SIMPLE_SUCCESS_PATTERN = (
        '{"status": "success", "message": "Operation completed"}'
    )
    SIMPLE_SUCCESS_RESPONSE = (
        '{"status": "success", "message": "Operation completed"}'
    )

    SIMPLE_ERROR_PATTERN = (
        '{"status": "error", "code": 400, "message": "Bad request"}'
    )
    SIMPLE_ERROR_RESPONSE = (
        '{"status": "error", "code": 400, "message": "Bad request"}'
    )

    NESTED_DATA_PATTERN = """
    {
        "user": {
            "id": 123,
            "name": "John Doe",
            "email": "john@example.com",
            "active": true
        },
        "metadata": {
            "created": "2025-01-01T00:00:00Z",
            "updated": "2025-01-01T12:00:00Z"
        }
    }
    """

    ARRAY_DATA_PATTERN = """
    {
        "users": [
            {"id": 1, "name": "Alice", "role": "admin"},
            {"id": 2, "name": "Bob", "role": "user"},
            {"id": 3, "name": "Charlie", "role": "user"}
        ],
        "total": 3,
        "page": 1
    }
    """

    COMPLEX_NESTED_PATTERN = """
    {
        "api_response": {
            "status": "success",
            "data": {
                "users": [
                    {
                        "id": 1,
                        "profile": {
                            "name": "Alice Johnson",
                            "contact": {
                                "email": "alice@example.com",
                                "phone": "+1-555-0101"
                            },
                            "preferences": {
                                "notifications": {
                                    "email": true,
                                    "sms": false,
                                    "push": true
                                },
                                "privacy": {
                                    "profile_visible": true,
                                    "activity_tracking": false
                                }
                            }
                        },
                        "permissions": ["read", "write", "admin"]
                    }
                ],
                "pagination": {
                    "current_page": 1,
                    "total_pages": 5,
                    "per_page": 20,
                    "total_items": 100
                }
            },
            "meta": {
                "request_id": "req_12345",
                "timestamp": "2025-01-01T12:00:00.000Z",
                "version": "1.2.3"
            }
        }
    }
    """

    # =================================================================
    # MALFORMED JSON PATTERNS
    # =================================================================

    MALFORMED_JSON_CASES = [
        '{"incomplete": ',
        '{"trailing_comma": "value",}',
        '{"duplicate": 1, "duplicate": 2}',
        '{unquoted_key: "value"}',
        "{'single_quotes': 'not_valid'}",
        '{"invalid_escape": "\\z"}',
        '{"numbers": [01, 02, 03]}',
        '{"special": Infinity}',
        "",
        "null",
        "not_json_at_all",
    ]

    # =================================================================
    # HTTP RESPONSE PATTERNS
    # =================================================================

    @staticmethod
    def get_http_response_with_status(
        status_code: int, body: str = None
    ) -> str:
        """Generate HTTP response with specific status code"""
        status_messages = {
            200: "OK",
            201: "Created",
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            500: "Internal Server Error",
            502: "Bad Gateway",
            503: "Service Unavailable",
        }

        status_message = status_messages.get(status_code, "Unknown")
        body = (
            body
            or f'{{"status": {status_code}, "message": "{status_message}"}}'
        )

        return f"""HTTP/1.1 {status_code} {status_message}
Content-Type: application/json
Content-Length: {len(body)}

{body}"""

    # =================================================================
    # CURL COMMAND PATTERNS
    # =================================================================

    CURL_COMMANDS = {
        "simple_get": "curl -X GET http://api.example.com/users",
        "post_with_data": "curl -X POST http://api.example.com/users -H 'Content-Type: application/json' -d '{\"name\":\"John\"}'",
        "put_with_auth": "curl -X PUT http://api.example.com/users/123 -H 'Authorization: Bearer token123' -d '{\"name\":\"Updated\"}'",
        "delete_simple": "curl -X DELETE http://api.example.com/users/123",
        "patch_with_headers": "curl -X PATCH http://api.example.com/users/123 -H 'Content-Type: application/json' -H 'X-Request-ID: req123'",
        "complex_curl": "curl -X POST 'http://api.example.com/complex' -H 'Content-Type: application/json' -H 'Accept: application/json' -H 'User-Agent: TestPilot/1.0' --data-raw '{\"complex\":\"data\"}' --compressed --max-time 30",
    }

    # =================================================================
    # AUDIT RESULT GENERATORS
    # =================================================================

    @staticmethod
    def generate_audit_result(
        test_name: str,
        result_type: str = "PASS",
        pattern: str = None,
        response: str = None,
        http_method_expected: str = "GET",
        http_method_actual: str = "GET",
        status_expected: int = 200,
        status_actual: int = 200,
        differences: List[Dict] = None,
        http_errors: List[str] = None,
        json_errors: List[str] = None,
    ) -> Dict[str, Any]:
        """Generate a single audit result with specified parameters"""

        pattern = pattern or AuditTestFixtures.SIMPLE_SUCCESS_PATTERN
        response = response or AuditTestFixtures.SIMPLE_SUCCESS_RESPONSE
        differences = differences or []
        http_errors = http_errors or []
        json_errors = json_errors or []

        if (
            result_type == "FAIL"
            and not differences
            and not http_errors
            and not json_errors
        ):
            # Auto-generate some failures for FAIL type
            if http_method_expected != http_method_actual:
                http_errors.append(
                    f"HTTP method mismatch: expected '{http_method_expected}', got '{http_method_actual}'"
                )
            if status_expected != status_actual:
                http_errors.append(
                    f"Status code mismatch: expected {status_expected}, got {status_actual}"
                )
            if pattern != response:
                json_errors.append("Pattern match failed: 1 differences found")
                differences.append(
                    {
                        "type": "mismatch",
                        "field_path": "auto_generated_diff",
                        "expected_value": "expected",
                        "actual_value": "actual",
                    }
                )

        return {
            "test_name": test_name,
            "timestamp": datetime.utcnow().isoformat(),
            "validation_type": "STRICT_100_PERCENT",
            "expected_pattern": pattern,
            "actual_response": response,
            "http_method_expected": http_method_expected,
            "http_method_actual": http_method_actual,
            "status_code_expected": status_expected,
            "status_code_actual": status_actual,
            "request_details": {
                "command": f"curl -X {http_method_expected} http://api.example.com/test",
                "host": "test-host",
                "execution_time": 0.123,
            },
            "differences": differences,
            "http_validation_errors": http_errors,
            "json_validation_errors": json_errors,
            "overall_result": result_type,
            "match_percentage": (
                100.0
                if result_type == "PASS"
                else 0.0 if result_type == "FAIL" else 0.0
            ),
        }

    @staticmethod
    def generate_audit_results_batch(
        num_pass: int = 10, num_fail: int = 5, num_error: int = 2
    ) -> List[Dict[str, Any]]:
        """Generate a batch of audit results with specified distribution"""
        results = []

        # Generate PASS results
        for i in range(num_pass):
            results.append(
                AuditTestFixtures.generate_audit_result(
                    test_name=f"pass_test_{i+1}", result_type="PASS"
                )
            )

        # Generate FAIL results
        for i in range(num_fail):
            results.append(
                AuditTestFixtures.generate_audit_result(
                    test_name=f"fail_test_{i+1}",
                    result_type="FAIL",
                    pattern='{"status": "success"}',
                    response='{"status": "error"}',
                    http_method_expected="GET",
                    http_method_actual="POST",
                    status_expected=200,
                    status_actual=400,
                )
            )

        # Generate ERROR results
        for i in range(num_error):
            results.append(
                AuditTestFixtures.generate_audit_result(
                    test_name=f"error_test_{i+1}",
                    result_type="ERROR",
                    pattern='{"status": "success"}',
                    response="",
                    json_errors=[
                        "Invalid JSON structure: Expecting value: line 1 column 1 (char 0)"
                    ],
                )
            )

        return results

    @staticmethod
    def generate_audit_summary(
        total_tests: int,
        passed_tests: int,
        failed_tests: int,
        error_tests: int,
    ) -> Dict[str, Any]:
        """Generate audit summary with specified counts"""
        pass_rate = (
            (passed_tests / total_tests * 100) if total_tests > 0 else 0
        )
        compliance_status = (
            "COMPLIANT"
            if failed_tests == 0 and error_tests == 0
            else "NON_COMPLIANT"
        )

        return {
            "audit_mode": "STRICT_100_PERCENT",
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "error_tests": error_tests,
            "pass_rate": pass_rate,
            "compliance_status": compliance_status,
            "generated_at": datetime.utcnow().isoformat(),
        }

    # =================================================================
    # EXCEL DATA GENERATORS
    # =================================================================

    @staticmethod
    def create_test_excel_data(num_tests: int = 5) -> pd.DataFrame:
        """Create test Excel data with specified number of tests"""
        test_data = {
            "Test_Name": [f"test_case_{i+1}" for i in range(num_tests)],
            "Pod_Exec": [f"test-pod-{i+1}" for i in range(num_tests)],
            "Command": [
                f"curl -X GET http://api.example.com/endpoint/{i+1}"
                for i in range(num_tests)
            ],
            "Expected_Status": [200] * num_tests,
            "Pattern_Match": [
                json.dumps(
                    {
                        "test_id": i + 1,
                        "status": "success",
                        "data": f"test_data_{i+1}",
                    }
                )
                for i in range(num_tests)
            ],
        }

        return pd.DataFrame(test_data)

    @staticmethod
    def create_test_excel_file(filepath: str, num_tests: int = 5) -> str:
        """Create a test Excel file with specified data"""
        df = AuditTestFixtures.create_test_excel_data(num_tests)
        df.to_excel(filepath, index=False, engine="openpyxl")
        return filepath

    @staticmethod
    def create_complex_excel_data() -> pd.DataFrame:
        """Create complex Excel data with various test scenarios"""
        test_data = {
            "Test_Name": [
                "user_registration",
                "user_authentication",
                "data_validation",
                "error_handling",
                "performance_test",
            ],
            "Pod_Exec": [
                "api-service-pod",
                "auth-service-pod",
                "validator-pod",
                "error-handler-pod",
                "performance-pod",
            ],
            "Command": [
                'curl -X POST http://api.service/users -d \'{"name":"test_user","email":"test@example.com"}\'',
                'curl -X POST http://auth.service/login -d \'{"username":"test_user","password":"test123"}\'',
                "curl -X GET http://validator.service/validate/data?id=12345",
                "curl -X GET http://api.service/invalid-endpoint",
                "curl -X GET http://api.service/performance-test --max-time 1",
            ],
            "Expected_Status": [201, 200, 200, 404, 200],
            "Pattern_Match": [
                '{"status": "created", "user": {"id": 12345, "name": "test_user", "email": "test@example.com"}}',
                '{"status": "success", "token": "jwt_token_here", "expires_in": 3600}',
                '{"status": "valid", "data": {"score": 95, "issues": []}}',
                '{"status": "error", "code": 404, "message": "Endpoint not found"}',
                '{"status": "success", "response_time_ms": 250, "data": {"performance": "good"}}',
            ],
        }

        return pd.DataFrame(test_data)

    # =================================================================
    # PERFORMANCE TEST DATA
    # =================================================================

    @staticmethod
    def generate_large_json_pattern(size_kb: int = 100) -> str:
        """Generate large JSON pattern for performance testing"""
        # Calculate approximate number of items needed for target size
        items_needed = (size_kb * 1024) // 100  # Rough estimate

        large_data = {
            "metadata": {
                "size_target_kb": size_kb,
                "generated_at": datetime.utcnow().isoformat(),
                "items_count": items_needed,
            },
            "data": [
                {
                    "id": i,
                    "name": f"item_{i}",
                    "description": f"This is a test item number {i} with some additional text to increase size",
                    "properties": {
                        "active": i % 2 == 0,
                        "priority": i % 5,
                        "tags": [f"tag_{j}" for j in range(i % 10)],
                        "metadata": {
                            "created": datetime.utcnow().isoformat(),
                            "version": "1.0.0",
                        },
                    },
                }
                for i in range(items_needed)
            ],
        }

        return json.dumps(large_data)

    @staticmethod
    def generate_performance_test_batch(
        num_tests: int = 100, json_size_kb: int = 10
    ) -> List[Dict[str, Any]]:
        """Generate batch of test data for performance testing"""
        base_pattern = json.loads(
            AuditTestFixtures.generate_large_json_pattern(json_size_kb)
        )
        results = []

        for i in range(num_tests):
            # Modify pattern slightly for each test
            pattern_copy = base_pattern.copy()
            pattern_copy["test_id"] = i
            pattern_copy["metadata"]["test_sequence"] = i

            result = AuditTestFixtures.generate_audit_result(
                test_name=f"performance_test_{i+1}",
                result_type="PASS" if i % 10 != 0 else "FAIL",  # 90% pass rate
                pattern=json.dumps(pattern_copy),
                response=(
                    json.dumps(pattern_copy)
                    if i % 10 != 0
                    else '{"status": "error"}'
                ),
            )

            results.append(result)

        return results

    # =================================================================
    # EDGE CASE DATA
    # =================================================================

    @staticmethod
    def get_unicode_test_data() -> Dict[str, str]:
        """Get test data with various Unicode characters"""
        return {
            "basic_unicode": '{"message": "Hello 世界! 🌍"}',
            "emoji_heavy": '{"status": "🟢", "result": "✅", "data": {"🚀": "rocket", "💻": "computer"}}',
            "special_chars": '{"text": "Special chars: àáâãäåæçèéêë ñòóôõö ùúûüý"}',
            "mathematical": '{"formula": "∑(i=1 to n) i² = n(n+1)(2n+1)/6", "symbols": "∀∃∈∉∩∪⊂⊆"}',
            "mixed_scripts": '{"english": "hello", "chinese": "你好", "arabic": "مرحبا", "russian": "привет"}',
            "control_chars": '{"data": "Line1\\nLine2\\tTabbed\\rCarriageReturn"}',
            "high_unicode": '{"high_plane": "𝓗𝓮𝓵𝓵𝓸 𝓦𝓸𝓻𝓵𝓭!", "music": "𝄞𝄢𝄡𝄟"}',
        }

    @staticmethod
    def get_boundary_test_data() -> Dict[str, Any]:
        """Get test data for boundary conditions"""
        return {
            "empty_json": {},
            "single_field": {"a": "b"},
            "very_long_string": {"data": "x" * 10000},
            "deep_nesting": {
                "level0": {
                    "level1": {"level2": {"level3": {"level4": "deep"}}}
                }
            },
            "large_array": {"items": list(range(1000))},
            "mixed_types": {
                "null": None,
                "bool_true": True,
                "bool_false": False,
                "int_zero": 0,
                "int_negative": -123,
                "int_large": 2147483647,
                "float_zero": 0.0,
                "float_small": 1e-10,
                "float_large": 1e10,
                "string_empty": "",
                "array_empty": [],
                "object_empty": {},
            },
        }

    # =================================================================
    # UTILITY METHODS
    # =================================================================

    @staticmethod
    def create_temp_excel_file(data: pd.DataFrame = None) -> str:
        """Create a temporary Excel file for testing"""
        if data is None:
            data = AuditTestFixtures.create_test_excel_data()

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        temp_file.close()

        data.to_excel(temp_file.name, index=False, engine="openpyxl")
        return temp_file.name

    @staticmethod
    def cleanup_temp_file(filepath: str):
        """Clean up temporary test file"""
        try:
            os.unlink(filepath)
        except (OSError, FileNotFoundError):
            pass

    @staticmethod
    def validate_audit_result_structure(result: Dict[str, Any]) -> bool:
        """Validate that an audit result has the expected structure"""
        required_fields = [
            "test_name",
            "timestamp",
            "validation_type",
            "expected_pattern",
            "actual_response",
            "overall_result",
            "differences",
            "http_validation_errors",
            "json_validation_errors",
        ]

        return all(field in result for field in required_fields)

    @staticmethod
    def get_sample_test_scenarios() -> Dict[str, Dict[str, Any]]:
        """Get predefined test scenarios for various use cases"""
        return {
            "perfect_match": {
                "description": "Perfect JSON match with all parameters matching",
                "expected_pattern": '{"status": "success", "data": {"id": 123}}',
                "actual_response": '{"status": "success", "data": {"id": 123}}',
                "http_method_expected": "GET",
                "http_method_actual": "GET",
                "status_code_expected": 200,
                "status_code_actual": 200,
                "expected_result": "PASS",
            },
            "json_mismatch": {
                "description": "JSON content mismatch",
                "expected_pattern": '{"status": "success", "data": {"id": 123}}',
                "actual_response": '{"status": "error", "data": {"id": 456}}',
                "http_method_expected": "GET",
                "http_method_actual": "GET",
                "status_code_expected": 200,
                "status_code_actual": 200,
                "expected_result": "FAIL",
            },
            "http_method_mismatch": {
                "description": "HTTP method mismatch",
                "expected_pattern": '{"status": "success"}',
                "actual_response": '{"status": "success"}',
                "http_method_expected": "GET",
                "http_method_actual": "POST",
                "status_code_expected": 200,
                "status_code_actual": 200,
                "expected_result": "FAIL",
            },
            "status_code_mismatch": {
                "description": "HTTP status code mismatch",
                "expected_pattern": '{"status": "success"}',
                "actual_response": '{"status": "success"}',
                "http_method_expected": "GET",
                "http_method_actual": "GET",
                "status_code_expected": 200,
                "status_code_actual": 404,
                "expected_result": "FAIL",
            },
            "invalid_json": {
                "description": "Invalid JSON response",
                "expected_pattern": '{"status": "success"}',
                "actual_response": '{"invalid": json}',
                "http_method_expected": "GET",
                "http_method_actual": "GET",
                "status_code_expected": 200,
                "status_code_actual": 200,
                "expected_result": "FAIL",
            },
            "empty_response": {
                "description": "Empty response handling",
                "expected_pattern": '{"status": "success"}',
                "actual_response": "",
                "http_method_expected": "GET",
                "http_method_actual": "GET",
                "status_code_expected": 200,
                "status_code_actual": 200,
                "expected_result": "FAIL",
            },
        }


# Create a global instance for easy access
fixtures = AuditTestFixtures()


if __name__ == "__main__":
    # Example usage and testing
    print("=== Audit Test Fixtures Demo ===")

    # Generate sample audit results
    results = fixtures.generate_audit_results_batch(3, 2, 1)
    print(f"Generated {len(results)} audit results")

    # Generate summary
    summary = fixtures.generate_audit_summary(6, 3, 2, 1)
    print(f"Summary: {summary['pass_rate']}% pass rate")

    # Create sample Excel data
    excel_data = fixtures.create_test_excel_data(3)
    print(f"Created Excel data with {len(excel_data)} rows")

    # Show test scenarios
    scenarios = fixtures.get_sample_test_scenarios()
    print(f"Available test scenarios: {list(scenarios.keys())}")

    print("✅ Fixtures working correctly!")
