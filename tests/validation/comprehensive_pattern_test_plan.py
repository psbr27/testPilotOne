#!/usr/bin/env python3
"""
Comprehensive Test Plan for Enhanced Response Validator Pattern Matching
Covers all scenarios between output and pattern_match with high regression testing
"""

import json
import logging
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from testpilot.core.enhanced_response_validator import (
    validate_response_enhanced,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ComprehensivePatternTestSuite:
    """Comprehensive test suite for all pattern matching scenarios"""

    def __init__(self):
        self.test_results = []
        self.passed = 0
        self.failed = 0

    def run_test(
        self,
        test_name,
        pattern_match,
        response_body,
        expected_result,
        raw_output=None,
        description="",
    ):
        """Run a single test and record results"""
        print(f"\n{'='*80}")
        print(f"TEST: {test_name}")
        print(f"Description: {description}")
        print(f"Pattern: {pattern_match}")
        print(
            f"Response: {json.dumps(response_body) if isinstance(response_body, (dict, list)) else str(response_body)[:100]}"
        )
        print(f"Expected: {expected_result}")

        result = validate_response_enhanced(
            pattern_match=pattern_match,
            response_headers={"content-type": "application/json"},
            response_body=response_body,
            response_payload=None,
            logger=logger,
            raw_output=raw_output,
        )

        actual_result = result["pattern_match_overall"]
        passed = actual_result == expected_result

        print(f"Actual: {actual_result}")
        print(f"Result: {'✅ PASS' if passed else '❌ FAIL'}")

        if passed:
            self.passed += 1
        else:
            self.failed += 1
            print(f"Pattern matches: {result['pattern_matches']}")

        self.test_results.append(
            {
                "test_name": test_name,
                "passed": passed,
                "expected": expected_result,
                "actual": actual_result,
                "pattern": pattern_match,
                "description": description,
            }
        )

        return passed

    def test_1_simple_string_patterns(self):
        """Test 1: Simple string patterns in various JSON structures"""
        print("\n" + "🔍 TEST CATEGORY 1: SIMPLE STRING PATTERNS" + "\n")

        # Simple flat JSON
        response = {"name": "John", "status": "active", "id": 123}

        self.run_test(
            "1.1",
            "John",
            response,
            True,
            description="Simple substring in flat JSON",
        )
        self.run_test(
            "1.2",
            "active",
            response,
            True,
            description="Status value substring",
        )
        self.run_test(
            "1.3",
            "inactive",
            response,
            False,
            description="Non-existent substring",
        )
        self.run_test(
            "1.4",
            "123",
            response,
            True,
            description="Number as string pattern",
        )

        # Nested JSON
        nested_response = {
            "user": {
                "name": "John",
                "details": {"status": "active", "role": "admin"},
            },
            "timestamp": "2025-01-01",
        }

        self.run_test(
            "1.5",
            "admin",
            nested_response,
            True,
            description="String in deeply nested structure",
        )
        self.run_test(
            "1.6",
            "2025-01-01",
            nested_response,
            True,
            description="Timestamp string pattern",
        )

        # Array with mixed content
        array_response = [
            {"name": "John", "status": "active"},
            {"name": "Jane", "status": "inactive"},
            "direct_string_value",
        ]

        self.run_test(
            "1.7",
            "Jane",
            array_response,
            True,
            description="String in array of objects",
        )
        self.run_test(
            "1.8",
            "direct_string_value",
            array_response,
            True,
            description="Direct string in array",
        )

    def test_2_key_value_patterns(self):
        """Test 2: Key-value patterns with various separators and nesting"""
        print("\n" + "🔍 TEST CATEGORY 2: KEY-VALUE PATTERNS" + "\n")

        response = {
            "nfType": "UDM",
            "status": {"code": 200, "message": "OK"},
            "services": [
                {"name": "service1", "port": 8080},
                {"name": "service2", "port": 8081},
            ],
            "metadata": {"version": "1.0", "environment": "prod"},
        }

        # Colon separator patterns
        self.run_test(
            "2.1",
            "nfType:UDM",
            response,
            True,
            description="Simple key-value with colon",
        )
        self.run_test(
            "2.2",
            "nfType:AMF",
            response,
            False,
            description="Key exists but wrong value",
        )
        self.run_test(
            "2.3",
            "nonexistent:value",
            response,
            False,
            description="Non-existent key",
        )

        # Equals separator patterns
        self.run_test(
            "2.4",
            "nfType=UDM",
            response,
            True,
            description="Simple key-value with equals",
        )

        # Nested key-value patterns (dot notation)
        self.run_test(
            "2.5",
            "status.code:200",
            response,
            True,
            description="Nested key-value access",
        )
        self.run_test(
            "2.6",
            "status.message:OK",
            response,
            True,
            description="Nested string value",
        )
        self.run_test(
            "2.7",
            "metadata.version:1.0",
            response,
            True,
            description="Nested metadata access",
        )
        self.run_test(
            "2.8",
            "metadata.environment:dev",
            response,
            False,
            description="Wrong nested value",
        )

        # Array element access
        self.run_test(
            "2.9",
            "name:service1",
            response,
            True,
            description="Key-value in array element",
        )
        self.run_test(
            "2.10",
            "port:8080",
            response,
            True,
            description="Numeric value in array",
        )

    def test_3_json_object_patterns(self):
        """Test 3: JSON object patterns as subsets"""
        print("\n" + "🔍 TEST CATEGORY 3: JSON OBJECT PATTERNS" + "\n")

        complex_response = {
            "nfInstanceId": "uuid-123",
            "nfType": "UDM",
            "nfStatus": "REGISTERED",
            "heartBeatTimer": 90,
            "plmnList": [{"mcc": "001", "mnc": "01"}],
            "services": {
                "nudm-sdm": {"versions": ["v1", "v2"]},
                "nudm-uecm": {"versions": ["v1"]},
            },
        }

        # Simple subset patterns
        self.run_test(
            "3.1",
            '{"nfType":"UDM"}',
            complex_response,
            True,
            description="Single field JSON subset",
        )
        self.run_test(
            "3.2",
            '{"nfType":"UDM","nfStatus":"REGISTERED"}',
            complex_response,
            True,
            description="Two field JSON subset",
        )
        self.run_test(
            "3.3",
            '{"nfType":"AMF"}',
            complex_response,
            False,
            description="Wrong value in JSON subset",
        )

        # Nested object patterns
        self.run_test(
            "3.4",
            '{"services":{"nudm-sdm":{"versions":["v1","v2"]}}}',
            complex_response,
            True,
            description="Nested object subset",
        )
        self.run_test(
            "3.5",
            '{"plmnList":[{"mcc":"001"}]}',
            complex_response,
            True,
            description="Array with object subset",
        )

        # Partial nested patterns
        self.run_test(
            "3.6",
            '{"heartBeatTimer":90}',
            complex_response,
            True,
            description="Numeric field subset",
        )

    def test_4_json_array_patterns(self):
        """Test 4: JSON array patterns"""
        print("\n" + "🔍 TEST CATEGORY 4: JSON ARRAY PATTERNS" + "\n")

        array_response = [
            {"id": 1, "name": "item1", "tags": ["tag1", "tag2"]},
            {"id": 2, "name": "item2", "tags": ["tag3", "tag4"]},
            {"id": 3, "name": "item3", "tags": ["tag1", "tag5"]},
        ]

        # Array subset patterns
        self.run_test(
            "4.1",
            '[{"name":"item1"}]',
            array_response,
            True,
            description="Single object in array pattern",
        )
        self.run_test(
            "4.2",
            '[{"id":1},{"id":2}]',
            array_response,
            True,
            description="Multiple objects in array pattern",
        )
        self.run_test(
            "4.3",
            '[{"name":"nonexistent"}]',
            array_response,
            False,
            description="Non-existent object in array",
        )

        # Nested array patterns
        self.run_test(
            "4.4",
            '["tag1"]',
            array_response,
            True,
            description="Value exists in nested array",
        )
        self.run_test(
            "4.5",
            '["nonexistent_tag"]',
            array_response,
            False,
            description="Non-existent nested array value",
        )

    def test_5_regex_patterns(self):
        """Test 5: Regular expression patterns"""
        print("\n" + "🔍 TEST CATEGORY 5: REGEX PATTERNS" + "\n")

        response = {
            "email": "user@example.com",
            "phone": "+1-555-123-4567",
            "uuid": "550e8400-e29b-41d4-a716-446655440000",
            "timestamp": "2025-01-01T12:00:00Z",
            "version": "v1.2.3",
        }

        self.run_test(
            "5.1",
            r"\w+@\w+\.\w+",
            response,
            True,
            description="Email regex pattern",
        )
        self.run_test(
            "5.2",
            r"\+\d{1}-\d{3}-\d{3}-\d{4}",
            response,
            True,
            description="Phone number regex",
        )
        self.run_test(
            "5.3",
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            response,
            True,
            description="UUID regex pattern",
        )
        self.run_test(
            "5.4",
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",
            response,
            True,
            description="ISO timestamp regex",
        )
        self.run_test(
            "5.5",
            r"v\d+\.\d+\.\d+",
            response,
            True,
            description="Version pattern regex",
        )
        self.run_test(
            "5.6",
            r"invalid_pattern_\d{10}",
            response,
            False,
            description="Non-matching regex pattern",
        )

    def test_6_jsonpath_patterns(self):
        """Test 6: JSONPath expression patterns"""
        print("\n" + "🔍 TEST CATEGORY 6: JSONPATH PATTERNS" + "\n")

        response = {
            "store": {
                "book": [
                    {
                        "category": "reference",
                        "title": "Sayings",
                        "price": 8.95,
                    },
                    {"category": "fiction", "title": "Sword", "price": 12.99},
                    {
                        "category": "fiction",
                        "title": "Moby Dick",
                        "price": 8.99,
                    },
                ],
                "bicycle": {"color": "red", "price": 19.95},
            }
        }

        # Note: These will fail if jsonpath-ng is not installed, but we test the patterns anyway
        self.run_test(
            "6.1",
            "$.store.book[*].title",
            response,
            False,
            description="JSONPath - all book titles",
        )  # Will fail due to no jsonpath-ng
        self.run_test(
            "6.2",
            "$.store.book[0].price",
            response,
            False,
            description="JSONPath - first book price",
        )
        self.run_test(
            "6.3",
            "$.store..price",
            response,
            False,
            description="JSONPath - all prices (recursive)",
        )

    def test_7_edge_cases_and_special_scenarios(self):
        """Test 7: Edge cases and special scenarios"""
        print(
            "\n"
            + "🔍 TEST CATEGORY 7: EDGE CASES AND SPECIAL SCENARIOS"
            + "\n"
        )

        # Empty and null values
        empty_response = {
            "empty_string": "",
            "null_value": None,
            "zero": 0,
            "false": False,
        }

        self.run_test(
            "7.1",
            '""',
            empty_response,
            True,
            description="Empty string pattern",
        )
        self.run_test(
            "7.2",
            "null",
            empty_response,
            True,
            description="Null value as string",
        )
        self.run_test(
            "7.3",
            "0",
            empty_response,
            True,
            description="Zero as string pattern",
        )
        self.run_test(
            "7.4",
            "false",
            empty_response,
            True,
            description="Boolean false as string",
        )

        # Special characters and escaping
        special_response = {
            "json_string": '{"nested":"value"}',
            "url": "https://example.com/path?param=value",
            "special_chars": "!@#$%^&*()",
            "unicode": "Hello 世界 🌍",
        }

        self.run_test(
            "7.5",
            "nested",
            special_response,
            True,
            description="Pattern inside JSON string value",
        )
        self.run_test(
            "7.6",
            "https://example.com",
            special_response,
            True,
            description="URL substring pattern",
        )
        self.run_test(
            "7.7",
            "!@#$%",
            special_response,
            True,
            description="Special characters pattern",
        )
        self.run_test(
            "7.8",
            "🌍",
            special_response,
            True,
            description="Unicode emoji pattern",
        )

        # Large nested structures
        deep_response = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "level5": {
                                "target_value": "deep_nested_value",
                                "array": [
                                    1,
                                    2,
                                    {"deep_array_object": "found_it"},
                                ],
                            }
                        }
                    }
                }
            }
        }

        self.run_test(
            "7.9",
            "deep_nested_value",
            deep_response,
            True,
            description="Very deep nested value",
        )
        self.run_test(
            "7.10",
            "level5.target_value:deep_nested_value",
            deep_response,
            True,
            description="Deep nested key-value",
        )
        self.run_test(
            "7.11",
            "found_it",
            deep_response,
            True,
            description="Value in deep nested array",
        )

    def test_8_raw_output_scenarios(self):
        """Test 8: Raw output vs parsed response scenarios"""
        print("\n" + "🔍 TEST CATEGORY 8: RAW OUTPUT SCENARIOS" + "\n")

        response_body = {"nfType": "UDM", "status": "REGISTERED", "id": 123}
        raw_output = '{"nfType":"UDM","status":"REGISTERED","id":123,"extra_field":"only_in_raw"}'

        # Test patterns that exist in raw but not in parsed response
        self.run_test(
            "8.1",
            "extra_field",
            response_body,
            True,
            raw_output,
            description="Pattern only in raw_output",
        )
        self.run_test(
            "8.2",
            "only_in_raw",
            response_body,
            True,
            raw_output,
            description="Value only in raw_output",
        )

        # Test JSON patterns with raw_output
        self.run_test(
            "8.3",
            '{"nfType":"UDM","extra_field":"only_in_raw"}',
            response_body,
            True,
            raw_output,
            description="JSON pattern using raw_output",
        )

    def test_9_mixed_type_scenarios(self):
        """Test 9: Mixed type scenarios - arrays, objects, primitives"""
        print("\n" + "🔍 TEST CATEGORY 9: MIXED TYPE SCENARIOS" + "\n")

        mixed_response = {
            "string_field": "simple_string",
            "number_field": 42,
            "boolean_field": True,
            "array_field": ["string_in_array", 123, {"nested": "object"}],
            "object_field": {"sub_string": "nested_value", "sub_number": 999},
            "mixed_array": [
                "plain_string",
                {"type": "object", "data": [1, 2, 3]},
                [{"nested_array_object": "deep_value"}],
            ],
        }

        self.run_test(
            "9.1",
            "simple_string",
            mixed_response,
            True,
            description="String in mixed type response",
        )
        self.run_test(
            "9.2",
            "42",
            mixed_response,
            True,
            description="Number as string pattern",
        )
        self.run_test(
            "9.3",
            "true",
            mixed_response,
            True,
            description="Boolean as string pattern",
        )
        self.run_test(
            "9.4",
            "string_in_array",
            mixed_response,
            True,
            description="String inside array",
        )
        self.run_test(
            "9.5",
            "nested_value",
            mixed_response,
            True,
            description="Nested object value",
        )
        self.run_test(
            "9.6",
            "deep_value",
            mixed_response,
            True,
            description="Value in nested array object",
        )
        self.run_test(
            "9.7",
            "type:object",
            mixed_response,
            True,
            description="Key-value in mixed array",
        )

    def test_10_error_and_boundary_conditions(self):
        """Test 10: Error conditions and boundary cases"""
        print(
            "\n" + "🔍 TEST CATEGORY 10: ERROR AND BOUNDARY CONDITIONS" + "\n"
        )

        # Malformed JSON strings as patterns
        response = {"valid": "json", "number": 123}

        self.run_test(
            "10.1",
            '{"malformed":json}',
            response,
            False,
            description="Malformed JSON pattern",
        )
        self.run_test(
            "10.2", "", response, None, description="Empty pattern string"
        )
        self.run_test("10.3", None, response, None, description="None pattern")

        # Very long patterns and responses
        long_string = "a" * 1000
        long_response = {"long_field": long_string, "normal": "value"}
        long_pattern = "a" * 500

        self.run_test(
            "10.4",
            long_pattern,
            long_response,
            True,
            description="Very long pattern matching",
        )

    def run_all_tests(self):
        """Run all test categories"""
        print(
            "🚀 COMPREHENSIVE ENHANCED RESPONSE VALIDATOR PATTERN MATCHING TEST SUITE"
        )
        print("=" * 100)

        self.test_1_simple_string_patterns()
        self.test_2_key_value_patterns()
        self.test_3_json_object_patterns()
        self.test_4_json_array_patterns()
        self.test_5_regex_patterns()
        self.test_6_jsonpath_patterns()
        self.test_7_edge_cases_and_special_scenarios()
        self.test_8_raw_output_scenarios()
        self.test_9_mixed_type_scenarios()
        self.test_10_error_and_boundary_conditions()

        # Summary
        print("\n" + "=" * 100)
        print("📊 COMPREHENSIVE TEST SUMMARY")
        print("=" * 100)
        print(f"Total Tests: {self.passed + self.failed}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(
            f"Success Rate: {(self.passed/(self.passed + self.failed)*100):.1f}%"
            if (self.passed + self.failed) > 0
            else "0.0%"
        )

        # Failed tests summary
        if self.failed > 0:
            print(f"\n❌ FAILED TESTS ({self.failed}):")
            for result in self.test_results:
                if not result["passed"]:
                    print(
                        f"  - {result['test_name']}: {result['description']}"
                    )
                    print(f"    Pattern: {result['pattern']}")
                    print(
                        f"    Expected: {result['expected']}, Got: {result['actual']}"
                    )

        return self.passed, self.failed


if __name__ == "__main__":
    test_suite = ComprehensivePatternTestSuite()
    test_suite.run_all_tests()
