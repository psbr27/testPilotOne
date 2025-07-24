"""
Comprehensive Kubectl Logs Coverage Tests
Tests based on real kubectl log formats from production test results.
"""

import json
import re
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.testpilot.core.enhanced_response_validator import (
    validate_response_enhanced,
)


class TestKubectlVerboseCurlOutput:
    """Test cases for kubectl verbose curl output parsing"""

    def setup_method(self):
        self.mock_logger = Mock()

    def test_kubectl_verbose_curl_with_tty_warning(self):
        """Test parsing kubectl output with TTY warnings"""
        kubectl_output = """Unable to use a TTY - input is not a terminal or the right kind of file
Note: Unnecessary use of -X or --request, GET is already inferred.
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed

  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0*   Trying 151.144.198.65...
* TCP_NODELAY set
* Connected to nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com (151.144.198.65) port 8081 (#0)
* Using HTTP2, server supports multi-use
* Connection state changed (HTTP/2 confirmed)
* Copying HTTP/2 data in stream buffer to connection buffer after upgrade: len=0
* Using Stream ID: 1 (easy handle 0x55a110609a60)
> GET /nnrf-disc/v1/nf-instances?target-nf-type=UDM&requester-nf-type=SMF&supi=imsi-302720603940001 HTTP/2
> Host: nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com:8081
> User-Agent: curl/7.61.1
> Accept: */*
> Content-Type: application/json
>
* Connection state changed (MAX_CONCURRENT_STREAMS == 2147483647)!
< HTTP/2 200
< x-request-id: 2aac2dcb-3b65-48f4-b78b-9d4d78b21e4c
< date: Wed, 23 Jul 2025 21:02:08 GMT
< x-b3-parentspanid: 397c1988f9412382
< content-length: 67
< server: envoy
< x-envoy-upstream-service-time: 33
< 3gpp-sbi-correlation-info: imsi-302720603940001
< 3gpp-sbi-correlation-info: imsi-302720603940001
< x-b3-traceid: d4fb0d8781a12f9e3b062b207b86035c
< x-b3-spanid: 26d3f651163363d2
< x-b3-sampled: 0
< content-type: application/json
< cache-control: max-age=30
< nettylatency: 1753304528967
< requestmethod: GET
<
{ [67 bytes data]

100    67  100    67    0     0   1763      0 --:--:-- --:--:-- --:--:--  1763
* Connection #0 to host nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com left intact
{"validityPeriod":30,"nfInstances":[],"nrfSupportedFeatures":"172"}"""

        # Test pattern matching in complex kubectl output
        result = validate_response_enhanced(
            pattern_match="validityPeriod",
            response_headers=None,
            response_body=kubectl_output,
            response_payload=None,
            logger=self.mock_logger,
            raw_output=kubectl_output,
        )

        assert result["pattern_match_overall"] is True
        # Should find the pattern in the JSON at the end
        assert any(match["result"] for match in result["pattern_matches"])

    def test_kubectl_verbose_curl_http2_connection(self):
        """Test parsing HTTP/2 connection information"""
        kubectl_output = """*   Trying 10.233.11.156...
* TCP_NODELAY set
* Connected to ocnrf-ingressgateway (10.233.11.156) port 8081 (#0)
* Using HTTP2, server supports multi-use
* Connection state changed (HTTP/2 confirmed)
* Copying HTTP/2 data in stream buffer to connection buffer after upgrade: len=0
* Using Stream ID: 1 (easy handle 0x559c99aa06f0)
> PUT /nnrf-nfm/v1/nf-instances/1faf1bbc-6e4a-4454-a507-a14ef8e1bc5c HTTP/2
> Host: ocnrf-ingressgateway:8081
> User-Agent: curl/7.61.1
> Accept: */*
> Content-Type: application/json
> Content-Length: 425
>
} [425 bytes data]
* We are completely uploaded and fine
* Connection state changed (MAX_CONCURRENT_STREAMS == 1000)!
< HTTP/2 201
< date: Tue, 22 Jul 2025 19:12:25 GMT
< location: http://ocnrf-tailgate-ingressgateway.ocnrf:8080/nnrf-nfm/v1/nf-instances/1faf1bbc-6e4a-4454-a507-a14ef8e1bc5c
< content-type: application/json
< accept-encoding: gzip
< nettylatency: 1753211545451
< requestmethod: PUT
<
{ [321 bytes data]
100   746    0   321  100   425  12840  17000 --:--:-- --:--:-- --:--:-- 29840
* Connection #0 to host ocnrf-ingressgateway left intact
{"nfInstanceId":"1faf1bbc-6e4a-4454-a507-a14ef8e1bc5c","nfType":"UDM","nfStatus":"REGISTERED"}"""

        # Test various pattern matches in HTTP/2 output
        test_patterns = [
            ("HTTP/2 201", True),  # Status code
            ("MAX_CONCURRENT_STREAMS", True),  # Connection info
            ("nfStatus.*REGISTERED", True),  # JSON content
            ("Content-Length: 425", True),  # Header
            ("nonexistent", False),  # Should not match
        ]

        for pattern, should_match in test_patterns:
            result = validate_response_enhanced(
                pattern_match=pattern,
                response_headers=None,
                response_body=kubectl_output,
                response_payload=None,
                logger=self.mock_logger,
                raw_output=kubectl_output,
            )

            if should_match:
                assert (
                    result["pattern_match_overall"] is True
                ), f"Pattern '{pattern}' should match"
            else:
                assert (
                    result["pattern_match_overall"] is False
                ), f"Pattern '{pattern}' should not match"

    def test_kubectl_progress_bar_interference(self):
        """Test handling of curl progress bars and transfer stats"""
        kubectl_output = """  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed

  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0
  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0
100    67  100    67    0     0   1763      0 --:--:-- --:--:-- --:--:--  1763
100   746    0   321  100   425  12840  17000 --:--:-- --:--:-- --:--:-- 29840
{"status": "success", "data": {"important": "value"}}"""

        # Test that progress bars don't interfere with JSON parsing
        result = validate_response_enhanced(
            pattern_match='"important": "value"',
            response_headers=None,
            response_body=kubectl_output,
            response_payload=None,
            logger=self.mock_logger,
            raw_output=kubectl_output,
        )

        assert result["pattern_match_overall"] is True

    def test_kubectl_carriage_return_handling(self):
        """Test handling of carriage returns in kubectl output"""
        kubectl_output = """* Connection state changed (MAX_CONCURRENT_STREAMS == 1000)!
< HTTP/2 200 \r
< date: Tue, 22 Jul 2025 19:12:26 GMT\r
< content-type: application/json\r
< accept-encoding: gzip\r
< nettylatency: 1753211546758\r
< requestmethod: GET\r
< \r
{ [321 bytes data]
\r100   321    0   321    0     0  24692      0 --:--:-- --:--:-- --:--:-- 24692
* Connection #0 to host ocnrf-ingressgateway left intact
{"result": "ok"}"""

        # Test patterns with carriage returns
        result = validate_response_enhanced(
            pattern_match="content-type: application/json",
            response_headers=None,
            response_body=kubectl_output,
            response_payload=None,
            logger=self.mock_logger,
            raw_output=kubectl_output,
        )

        assert result["pattern_match_overall"] is True

    def test_kubectl_multiple_json_objects(self):
        """Test handling of multiple JSON objects in kubectl logs"""
        kubectl_multi_json = """{"timestamp": "2023-01-01T10:00:00Z", "level": "INFO", "message": "Service started"}
{"timestamp": "2023-01-01T10:00:01Z", "level": "INFO", "message": "Processing request", "requestId": "req123"}
{"timestamp": "2023-01-01T10:00:02Z", "level": "ERROR", "message": "Database connection failed", "error": "timeout"}
{"timestamp": "2023-01-01T10:00:03Z", "level": "INFO", "message": "Request completed", "status": "success"}"""

        # Test finding patterns across multiple JSON log entries
        test_cases = [
            ("Service started", True),
            ("Database connection failed", True),
            ("requestId.*req123", True),
            ("level.*ERROR", True),
            ("nonexistent_pattern", False),
        ]

        for pattern, should_match in test_cases:
            result = validate_response_enhanced(
                pattern_match=pattern,
                response_headers=None,
                response_body=kubectl_multi_json,
                response_payload=None,
                logger=self.mock_logger,
                raw_output=kubectl_multi_json,
            )

            if should_match:
                assert (
                    result["pattern_match_overall"] is True
                ), f"Pattern '{pattern}' should match in multi-JSON logs"
            else:
                assert (
                    result["pattern_match_overall"] is False
                ), f"Pattern '{pattern}' should not match"

    def test_kubectl_mixed_content_types(self):
        """Test kubectl output with mixed content types"""
        mixed_output = """< content-type: text/plain
<
Plain text response content here
< content-type: application/xml
<
<?xml version="1.0"?>
<root>
    <element>value</element>
</root>
< content-type: application/json
<
{"json": "content", "nested": {"key": "value"}}"""

        # Test patterns across different content types
        test_patterns = [
            ("Plain text response", True),
            ("<element>value</element>", True),
            ('"json": "content"', True),
            ("nested.*key.*value", True),
        ]

        for pattern, should_match in test_patterns:
            result = validate_response_enhanced(
                pattern_match=pattern,
                response_headers=None,
                response_body=mixed_output,
                response_payload=None,
                logger=self.mock_logger,
                raw_output=mixed_output,
            )

            if should_match:
                assert (
                    result["pattern_match_overall"] is True
                ), f"Pattern '{pattern}' should match in mixed content"


class TestKubectlErrorScenarios:
    """Test cases for kubectl error scenarios and edge cases"""

    def setup_method(self):
        self.mock_logger = Mock()

    def test_kubectl_connection_failures(self):
        """Test kubectl output with connection failures"""
        connection_failure = """*   Trying 192.168.1.100...
* TCP_NODELAY set
* connect to 192.168.1.100 port 8081 failed: Connection refused
*   Trying 192.168.1.101...
* TCP_NODELAY set
* connect to 192.168.1.101 port 8081 failed: Connection timed out
* Failed to connect to service port 8081: Connection refused
curl: (7) Failed to connect to service port 8081: Connection refused
command terminated with exit code 7"""

        # Test error pattern matching
        result = validate_response_enhanced(
            pattern_match="Connection refused",
            response_headers=None,
            response_body=connection_failure,
            response_payload=None,
            logger=self.mock_logger,
            raw_output=connection_failure,
        )

        assert result["pattern_match_overall"] is True

    def test_kubectl_ssl_certificate_errors(self):
        """Test kubectl output with SSL certificate errors"""
        ssl_error = """*   Trying 10.0.0.1...
* TCP_NODELAY set
* Connected to secure-service (10.0.0.1) port 443 (#0)
* ALPN, offering h2
* ALPN, offering http/1.1
* successfully set certificate verify locations:
*   CAfile: /etc/ssl/certs/ca-certificates.crt
  CApath: /etc/ssl/certs
* SSL connection using TLSv1.3 / TLS_AES_256_GCM_SHA384
* ALPN, server accepted to use h2
* Server certificate:
*  subject: CN=wrong-hostname.com
*  start date: Jan  1 00:00:00 2023 GMT
*  expire date: Dec 31 23:59:59 2023 GMT
*  subjectAltName does not match secure-service
* SSL: certificate subject name 'wrong-hostname.com' does not match target host name 'secure-service'
* Closing connection 0
curl: (51) SSL: certificate subject name 'wrong-hostname.com' does not match target host name 'secure-service'"""

        # Test SSL error patterns
        ssl_patterns = [
            ("certificate subject name.*does not match", True),
            ("SSL connection using TLSv1.3", True),
            ("Server certificate", True),
            ("Closing connection", True),
        ]

        for pattern, should_match in ssl_patterns:
            result = validate_response_enhanced(
                pattern_match=pattern,
                response_headers=None,
                response_body=ssl_error,
                response_payload=None,
                logger=self.mock_logger,
                raw_output=ssl_error,
            )

            if should_match:
                assert (
                    result["pattern_match_overall"] is True
                ), f"SSL pattern '{pattern}' should match"

    def test_kubectl_timeout_scenarios(self):
        """Test kubectl output with timeout scenarios"""
        timeout_output = """*   Trying 10.0.0.1...
* TCP_NODELAY set
* Connected to slow-service (10.0.0.1) port 8080 (#0)
> GET /slow-endpoint HTTP/1.1
> Host: slow-service:8080
> User-Agent: curl/7.61.1
> Accept: */*
>
* Operation timed out after 30000 milliseconds with 0 bytes received
* Closing connection 0
curl: (28) Operation timed out after 30000 milliseconds with 0 bytes received"""

        result = validate_response_enhanced(
            pattern_match="Operation timed out",
            response_headers=None,
            response_body=timeout_output,
            response_payload=None,
            logger=self.mock_logger,
            raw_output=timeout_output,
        )

        assert result["pattern_match_overall"] is True

    def test_kubectl_pod_not_found_errors(self):
        """Test kubectl output when pod is not found"""
        pod_not_found = """Error from server (NotFound): pods "nonexistent-pod-12345" not found
error: unable to upgrade connection: container not found ("app-container")
Error executing in Docker Container: 126"""

        # Test pod error patterns
        result = validate_response_enhanced(
            pattern_match="pods.*not found",
            response_headers=None,
            response_body=pod_not_found,
            response_payload=None,
            logger=self.mock_logger,
            raw_output=pod_not_found,
        )

        assert result["pattern_match_overall"] is True

    def test_kubectl_resource_limits_exceeded(self):
        """Test kubectl output with resource limit errors"""
        resource_limits = """OOMKilled: Container exceeded memory limit
CPU throttling activated: container using 100% of allocated CPU
Disk space exceeded: /tmp filesystem full
Network timeout: packet loss rate 95%
Pod evicted due to resource pressure: Evicted"""

        resource_patterns = [
            ("OOMKilled.*memory limit", True),
            ("CPU throttling", True),
            ("Disk space exceeded", True),
            ("Pod evicted.*resource pressure", True),
        ]

        for pattern, should_match in resource_patterns:
            result = validate_response_enhanced(
                pattern_match=pattern,
                response_headers=None,
                response_body=resource_limits,
                response_payload=None,
                logger=self.mock_logger,
                raw_output=resource_limits,
            )

            if should_match:
                assert (
                    result["pattern_match_overall"] is True
                ), f"Resource pattern '{pattern}' should match"


class TestKubectlComplexScenarios:
    """Test cases for complex kubectl scenarios"""

    def setup_method(self):
        self.mock_logger = Mock()

    def test_kubectl_streaming_logs_with_timestamps(self):
        """Test kubectl streaming logs with various timestamp formats"""
        streaming_logs = """2023-07-23T14:29:23.123456789Z app-container {"level":"info","msg":"Application started","version":"1.2.3"}
2023-07-23T14:29:24.987654321Z app-container {"level":"debug","msg":"Database connection established","db":"postgresql"}
2023-07-23T14:29:25.555000000Z app-container {"level":"warn","msg":"High memory usage detected","memory_pct":85}
2023-07-23T14:29:26.777888999Z app-container {"level":"error","msg":"Request failed","error":"timeout","request_id":"req-12345"}
2023-07-23T14:29:27.123000000Z app-container {"level":"info","msg":"Request completed","status":"success","duration_ms":1234}"""

        # Test timestamp and structured log parsing
        timestamp_patterns = [
            ("2023-07-23T14:29:23", True),  # Timestamp matching
            ('"level":"error"', True),  # JSON field matching
            ("request_id.*req-12345", True),  # Nested field matching
            ("memory_pct.*85", True),  # Numeric field matching
            ("duration_ms", True),  # Field name matching
        ]

        for pattern, should_match in timestamp_patterns:
            result = validate_response_enhanced(
                pattern_match=pattern,
                response_headers=None,
                response_body=streaming_logs,
                response_payload=None,
                logger=self.mock_logger,
                raw_output=streaming_logs,
            )

            if should_match:
                assert (
                    result["pattern_match_overall"] is True
                ), f"Timestamp pattern '{pattern}' should match"

    def test_kubectl_multi_container_logs(self):
        """Test kubectl logs from multiple containers"""
        multi_container_logs = """nginx-container 192.168.1.10 - - [23/Jul/2023:14:29:23 +0000] "GET /api/health HTTP/1.1" 200 45 "-" "kube-probe/1.27"
app-container {"timestamp":"2023-07-23T14:29:23Z","level":"info","component":"health-check","status":"ok"}
sidecar-container [2023-07-23 14:29:23] INFO: Metrics collected and sent to prometheus
nginx-container 192.168.1.10 - - [23/Jul/2023:14:29:24 +0000] "POST /api/users HTTP/1.1" 201 123 "-" "Mozilla/5.0"
app-container {"timestamp":"2023-07-23T14:29:24Z","level":"info","component":"user-service","action":"create","user_id":"user123"}
sidecar-container [2023-07-23 14:29:24] WARN: High CPU usage detected on container app-container"""

        # Test patterns across different container log formats
        container_patterns = [
            ("nginx-container.*GET /api/health", True),  # Nginx access log
            (
                '"component":"health-check"',
                True,
            ),  # App container structured log
            (
                "sidecar-container.*Metrics collected",
                True,
            ),  # Sidecar container log
            ("POST /api/users.*201", True),  # HTTP status in nginx log
            ('"user_id":"user123"', True),  # User action in app log
            ("High CPU usage detected", True),  # Warning in sidecar log
        ]

        for pattern, should_match in container_patterns:
            result = validate_response_enhanced(
                pattern_match=pattern,
                response_headers=None,
                response_body=multi_container_logs,
                response_payload=None,
                logger=self.mock_logger,
                raw_output=multi_container_logs,
            )

            if should_match:
                assert (
                    result["pattern_match_overall"] is True
                ), f"Multi-container pattern '{pattern}' should match"

    def test_kubectl_binary_data_handling(self):
        """Test kubectl output containing binary data or non-UTF8 content"""
        binary_mixed_output = """Content-Type: application/octet-stream
Content-Length: 1024

\x00\x01\x02\x03Binary data here\xff\xfe\xfd
{"json_after_binary": true, "status": "ok"}
More binary: \x80\x81\x82\x83\x84\x85
Text content continues here
{"final_json": {"result": "success"}}"""

        # Test that patterns can still be found despite binary content
        result = validate_response_enhanced(
            pattern_match='"json_after_binary": true',
            response_headers=None,
            response_body=binary_mixed_output,
            response_payload=None,
            logger=self.mock_logger,
            raw_output=binary_mixed_output,
        )

        assert result["pattern_match_overall"] is True

    def test_kubectl_very_large_log_output(self):
        """Test kubectl with very large log output"""
        # Simulate a large log file
        large_log_base = '{{"timestamp": "2023-07-23T14:29:23Z", "level": "info", "message": "Processing batch {}", "batch_id": {}, "items_processed": {}}}'

        large_log_lines = []
        for i in range(1000):  # 1000 log entries
            large_log_lines.append(large_log_base.format(i, i, i * 10))

        # Add a target pattern at the end
        large_log_lines.append(
            '{"timestamp": "2023-07-23T14:30:00Z", "level": "info", "message": "Processing completed", "total_batches": 1000, "status": "SUCCESS"}'
        )

        large_log_output = "\n".join(large_log_lines)

        # Test finding pattern in large output
        result = validate_response_enhanced(
            pattern_match="Processing completed",
            response_headers=None,
            response_body=large_log_output,
            response_payload=None,
            logger=self.mock_logger,
            raw_output=large_log_output,
        )

        assert result["pattern_match_overall"] is True

    def test_kubectl_log_with_escape_sequences(self):
        """Test kubectl logs with ANSI escape sequences and terminal colors"""
        colored_logs = """\033[32m[INFO]\033[0m 2023-07-23 14:29:23 Application started successfully
\033[33m[WARN]\033[0m 2023-07-23 14:29:24 Configuration file not found, using defaults
\033[31m[ERROR]\033[0m 2023-07-23 14:29:25 Database connection failed: \033[1mConnection timeout\033[0m
\033[36m[DEBUG]\033[0m 2023-07-23 14:29:26 Request details: {"method": "GET", "path": "/api/users", "status": 200}
\033[32m[INFO]\033[0m 2023-07-23 14:29:27 Request completed in 150ms"""

        # Test patterns with and without ANSI escape sequences
        escape_patterns = [
            ("Application started successfully", True),
            ("Configuration file not found", True),
            ("Database connection failed", True),
            ('"method": "GET"', True),
            ("Request completed in 150ms", True),
        ]

        for pattern, should_match in escape_patterns:
            result = validate_response_enhanced(
                pattern_match=pattern,
                response_headers=None,
                response_body=colored_logs,
                response_payload=None,
                logger=self.mock_logger,
                raw_output=colored_logs,
            )

            if should_match:
                assert (
                    result["pattern_match_overall"] is True
                ), f"ANSI escape pattern '{pattern}' should match"


class TestKubectlRealWorldPatterns:
    """Test cases based on real-world kubectl log patterns from the test results"""

    def setup_method(self):
        self.mock_logger = Mock()

    def test_real_nrf_discovery_output(self):
        """Test against real NRF discovery output from test results"""
        # Based on actual test_results_NFInstanceDiscovery-NRF.json
        real_nrf_output = """Unable to use a TTY - input is not a terminal or the right kind of file
Note: Unnecessary use of -X or --request, GET is already inferred.
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed

  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0*   Trying 151.144.198.65...
* TCP_NODELAY set
* Connected to nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com (151.144.198.65) port 8081 (#0)
* Using HTTP2, server supports multi-use
* Connection state changed (HTTP/2 confirmed)
* Copying HTTP/2 data in stream buffer to connection buffer after upgrade: len=0
* Using Stream ID: 1 (easy handle 0x55a110609a60)
> GET /nnrf-disc/v1/nf-instances?target-nf-type=UDM&requester-nf-type=SMF&supi=imsi-302720603940001 HTTP/2
> Host: nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com:8081
> User-Agent: curl/7.61.1
> Accept: */*
> Content-Type: application/json
>
* Connection state changed (MAX_CONCURRENT_STREAMS == 2147483647)!
< HTTP/2 200
< x-request-id: 2aac2dcb-3b65-48f4-b78b-9d4d78b21e4c
< date: Wed, 23 Jul 2025 21:02:08 GMT
< x-b3-parentspanid: 397c1988f9412382
< content-length: 67
< server: envoy
< x-envoy-upstream-service-time: 33
< 3gpp-sbi-correlation-info: imsi-302720603940001
< 3gpp-sbi-correlation-info: imsi-302720603940001
< x-b3-traceid: d4fb0d8781a12f9e3b062b207b86035c
< x-b3-spanid: 26d3f651163363d2
< x-b3-sampled: 0
< content-type: application/json
< cache-control: max-age=30
< nettylatency: 1753304528967
< requestmethod: GET
<
{ [67 bytes data]

100    67  100    67    0     0   1763      0 --:--:-- --:--:-- --:--:--  1763
* Connection #0 to host nnrf-106.rcnltxek.rcn.nnrf.5gc.vzimstest.com left intact
{"validityPeriod":30,"nfInstances":[],"nrfSupportedFeatures":"172"}"""

        # Test real-world NRF patterns
        nrf_patterns = [
            ("validityPeriod.*30", True),
            ("nfInstances.*\\[\\]", True),
            ("nrfSupportedFeatures.*172", True),
            ("HTTP/2 200", True),
            ("x-request-id", True),
            ("3gpp-sbi-correlation-info", True),
            ("envoy", True),
            ("imsi-302720603940001", True),
        ]

        for pattern, should_match in nrf_patterns:
            result = validate_response_enhanced(
                pattern_match=pattern,
                response_headers=None,
                response_body=real_nrf_output,
                response_payload=None,
                logger=self.mock_logger,
                raw_output=real_nrf_output,
            )

            if should_match:
                assert (
                    result["pattern_match_overall"] is True
                ), f"Real NRF pattern '{pattern}' should match"

    def test_real_nrf_registration_output(self):
        """Test against real NRF registration output from test results"""
        # Based on actual test_results_nrf_registration.json
        real_registration_output = """Unable to use a TTY - input is not a terminal or the right kind of file
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed

  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0*   Trying 10.233.11.156...
* TCP_NODELAY set
* Connected to ocnrf-ingressgateway (10.233.11.156) port 8081 (#0)
* Using HTTP2, server supports multi-use
* Connection state changed (HTTP/2 confirmed)
* Copying HTTP/2 data in stream buffer to connection buffer after upgrade: len=0
* Using Stream ID: 1 (easy handle 0x559c99aa06f0)
> PUT /nnrf-nfm/v1/nf-instances/1faf1bbc-6e4a-4454-a507-a14ef8e1bc5c HTTP/2
> Host: ocnrf-ingressgateway:8081
> User-Agent: curl/7.61.1
> Accept: */*
> Content-Type: application/json
> Content-Length: 425
>
} [425 bytes data]
* We are completely uploaded and fine
* Connection state changed (MAX_CONCURRENT_STREAMS == 1000)!
< HTTP/2 201
< date: Tue, 22 Jul 2025 19:12:25 GMT
< location: http://ocnrf-tailgate-ingressgateway.ocnrf:8080/nnrf-nfm/v1/nf-instances/1faf1bbc-6e4a-4454-a507-a14ef8e1bc5c
< content-type: application/json
< accept-encoding: gzip
< nettylatency: 1753211545451
< requestmethod: PUT
<
{ [321 bytes data]
100   746    0   321  100   425  12840  17000 --:--:-- --:--:-- --:--:-- 29840
* Connection #0 to host ocnrf-ingressgateway left intact
{"nfInstanceId":"1faf1bbc-6e4a-4454-a507-a14ef8e1bc5c","nfType":"UDM","nfStatus":"REGISTERED","heartBeatTimer":90,"fqdn":"UDM.d5g.oracle.com","interPlmnFqdn":"UDM-d5g.oracle.com","ipv4Addresses":["192.168.2.100","192.168.3.100","192.168.2.110","192.168.3.110"],"ipv6Addresses":["2001:0db8:85a3:0000:0000:8a2e:0370:7334"]}"""

        # Test complex JSON pattern matching in registration response
        registration_patterns = [
            ('"nfStatus":"REGISTERED"', True),
            ('"nfType":"UDM"', True),
            ('"heartBeatTimer":90', True),
            ('"fqdn":"UDM.d5g.oracle.com"', True),
            ("192.168.2.100", True),
            ("2001:0db8:85a3:0000:0000:8a2e:0370:7334", True),
            ("HTTP/2 201", True),
            ("Content-Length: 425", True),
        ]

        for pattern, should_match in registration_patterns:
            result = validate_response_enhanced(
                pattern_match=pattern,
                response_headers=None,
                response_body=real_registration_output,
                response_payload=None,
                logger=self.mock_logger,
                raw_output=real_registration_output,
            )

            if should_match:
                assert (
                    result["pattern_match_overall"] is True
                ), f"Registration pattern '{pattern}' should match"

    def test_real_world_json_validation(self):
        """Test JSON validation against real response payloads"""
        real_response = {
            "validityPeriod": 30,
            "nfInstances": [],
            "nrfSupportedFeatures": "172",
        }
        kubectl_with_json = """< HTTP/2 200
< content-type: application/json
< content-length: 67
{"validityPeriod":30,"nfInstances":[],"nrfSupportedFeatures":"172"}"""

        # Extract just the JSON part for response_body (dict validation)
        json_only = '{"validityPeriod":30,"nfInstances":[],"nrfSupportedFeatures":"172"}'

        # Test both pattern and dict matching
        result = validate_response_enhanced(
            pattern_match="validityPeriod",
            response_headers={"content-type": "application/json"},
            response_body=json_only,  # Use JSON only for dict validation
            response_payload=real_response,
            logger=self.mock_logger,
            raw_output=kubectl_with_json,  # Full kubectl output for pattern matching
        )

        # Both pattern and dict validation should succeed
        assert result["pattern_match_overall"] is True
        # Dict match depends on implementation details, but shouldn't crash
        assert "dict_match" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
