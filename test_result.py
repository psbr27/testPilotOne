from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TestResult:
    sheet: str
    row_idx: int
    host: str
    command: str
    output: str
    error: str
    expected_status: Optional[int]
    actual_status: Optional[int]
    pattern_match: Optional[str]
    pattern_found: Optional[bool]
    passed: bool
    fail_reason: Optional[str]
    # Additional fields that are set dynamically
    test_name: Optional[str] = None
    duration: float = 0.0
    method: str = "GET"


class TestStep:
    def __init__(
        self,
        row_idx: int,
        method: str,
        url: str,
        payload: Any,
        headers: Dict,
        expected_status: Any,
        pattern_match: Any,
        other_fields: Dict = None,
    ):
        self.row_idx = row_idx
        self.method = method
        self.url = url
        self.payload = payload
        self.headers = headers
        self.expected_status = expected_status
        self.pattern_match = pattern_match
        self.other_fields = other_fields or {}
        self.result: Optional[TestResult] = (
            None  # Will hold TestResult after execution
        )


class TestFlow:
    def __init__(self, sheet: str, test_name: str):
        self.sheet = sheet
        self.test_name = test_name
        self.steps: List[TestStep] = []
        self.context: Dict[str, Any] = {}  # For storing data between steps

    def add_step(self, step: TestStep):
        self.steps.append(step)
