"""
Additional tests to achieve 100% code coverage
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.testpilot.core.excel_data_validator import ExcelDataValidator


class TestCoverageCompletion(unittest.TestCase):
    """Tests to cover remaining uncovered lines"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.validator = ExcelDataValidator()
    
    def test_invalid_json_array_standardization(self):
        """Test JSON array standardization error handling (line 202-203)"""
        # This should trigger the JSONDecodeError in _standardize_json_array
        # by creating an invalid array that passes initial detection
        
        # First, let's test the private method directly
        result = self.validator._standardize_json_array('[invalid json')
        self.assertEqual(result, '[invalid json')  # Should return original on error
        
        # Also test with valid array to ensure normal path works
        result = self.validator._standardize_json_array('["valid", "array"]')
        self.assertEqual(result, '["valid","array"]')
    
    def test_invalid_json_object_standardization(self):
        """Test JSON object standardization error handling (line 194-195)"""
        # Test the private method directly
        result = self.validator._standardize_json_object('{invalid json')
        self.assertEqual(result, '{invalid json')  # Should return original on error
        
        # Also test with valid object
        result = self.validator._standardize_json_object('{"valid": "object"}')
        self.assertEqual(result, '{"valid":"object"}')
    
    def test_invalid_json_array_detection(self):
        """Test JSON array detection error handling (line 157-158)"""
        # This should trigger the JSONDecodeError in _is_json_array_pattern
        # Need a pattern that starts with [ and ends with ] but is invalid JSON
        result = self.validator._is_json_array_pattern('[invalid, json, array]')
        self.assertFalse(result)
        
        # Another invalid case that looks like array
        result = self.validator._is_json_array_pattern('[1, 2, invalid]')
        self.assertFalse(result)
        
        # Test valid array detection
        result = self.validator._is_json_array_pattern('["valid"]')
        self.assertTrue(result)
    
    def test_key_value_pattern_fallback(self):
        """Test key-value pattern fallback case (line 228)"""
        # Test pattern that doesn't contain : or = (fallback case)
        result = self.validator._standardize_key_value('no_separator_pattern')
        self.assertEqual(result, 'no_separator_pattern')
        
        # Test patterns with separators work normally
        result = self.validator._standardize_key_value('key:value')
        self.assertEqual(result, 'key:value')
        
        result = self.validator._standardize_key_value('key=value')
        self.assertEqual(result, 'key:value')  # Normalized to colon


if __name__ == '__main__':
    unittest.main(verbosity=2)