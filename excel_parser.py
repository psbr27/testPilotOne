import re
import shlex
from typing import Dict, List, Optional, Set
import pandas as pd
from test_result import TestFlow, TestStep


class ExcelParser:
    def __init__(self, excel_file_path: str):
        self.excel_file_path = excel_file_path
        self.ignore_keywords: Set[str] = {
            "cover",
            "revision",
            "commonitem",
            "testcases",
        }  # case-insensitive match
        self.sheets: Dict[str, pd.DataFrame] = self._load_valid_sheets()

    def _is_valid_sheet(self, sheet_name: str) -> bool:
        """Check if sheet name is valid (not in ignore list)."""
        lowered = sheet_name.strip().lower()
        return not any(keyword in lowered for keyword in self.ignore_keywords)

    def _load_valid_sheets(self) -> Dict[str, pd.DataFrame]:
        """Load all valid sheets from Excel file."""
        import os

        # Check if file exists and has content
        if not os.path.exists(self.excel_file_path):
            raise FileNotFoundError(f"Excel file not found: {self.excel_file_path}")

        file_size = os.path.getsize(self.excel_file_path)
        if file_size == 0:
            raise ValueError(f"Excel file is empty (0 bytes): {self.excel_file_path}")

        try:
            # Try with openpyxl engine first (for .xlsx files)
            try:
                all_sheets = pd.ExcelFile(
                    self.excel_file_path, engine="openpyxl"
                ).sheet_names
            except Exception:
                # Fallback to xlrd for older .xls files
                try:
                    all_sheets = pd.ExcelFile(
                        self.excel_file_path, engine="xlrd"
                    ).sheet_names
                except Exception:
                    # Let pandas auto-detect
                    all_sheets = pd.ExcelFile(self.excel_file_path).sheet_names

            valid_sheets = [s for s in all_sheets if self._is_valid_sheet(s)]

            if not valid_sheets:
                raise ValueError(
                    f"No valid sheets found in {self.excel_file_path}. "
                    f"All sheets: {all_sheets}"
                )

            loaded_sheets = {}
            for sheet in valid_sheets:
                try:
                    loaded_sheets[sheet] = pd.read_excel(
                        self.excel_file_path, sheet_name=sheet, engine="openpyxl"
                    )
                except Exception:
                    loaded_sheets[sheet] = pd.read_excel(
                        self.excel_file_path, sheet_name=sheet
                    )

            return loaded_sheets

        except Exception as e:
            raise ValueError(
                f"Failed to load Excel file {self.excel_file_path}: "
                f"{type(e).__name__}: {str(e)}"
            )

    def list_valid_sheets(self) -> List[str]:
        """Get list of valid sheet names."""
        return list(self.sheets.keys())

    def get_sheet(self, sheet_name: str) -> Optional[pd.DataFrame]:
        """Get specific sheet by name."""
        return self.sheets.get(sheet_name)

    def get_all_sheets(self) -> Dict[str, pd.DataFrame]:
        """Get all loaded sheets."""
        return self.sheets


def parse_excel_to_flows(
    excel_parser: ExcelParser, valid_sheets: List[str]
) -> List[TestFlow]:
    """
    Parses all sheets and groups rows by Test_Name into TestFlow objects.
    Returns a list of TestFlow objects for all sheets.
    """
    flows: List[TestFlow] = []

    for sheet in valid_sheets:
        df = excel_parser.get_sheet(sheet)
        if df is None:
            continue

        test_flows: Dict[str, TestFlow] = {}

        for row_idx, row in df.iterrows():
            test_name = row.get("Test_Name") or f"row_{row_idx}"
            command = row.get("Command")

            # Extract url, method, headers from command if missing
            url = row.get("URL")
            method = row.get("Method")
            headers = row.get("Headers")

            if (
                (not url or pd.isna(url))
                or (not method or pd.isna(method))
                or (not headers or pd.isna(headers))
            ):
                if (
                    command
                    and isinstance(command, str)
                    and command.strip().startswith("curl")
                ):
                    try:
                        tokens = shlex.split(command)

                        # Method
                        if not method or pd.isna(method):
                            if "-X" in tokens:
                                idx = tokens.index("-X")
                                if idx + 1 < len(tokens):
                                    method = tokens[idx + 1]
                            else:
                                method = "GET"

                        # URL
                        if not url or pd.isna(url):
                            url_pat = re.compile(r'"(http[s]?://[^"]+)"')
                            url_match = url_pat.search(command)
                            if url_match:
                                url = url_match.group(1)
                            else:
                                # Try to find the first arg that looks like a URL
                                for t in tokens:
                                    if t.startswith("http://") or t.startswith(
                                        "https://"
                                    ):
                                        url = t
                                        break

                        # Headers
                        if not headers or pd.isna(headers):
                            headers = {}
                            header_pat = re.compile(
                                r"-H\s*'([^']+:[^']+)'|-H\s*\"([^\"]+: [^\"]+)\""
                            )
                            for m in header_pat.finditer(command):
                                h = m.group(1) or m.group(2)
                                if h and ":" in h:
                                    k, v = h.split(":", 1)
                                    headers[k.strip()] = v.strip()
                    except (ValueError, IndexError):
                        # If parsing fails, continue with default values
                        method = method or "GET"
                        headers = headers or {}

            if test_name not in test_flows:
                test_flows[test_name] = TestFlow(sheet, test_name)

            step = TestStep(
                row_idx=row_idx,
                method=method if method else "GET",
                url=url,
                payload=row.get("Request_Payload"),
                headers=headers if headers else {},
                expected_status=row.get("Expected_Status"),
                pattern_match=row.get("Pattern_Match"),
                other_fields=row.to_dict(),
            )
            test_flows[test_name].add_step(step)

        flows.extend(test_flows.values())
    return flows
