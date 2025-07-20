#!/usr/bin/env python3
"""
Test script for Enhanced Test Results Exporter
Demonstrates the new fields: row_index, pattern_match, response_body
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add src directory to path to find testpilot package
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from testpilot.exporters.test_results_exporter import TestResultsExporter


class MockTestResult:
    """Mock test result class for demonstration"""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def create_sample_test_results():
    """Create sample test results for demonstration"""

    return [
        MockTestResult(
            host="localhost:8080",
            sheet="AutoCreateSubs",
            test_name="test_auto_create_subs_1",
            method="POST",
            command="curl -X POST /api/v1/subscriptions",
            passed=True,
            duration=0.15,
            timestamp="2025-01-20T10:30:00Z",
            error="< HTTP/1.1 201 Created\n< Content-Type: application/json",
            output='{"subscription_id":"sub_67890","status":"active","created_at":"2025-01-20T10:30:00Z"}',
            Pattern_Match="subscription_creation_pattern",  # From Excel column
            Response_Payload='{"subscription_id":"sub_67890","status":"active","created_at":"2025-01-20T10:30:00Z"}',  # From Excel column
        ),
        MockTestResult(
            host="localhost:8080",
            sheet="AutoCreateSubs",
            test_name="test_auto_create_subs_2",
            method="GET",
            command="curl -X GET /api/v1/subscriptions/sub_67890",
            passed=True,
            duration=0.095,
            timestamp="2025-01-20T10:30:01Z",
            error="< HTTP/1.1 200 OK\n< Content-Type: application/json",
            output='{"subscription_id":"sub_67890","status":"active","subscriber_id":"12345","plan":"premium"}',
            Pattern_Match="YES",  # From Excel column
            Response_Payload='{"subscription_id":"sub_67890","status":"active","subscriber_id":"12345","plan":"premium"}',  # From Excel column
        ),
        MockTestResult(
            host="localhost:8080",
            sheet="UserManagement",
            test_name="test_user_login",
            method="POST",
            command="curl -X POST /api/v1/auth/login",
            passed=False,
            duration=0.2,
            timestamp="2025-01-20T10:30:02Z",
            error="< HTTP/1.1 401 Unauthorized\n< Content-Type: text/plain",
            output="Unauthorized",
            Pattern_Match="NO",  # From Excel column
            Response_Payload="Unauthorized",  # From Excel column
        ),
        MockTestResult(
            host="localhost:8080",
            sheet="ProductCatalog",
            test_name="test_list_products",
            method="GET",
            command="curl -X GET /api/v1/products",
            passed=True,
            duration=0.08,
            timestamp="2025-01-20T10:30:03Z",
            error="< HTTP/1.1 200 OK\n< Content-Type: application/json",
            output='[{"id":1,"name":"Premium Plan","price":29.99},{"id":2,"name":"Basic Plan","price":9.99}]',
            Pattern_Match="api_response_pattern",  # From Excel column
            Response_Payload='[{"id":1,"name":"Premium Plan","price":29.99},{"id":2,"name":"Basic Plan","price":9.99}]',  # From Excel column
        ),
        MockTestResult(
            host="localhost:8080",
            sheet="ErrorHandling",
            test_name="test_invalid_endpoint",
            method="GET",
            command="curl -X GET /api/v1/nonexistent",
            passed=False,
            duration=0.05,
            timestamp="2025-01-20T10:30:04Z",
            error="< HTTP/1.1 404 Not Found\n< Content-Type: text/html",
            output="<html><body><h1>404 Not Found</h1></body></html>",
            Pattern_Match="False",  # From Excel column
            Response_Payload="<html><body><h1>404 Not Found</h1></body></html>",  # From Excel column
        ),
    ]


def main():
    """Demonstrate the enhanced test results exporter"""

    print("🧪 Enhanced Test Results Exporter Demo")
    print("=" * 50)

    # Create sample test results
    test_results = create_sample_test_results()
    print(f"📊 Created {len(test_results)} sample test results")

    # Initialize exporter
    exporter = TestResultsExporter("test_results")

    # Export to JSON with enhanced fields
    print("\n📁 Exporting to enhanced JSON format...")
    json_file = exporter.export_to_json(
        test_results, "enhanced_test_export.json"
    )
    print(f"✅ JSON export completed: {json_file}")

    # Export to CSV with enhanced fields
    print("\n📊 Exporting to enhanced CSV format...")
    csv_file = exporter.export_to_csv(test_results, "enhanced_test_export.csv")
    print(f"✅ CSV export completed: {csv_file}")

    # Display sample of enhanced JSON structure
    print("\n📋 Sample of enhanced JSON structure:")
    with open(json_file, "r") as f:
        data = json.load(f)

    # Show summary with enhanced fields
    print(f"\n📈 Enhanced Summary:")
    summary = data["summary"]
    print(f"   Total Tests: {summary['total_tests']}")
    print(f"   Success Rate: {summary['success_rate']}%")
    print(
        f"   Pattern Match Rate: {summary['enhanced_fields']['pattern_matching']['match_rate']}%"
    )
    print(
        f"   JSON Responses: {summary['enhanced_fields']['response_analysis']['json_responses']}"
    )
    print(
        f"   Avg Response Size: {summary['enhanced_fields']['response_analysis']['avg_response_size_bytes']} bytes"
    )

    # Show first result with enhanced fields
    first_result = data["results"][0]
    print(
        f"\n🔍 Sample Enhanced Test Result (Row {first_result['row_index']}):"
    )
    print(f"   Test: {first_result['test_name']}")
    print(f"   Status: {first_result['status']}")
    print(
        f"   Pattern Match (from Excel): '{first_result['pattern_match']['raw_pattern_match']}'"
    )
    print(f"   Pattern Matched: {first_result['pattern_match']['matched']}")
    print(f"   Pattern Type: {first_result['pattern_match']['pattern_type']}")
    print(
        f"   Response Payload (from Excel): {first_result['response_body']['raw_payload'][:100]}{'...' if len(first_result['response_body']['raw_payload']) > 100 else ''}"
    )
    print(
        f"   Response Size: {first_result['response_body']['size_bytes']} bytes"
    )
    print(f"   Content Type: {first_result['response_body']['content_type']}")

    if first_result["response_body"]["parsed_json"]:
        print(
            f"   Parsed JSON Keys: {list(first_result['response_body']['parsed_json'].keys())}"
        )

    print(f"\n🎉 Demo completed! Check the exported files:")
    print(f"   📄 {json_file}")
    print(f"   📊 {csv_file}")


if __name__ == "__main__":
    main()
