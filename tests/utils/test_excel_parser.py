import os
import tempfile
from io import BytesIO
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

from src.testpilot.core.test_result import TestFlow, TestStep
from src.testpilot.utils.excel_parser import ExcelParser, parse_excel_to_flows


class TestExcelParser:
    """Test cases for ExcelParser class"""

    def test_init_valid_file(self):
        """Test initialization with valid file"""
        with patch("os.path.exists", return_value=True), patch(
            "os.path.getsize", return_value=1000
        ), patch("pandas.ExcelFile") as mock_excel_file, patch(
            "pandas.read_excel"
        ) as mock_read_excel:

            mock_excel_file.return_value.sheet_names = [
                "Sheet1",
                "TestCases",
                "API_Tests",
            ]
            mock_read_excel.return_value = pd.DataFrame(
                {"Test_Name": ["Test1"]}
            )

            parser = ExcelParser("test.xlsx")

            assert "test.xlsx" == parser.excel_file_path
            assert "Sheet1" in parser.sheets
            assert "API_Tests" in parser.sheets
            assert "TestCases" not in parser.sheets  # Should be ignored

    def test_init_file_not_found(self):
        """Test initialization with non-existent file"""
        with patch("os.path.exists", return_value=False):
            with pytest.raises(
                FileNotFoundError, match="Excel file not found"
            ):
                ExcelParser("missing.xlsx")

    def test_init_empty_file(self):
        """Test initialization with empty file"""
        with patch("os.path.exists", return_value=True), patch(
            "os.path.getsize", return_value=0
        ):
            with pytest.raises(ValueError, match="Excel file is empty"):
                ExcelParser("empty.xlsx")

    def test_is_valid_sheet(self):
        """Test sheet name validation"""
        with patch("os.path.exists", return_value=True), patch(
            "os.path.getsize", return_value=1000
        ), patch("pandas.ExcelFile") as mock_excel_file, patch(
            "pandas.read_excel"
        ) as mock_read_excel:

            mock_excel_file.return_value.sheet_names = ["Valid_Sheet"]
            mock_read_excel.return_value = pd.DataFrame(
                {"Test_Name": ["Test1"]}
            )
            parser = ExcelParser("test.xlsx")

            # Valid sheets
            assert parser._is_valid_sheet("Sheet1")
            assert parser._is_valid_sheet("API_Tests")
            assert parser._is_valid_sheet("NRF_Tests")

            # Invalid sheets (contain ignore keywords)
            assert not parser._is_valid_sheet("cover page")
            assert not parser._is_valid_sheet("revision info")
            assert not parser._is_valid_sheet("commonitem details")
            assert not parser._is_valid_sheet("testcases template")
            assert not parser._is_valid_sheet("test cover sheet")

    def test_load_valid_sheets_with_openpyxl(self):
        """Test loading sheets with openpyxl engine"""
        with patch("os.path.exists", return_value=True), patch(
            "os.path.getsize", return_value=1000
        ), patch("pandas.ExcelFile") as mock_excel_file, patch(
            "pandas.read_excel"
        ) as mock_read_excel:

            mock_excel_file.return_value.sheet_names = [
                "Sheet1",
                "Cover",
                "API_Tests",
            ]
            mock_read_excel.return_value = pd.DataFrame(
                {"Test_Name": ["Test1"]}
            )

            parser = ExcelParser("test.xlsx")
            sheets = parser._load_valid_sheets()

            assert "Sheet1" in sheets
            assert "API_Tests" in sheets
            assert "Cover" not in sheets

    def test_load_valid_sheets_no_valid_sheets(self):
        """Test loading when no valid sheets exist"""
        with patch("os.path.exists", return_value=True), patch(
            "os.path.getsize", return_value=1000
        ), patch("pandas.ExcelFile") as mock_excel_file:

            mock_excel_file.return_value.sheet_names = [
                "Cover",
                "Revision",
                "TestCases",
            ]

            with pytest.raises(ValueError, match="No valid sheets found"):
                ExcelParser("test.xlsx")

    def test_list_valid_sheets(self):
        """Test getting list of valid sheets"""
        with patch("os.path.exists", return_value=True), patch(
            "os.path.getsize", return_value=1000
        ), patch("pandas.ExcelFile") as mock_excel_file, patch(
            "pandas.read_excel"
        ) as mock_read_excel:

            mock_excel_file.return_value.sheet_names = [
                "Sheet1",
                "Sheet2",
                "Cover",
            ]
            mock_read_excel.return_value = pd.DataFrame(
                {"Test_Name": ["Test1"]}
            )

            parser = ExcelParser("test.xlsx")
            valid_sheets = parser.list_valid_sheets()

            assert "Sheet1" in valid_sheets
            assert "Sheet2" in valid_sheets
            assert "Cover" not in valid_sheets

    def test_get_sheet(self):
        """Test getting specific sheet"""
        with patch("os.path.exists", return_value=True), patch(
            "os.path.getsize", return_value=1000
        ), patch("pandas.ExcelFile") as mock_excel_file, patch(
            "pandas.read_excel"
        ) as mock_read_excel:

            mock_excel_file.return_value.sheet_names = ["Sheet1"]
            test_df = pd.DataFrame(
                {
                    "Test_Name": ["Test1"],
                    "Command": ["curl http://example.com"],
                }
            )
            mock_read_excel.return_value = test_df

            parser = ExcelParser("test.xlsx")
            sheet = parser.get_sheet("Sheet1")

            assert sheet is not None
            assert sheet.equals(test_df)
            assert parser.get_sheet("NonExistent") is None

    def test_get_all_sheets(self):
        """Test getting all sheets"""
        with patch("os.path.exists", return_value=True), patch(
            "os.path.getsize", return_value=1000
        ), patch("pandas.ExcelFile") as mock_excel_file, patch(
            "pandas.read_excel"
        ) as mock_read_excel:

            mock_excel_file.return_value.sheet_names = ["Sheet1", "Sheet2"]
            mock_read_excel.return_value = pd.DataFrame(
                {"Test_Name": ["Test1"]}
            )

            parser = ExcelParser("test.xlsx")
            all_sheets = parser.get_all_sheets()

            assert len(all_sheets) == 2
            assert "Sheet1" in all_sheets
            assert "Sheet2" in all_sheets


class TestParseExcelToFlows:
    """Test cases for parse_excel_to_flows function"""

    def setup_method(self):
        """Setup test data"""
        self.mock_parser = Mock(spec=ExcelParser)

    def test_parse_basic_flow(self):
        """Test parsing basic test flow"""
        test_df = pd.DataFrame(
            {
                "Test_Name": ["Test1", "Test1", "Test2"],
                "Command": [
                    "curl http://api1.com",
                    "curl http://api2.com",
                    "curl http://api3.com",
                ],
                "URL": [
                    "http://api1.com",
                    "http://api2.com",
                    "http://api3.com",
                ],
                "Method": ["GET", "POST", "GET"],
                "Headers": [
                    None,
                    '{"Content-Type": "application/json"}',
                    None,
                ],
                "Request_Payload": [None, '{"data": "test"}', None],
                "Expected_Status": [200, 201, 200],
                "Pattern_Match": ["status.*ok", None, "success"],
            }
        )

        self.mock_parser.get_sheet.return_value = test_df

        flows = parse_excel_to_flows(self.mock_parser, ["Sheet1"])

        assert len(flows) == 2
        assert flows[0].test_name == "Test1"
        assert len(flows[0].steps) == 2
        assert flows[1].test_name == "Test2"
        assert len(flows[1].steps) == 1

    def test_parse_curl_command_extraction(self):
        """Test extraction of URL, method, headers from curl command"""
        test_df = pd.DataFrame(
            {
                "Test_Name": ["Test1"],
                "Command": [
                    'curl -X POST -H "Authorization: Bearer token" -H "Content-Type: application/json" http://api.example.com/endpoint'
                ],
                "URL": [None],  # URL should be extracted from command
                "Method": [None],  # Method should be extracted from command
                "Headers": [None],  # Headers should be extracted from command
                "Request_Payload": ['{"test": "data"}'],
                "Expected_Status": [200],
                "Pattern_Match": [None],
            }
        )

        self.mock_parser.get_sheet.return_value = test_df

        flows = parse_excel_to_flows(self.mock_parser, ["Sheet1"])

        assert len(flows) == 1
        step = flows[0].steps[0]
        assert step.method == "POST"
        assert step.url == "http://api.example.com/endpoint"
        assert "Authorization" in step.headers
        assert step.headers["Authorization"] == "Bearer token"
        assert "Content-Type" in step.headers

    def test_parse_curl_with_quoted_url(self):
        """Test parsing curl command with quoted URL"""
        test_df = pd.DataFrame(
            {
                "Test_Name": ["Test1"],
                "Command": [
                    'curl -X GET "http://api.example.com/path with spaces"'
                ],
                "URL": [None],
                "Method": [None],
                "Headers": [None],
                "Request_Payload": [None],
                "Expected_Status": [200],
                "Pattern_Match": [None],
            }
        )

        self.mock_parser.get_sheet.return_value = test_df

        flows = parse_excel_to_flows(self.mock_parser, ["Sheet1"])

        step = flows[0].steps[0]
        assert step.url == "http://api.example.com/path with spaces"
        assert step.method == "GET"

    def test_parse_default_values(self):
        """Test default values when fields are missing"""
        test_df = pd.DataFrame(
            {
                "Test_Name": ["Test1"],
                "Command": ["some_command"],
                "URL": [None],
                "Method": [None],
                "Headers": [None],
                "Request_Payload": [None],
                "Expected_Status": [None],
                "Pattern_Match": [None],
            }
        )

        self.mock_parser.get_sheet.return_value = test_df

        flows = parse_excel_to_flows(self.mock_parser, ["Sheet1"])

        step = flows[0].steps[0]
        assert step.method == "GET"  # Default method
        assert step.headers == {}  # Default empty headers
        assert step.url is None

    def test_parse_missing_test_name(self):
        """Test handling of missing test name"""
        test_df = pd.DataFrame(
            {
                "Test_Name": [None],
                "Command": ["curl http://api.com"],
                "URL": ["http://api.com"],
                "Method": ["GET"],
                "Headers": [None],
                "Request_Payload": [None],
                "Expected_Status": [200],
                "Pattern_Match": [None],
            }
        )

        self.mock_parser.get_sheet.return_value = test_df

        flows = parse_excel_to_flows(self.mock_parser, ["Sheet1"])

        assert len(flows) == 1
        assert flows[0].test_name == "row_0"  # Default name based on row index

    def test_parse_multiple_sheets(self):
        """Test parsing multiple sheets"""
        sheet1_df = pd.DataFrame(
            {
                "Test_Name": ["Test1"],
                "Command": ["curl http://api1.com"],
                "URL": ["http://api1.com"],
                "Method": ["GET"],
                "Headers": [None],
                "Request_Payload": [None],
                "Expected_Status": [200],
                "Pattern_Match": [None],
            }
        )

        sheet2_df = pd.DataFrame(
            {
                "Test_Name": ["Test2"],
                "Command": ["curl http://api2.com"],
                "URL": ["http://api2.com"],
                "Method": ["POST"],
                "Headers": [None],
                "Request_Payload": ['{"data": "test"}'],
                "Expected_Status": [201],
                "Pattern_Match": [None],
            }
        )

        self.mock_parser.get_sheet.side_effect = [sheet1_df, sheet2_df]

        flows = parse_excel_to_flows(self.mock_parser, ["Sheet1", "Sheet2"])

        assert len(flows) == 2
        assert flows[0].sheet == "Sheet1"
        assert flows[0].test_name == "Test1"
        assert flows[1].sheet == "Sheet2"
        assert flows[1].test_name == "Test2"

    def test_parse_complex_headers(self):
        """Test parsing complex headers from curl command"""
        test_df = pd.DataFrame(
            {
                "Test_Name": ["Test1"],
                "Command": [
                    "curl -H 'X-Custom-Header: value1' -H \"Authorization: Bearer abc123\" http://api.com"
                ],
                "URL": [None],
                "Method": [None],
                "Headers": [None],
                "Request_Payload": [None],
                "Expected_Status": [200],
                "Pattern_Match": [None],
            }
        )

        self.mock_parser.get_sheet.return_value = test_df

        flows = parse_excel_to_flows(self.mock_parser, ["Sheet1"])

        step = flows[0].steps[0]
        assert step.headers["X-Custom-Header"] == "value1"
        assert step.headers["Authorization"] == "Bearer abc123"

    def test_parse_invalid_curl_command(self):
        """Test handling of invalid curl command"""
        test_df = pd.DataFrame(
            {
                "Test_Name": ["Test1"],
                "Command": ['curl -X "INVALID TOKENS'],  # Malformed command
                "URL": [None],
                "Method": [None],
                "Headers": [None],
                "Request_Payload": [None],
                "Expected_Status": [200],
                "Pattern_Match": [None],
            }
        )

        self.mock_parser.get_sheet.return_value = test_df

        flows = parse_excel_to_flows(self.mock_parser, ["Sheet1"])

        # Should handle gracefully with defaults
        step = flows[0].steps[0]
        assert step.method == "GET"
        assert step.headers == {}

    def test_parse_step_other_fields(self):
        """Test that all row fields are preserved in other_fields"""
        test_df = pd.DataFrame(
            {
                "Test_Name": ["Test1"],
                "Command": ["curl http://api.com"],
                "URL": ["http://api.com"],
                "Method": ["GET"],
                "Headers": [None],
                "Request_Payload": [None],
                "Expected_Status": [200],
                "Pattern_Match": [None],
                "Custom_Field1": ["value1"],
                "Custom_Field2": ["value2"],
            }
        )

        self.mock_parser.get_sheet.return_value = test_df

        flows = parse_excel_to_flows(self.mock_parser, ["Sheet1"])

        step = flows[0].steps[0]
        assert "Custom_Field1" in step.other_fields
        assert step.other_fields["Custom_Field1"] == "value1"
        assert "Custom_Field2" in step.other_fields
        assert step.other_fields["Custom_Field2"] == "value2"


class TestExcelParserIntegration:
    """Integration tests with real Excel file operations"""

    def test_create_and_parse_excel(self):
        """Test creating and parsing a real Excel file"""
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Create test Excel file
            test_data = {
                "Test_Name": ["Test1", "Test1", "Test2"],
                "Command": [
                    "curl -X GET http://api1.com",
                    'curl -X POST -H "Content-Type: application/json" http://api2.com',
                    "curl http://api3.com",
                ],
                "Expected_Status": [200, 201, 200],
                "Pattern_Match": ["success", None, "ok"],
            }

            df = pd.DataFrame(test_data)
            df.to_excel(tmp_path, sheet_name="API_Tests", index=False)

            # Parse the Excel file
            parser = ExcelParser(tmp_path)
            flows = parse_excel_to_flows(parser, parser.list_valid_sheets())

            # Verify results
            assert len(flows) == 2
            assert flows[0].test_name == "Test1"
            assert len(flows[0].steps) == 2
            assert flows[0].steps[0].method == "GET"
            assert flows[0].steps[1].method == "POST"
            assert "Content-Type" in flows[0].steps[1].headers

        finally:
            # Cleanup
            os.unlink(tmp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
