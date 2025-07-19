import json
import re
from datetime import datetime


class CurlOutputParser:
    def __init__(self):
        self.connection_info = {}
        self.request_info = {}
        self.response_info = {}
        self.response_headers = {}
        self.timing_info = {}
        self.response_body = []
        self.curl_info = {}

    def parse(self, lines):
        """Parse curl output - works with various curl formats"""

        # Reset all data
        self.__init__()

        in_response_body = False
        current_section = None

        for line in lines:
            line = line.strip()

            # Skip empty lines and progress bars
            if not line or self._is_progress_line(line):
                continue

            # Detect different sections
            if line.startswith("*"):
                self._parse_curl_info(line)
            elif line.startswith(">"):
                self._parse_request_line(line)
            elif line.startswith("<"):
                if self._parse_response_line(line):
                    in_response_body = False
                else:
                    in_response_body = True
            elif in_response_body:
                self._parse_response_body(line)
            elif self._is_timing_line(line):
                self._parse_timing_line(line)

        return self._organize_data()

    def _is_progress_line(self, line):
        """Check if line is curl progress output"""
        return (
            line.startswith("%")
            or "Total" in line
            and "Received" in line
            and "Speed" in line
            or re.match(r"^\s*\d+\s+\d+\s+\d+\s+\d+", line)
        )

    def _parse_curl_info(self, line):
        """Parse curl connection info lines (starting with *)"""
        line = line[1:].strip()  # Remove *

        if line.startswith("Trying"):
            self.connection_info["target_ip"] = line.split()[1].rstrip("...")
        elif line.startswith("Connected to"):
            parts = line.split()
            if len(parts) >= 6:
                self.connection_info["hostname"] = parts[2]
                self.connection_info["port"] = parts[4]
        elif "HTTP/2" in line:
            self.connection_info["protocol"] = "HTTP/2"
        elif "HTTP/1.1" in line:
            self.connection_info["protocol"] = "HTTP/1.1"
        elif "Stream ID:" in line:
            match = re.search(r"Stream ID:\s*(\d+)", line)
            if match:
                self.connection_info["stream_id"] = match.group(1)
        elif "SSL" in line or "TLS" in line:
            self.connection_info["encryption"] = "TLS/SSL"
        elif "Connection #" in line and "left intact" in line:
            self.connection_info["connection_reused"] = True
        elif "Closing connection" in line:
            self.connection_info["connection_closed"] = True

    def _parse_request_line(self, line):
        """Parse request lines (starting with >)"""
        line = line[1:].strip()  # Remove >

        # Parse request line (GET /path HTTP/1.1)
        if re.match(r"^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)", line):
            parts = line.split()
            if len(parts) >= 3:
                self.request_info["method"] = parts[0]
                self.request_info["path"] = parts[1]
                self.request_info["protocol"] = parts[2]
        elif ":" in line:
            # Parse request headers
            key, value = line.split(":", 1)
            self.request_info[key.strip().lower().replace("-", "_")] = (
                value.strip()
            )

    def _parse_response_line(self, line):
        """Parse response lines (starting with <)"""
        line = line[1:].strip()  # Remove <

        # Parse status line
        if re.match(r"^HTTP/[12](\.[01])?\s+\d+", line):
            parts = line.split()
            if len(parts) >= 2:
                self.response_info["protocol"] = parts[0]
                self.response_info["status_code"] = parts[1]
                if len(parts) > 2:
                    self.response_info["status_text"] = " ".join(parts[2:])
            return True
        elif ":" in line:
            # Parse response headers
            key, value = line.split(":", 1)
            self.response_headers[key.strip()] = value.strip()
            return True
        elif not line:
            # Empty line indicates end of headers
            return False

        return False

    def _parse_response_body(self, line):
        """Parse response body content"""
        if (
            not line.startswith("{")
            and "[" not in line
            and "bytes data" not in line
        ):
            self.response_body.append(line)

    def _is_timing_line(self, line):
        """Check if line contains timing information"""
        return (
            re.match(r"^\s*\d+\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+", line)
            or "speed" in line.lower()
            and "time" in line.lower()
        )

    def _parse_timing_line(self, line):
        """Parse timing information from final curl output"""
        # Match the final statistics line
        match = re.match(
            r"^\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)", line
        )
        if match:
            self.timing_info.update(
                {
                    "total_bytes": match.group(1),
                    "bytes_downloaded": match.group(2),
                    "bytes_uploaded": match.group(4),
                    "average_speed": match.group(6),
                }
            )

    def _organize_data(self):
        """Organize all parsed data into a structured format"""
        return {
            "connection": self.connection_info,
            "request": self.request_info,
            "response": self.response_info,
            "response_headers": self.response_headers,
            "response_body": self.response_body,
            "timing": self.timing_info,
        }


def print_universal_analysis(parsed_data):
    """Universal pretty printer for any curl output"""

    # print("=" * 80)
    # print("🌐 UNIVERSAL CURL ANALYSIS")
    # print("=" * 80)

    # # Connection Information
    # print("\n📡 CONNECTION INFO")
    # print("-" * 40)
    # conn = parsed_data['connection']
    # for key, value in conn.items():
    #     formatted_key = key.replace('_', ' ').title()
    #     print(f"{formatted_key}: {value}")

    # # Request Information
    # print("\n📤 REQUEST INFO")
    # print("-" * 40)
    req = parsed_data["request"]

    # # Show method and path first
    # if req.get('method'):
    #     method_emoji = {
    #         'GET': '📥', 'POST': '📤', 'PUT': '📝',
    #         'DELETE': '🗑️', 'PATCH': '🔧', 'HEAD': '👀'
    #     }.get(req['method'], '🔗')
    #     print(f"Method: {method_emoji} {req['method']}")

    # if req.get('path'):
    #     print(f"Path: {req['path']}")

    # # Show other request headers
    # for key, value in req.items():
    #     if key not in ['method', 'path', 'protocol']:
    #         formatted_key = key.replace('_', ' ').title()
    #         print(f"{formatted_key}: {value}")

    # Response Information
    # print("\n📥 RESPONSE INFO")
    # print("-" * 40)
    resp = parsed_data["response"]

    if resp.get("status_code"):
        status_code = resp["status_code"]
        status_emoji = {
            "200": "✅",
            "201": "✅",
            "204": "✅",
            "301": "🔄",
            "302": "🔄",
            "304": "🔄",
            "400": "❌",
            "401": "🔐",
            "403": "🚫",
            "404": "🔍",
            "409": "⚠️",
            "500": "💥",
            "502": "🚨",
            "503": "⏸️",
        }.get(status_code, "❓")

        status_text = resp.get("status_text", "")
        print(f"Status: {status_emoji} {status_code} {status_text}")

    # Response Headers
    print("\n📋 RESPONSE HEADERS")
    print("-" * 40)
    headers = parsed_data["response_headers"]

    if headers:
        # Categorize headers
        standard_headers = [
            "date",
            "server",
            "content-type",
            "content-length",
            "cache-control",
        ]
        security_headers = [
            "x-frame-options",
            "x-xss-protection",
            "strict-transport-security",
        ]
        custom_headers = [
            k
            for k in headers.keys()
            if k.lower() not in standard_headers + security_headers
        ]

        # Print standard headers first
        for header in standard_headers:
            if header in headers:
                print(f"{header.title()}: {headers[header]}")

        # Print security headers
        security_found = [h for h in security_headers if h in headers]
        if security_found:
            print("\n Security Headers:")
            for header in security_found:
                print(f"  {header.title()}: {headers[header]}")

        # Print custom headers
        if custom_headers:
            print("\n Custom Headers:")
            for header in custom_headers:
                value = headers[header]
                # Handle special headers
                if "3gpp-sbi" in header.lower():
                    print(f"  📱 {header}:")
                    if ";" in value:
                        for part in value.split(";"):
                            if part.strip():
                                print(f"    {part.strip()}")
                    else:
                        print(f"    {value}")
                else:
                    print(f"  {header}: {value}")

    # Response Body
    if parsed_data["response_body"]:
        print("\n📄 RESPONSE BODY")
        print("-" * 40)
        body_text = "\n".join(parsed_data["response_body"])

        # Try to parse as JSON
        try:
            json_data = json.loads(body_text)
            print(json.dumps(json_data, indent=2))
        except:
            print(
                body_text[:500] + "..." if len(body_text) > 500 else body_text
            )

    # Timing Information
    timing = parsed_data["timing"]
    if timing:
        print("\n⏱️ PERFORMANCE INFO")
        print("-" * 40)
        for key, value in timing.items():
            formatted_key = key.replace("_", " ").title()
            if "speed" in key.lower():
                print(f"{formatted_key}: {value} bytes/sec")
            else:
                print(f"{formatted_key}: {value} bytes")

    print("\n" + "=" * 80)


# Example usage
def analyze_curl_output(lines):
    """Main function to analyze any curl output"""
    parser = CurlOutputParser()
    parsed_data = parser.parse(lines)
    print_universal_analysis(parsed_data)
    return parsed_data
