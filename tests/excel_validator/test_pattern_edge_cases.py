"""
Edge case tests for pattern categorization
Tests complex, ambiguous, and boundary patterns
"""

import unittest
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.testpilot.core.excel_data_validator import ExcelDataValidator


class TestPatternEdgeCases(unittest.TestCase):
    """Test edge cases and complex patterns for categorization"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.validator = ExcelDataValidator()
    
    # ========== Complex Key-Value Patterns ==========
    
    def test_key_value_with_special_characters(self):
        """Test key-value patterns with special characters"""
        test_cases = [
            # Colons in values
            ('url:http://example.com', 'KEY_VALUE', 'url:http://example.com'),
            ('time:12:30:45', 'KEY_VALUE', 'time:12:30:45'),
            
            # Equals in values  
            ('formula:x=y+z', 'KEY_VALUE', 'formula:x=y+z'),
            
            # Quotes in values
            ('message:"Hello, World!"', 'KEY_VALUE', 'message:"Hello, World!"'),
            ("name:'John Doe'", 'KEY_VALUE', "name:'John Doe'"),
            
            # Mixed quotes
            ('data:"key=\'value\'"', 'KEY_VALUE', 'data:"key=\'value\'"'),
            
            # Spaces in keys/values
            ('user name:John Doe', 'KEY_VALUE', 'user name:John Doe'),
            ('key:value with spaces', 'KEY_VALUE', 'key:value with spaces'),
            
            # Unicode characters
            ('name:José', 'KEY_VALUE', 'name:José'),
            ('emoji:😀', 'KEY_VALUE', 'emoji:😀'),
            ('chinese:你好', 'KEY_VALUE', 'chinese:你好'),
        ]
        
        for pattern, expected_category, expected_standard in test_cases:
            with self.subTest(pattern=pattern):
                category, standardized = self.validator.categorize_pattern(pattern)
                self.assertEqual(category, expected_category)
                self.assertEqual(standardized, expected_standard)
    
    def test_multi_key_value_edge_cases(self):
        """Test multi key-value patterns with edge cases"""
        test_cases = [
            # Commas in quoted values
            ('key1:"value,with,comma",key2:value2', 'MULTI_KEY_VALUE', 
             'key1:"value,with,comma",key2:value2'),
            
            # Mixed separators
            ('a:1,b=2,c:3,d=4', 'MULTI_KEY_VALUE', 'a:1,b:2,c:3,d:4'),
            
            # Nested structures in values
            ('data:{nested},other:value', 'MULTI_KEY_VALUE', 'data:{nested},other:value'),
            
            # Empty values
            ('key1:,key2:value', 'MULTI_KEY_VALUE', 'key1:,key2:value'),
            ('key1:value,key2:', 'MULTI_KEY_VALUE', 'key1:value,key2:'),
            
            # Many pairs
            ('a:1,b:2,c:3,d:4,e:5,f:6', 'MULTI_KEY_VALUE', 'a:1,b:2,c:3,d:4,e:5,f:6'),
        ]
        
        for pattern, expected_category, expected_standard in test_cases:
            with self.subTest(pattern=pattern):
                category, standardized = self.validator.categorize_pattern(pattern)
                self.assertEqual(category, expected_category)
                self.assertEqual(standardized, expected_standard)
    
    # ========== Ambiguous JSON Patterns ==========
    
    def test_invalid_json_patterns(self):
        """Test patterns that look like JSON but aren't valid"""
        test_cases = [
            # Almost JSON objects
            ('{invalid}', 'SUBSTRING', '{invalid}'),
            ('{"key": undefined}', 'SUBSTRING', '{"key": undefined}'),
            ('{"missing": "quote}', 'SUBSTRING', '{"missing": "quote}'),
            ('{key: value}', 'SUBSTRING', '{key: value}'),  # Unquoted key
            
            # Almost JSON arrays
            ('[1, 2, 3,]', 'SUBSTRING', '[1, 2, 3,]'),  # Trailing comma
            ('[invalid]', 'SUBSTRING', '[invalid]'),
            ('["unclosed', 'SUBSTRING', '["unclosed'),
            
            # Partial JSON
            ('{"partial":', 'SUBSTRING', '{"partial":'),
            ('["incomplete",', 'SUBSTRING', '["incomplete",'),
        ]
        
        for pattern, expected_category, expected_standard in test_cases:
            with self.subTest(pattern=pattern):
                category, standardized = self.validator.categorize_pattern(pattern)
                self.assertEqual(category, expected_category)
                self.assertEqual(standardized, expected_standard)
    
    def test_nested_json_patterns(self):
        """Test deeply nested JSON patterns"""
        test_cases = [
            # Deep nesting
            ('{"a":{"b":{"c":{"d":"value"}}}}', 'JSON_OBJECT', 
             '{"a":{"b":{"c":{"d":"value"}}}}'),
            
            # Arrays of objects
            ('[{"id":1},{"id":2},{"id":3}]', 'JSON_ARRAY',
             '[{"id":1},{"id":2},{"id":3}]'),
            
            # Mixed nesting
            ('{"array":[{"nested":true}]}', 'JSON_OBJECT',
             '{"array":[{"nested":true}]}'),
            
            # Large JSON (should still work)
            ('{"a":"' + 'x'*1000 + '"}', 'JSON_OBJECT',
             '{"a":"' + 'x'*1000 + '"}'),
        ]
        
        for pattern, expected_category, expected_standard in test_cases:
            with self.subTest(pattern=pattern[:50] + '...'):  # Truncate for display
                category, standardized = self.validator.categorize_pattern(pattern)
                self.assertEqual(category, expected_category)
                self.assertEqual(standardized, expected_standard)
    
    # ========== Complex JSONPath Patterns ==========
    
    def test_jsonpath_edge_cases(self):
        """Test complex JSONPath expressions"""
        test_cases = [
            # Complex filters
            ('$.items[?(@.price < 10 && @.available == true)]', 'JSONPATH'),
            ('$..book[?(@.isbn)]', 'JSONPATH'),
            
            # Array slicing
            ('$.items[0:5]', 'JSONPATH'),
            ('$.items[-1]', 'JSONPATH'),
            
            # Wildcards
            ('$.*', 'JSONPATH'),
            ('$.store..price', 'JSONPATH'),
            
            # Complex paths
            ('$.data[*].users[?(@.age >= 18)].name', 'JSONPATH'),
            
            # Script expressions (some JSONPath implementations)
            ('$.items[(@.length-1)]', 'JSONPATH'),
        ]
        
        for pattern in test_cases:
            with self.subTest(pattern=pattern):
                category, standardized = self.validator.categorize_pattern(pattern)
                self.assertEqual(category, 'JSONPATH')
                self.assertEqual(standardized, pattern)
    
    # ========== Regex Pattern Edge Cases ==========
    
    def test_regex_vs_substring_ambiguity(self):
        """Test patterns that could be regex or substring"""
        test_cases = [
            # Clear regex patterns
            ('^start.*end$', 'REGEX'),
            ('\\d{3}-\\d{3}-\\d{4}', 'REGEX'),
            ('[A-Za-z]+@[A-Za-z]+\\.[A-Za-z]+', 'REGEX'),
            
            # Ambiguous - treated as substring (not enough regex indicators)
            ('test.com', 'SUBSTRING'),  # Single dot
            ('hello*', 'SUBSTRING'),  # Single asterisk
            ('(test)', 'SUBSTRING'),  # Just parentheses
            
            # More complex patterns that should be regex
            ('test.*\\.com', 'REGEX'),
            ('(option1|option2|option3)', 'REGEX'),
            ('[0-9]+', 'REGEX'),
        ]
        
        for pattern, expected_category in test_cases:
            with self.subTest(pattern=pattern):
                category, _ = self.validator.categorize_pattern(pattern)
                self.assertEqual(category, expected_category)
    
    # ========== Boundary and Special Cases ==========
    
    def test_extremely_long_patterns(self):
        """Test handling of very long patterns"""
        # Very long substring
        long_text = 'a' * 10000
        category, standardized = self.validator.categorize_pattern(long_text)
        self.assertEqual(category, 'SUBSTRING')
        self.assertEqual(len(standardized), 10000)
        
        # Very long key-value
        long_key_value = f"key:{'x' * 5000}"
        category, standardized = self.validator.categorize_pattern(long_key_value)
        self.assertEqual(category, 'KEY_VALUE')
        
        # Very long JSON
        long_json = '{"data":"' + 'x' * 5000 + '"}'
        category, standardized = self.validator.categorize_pattern(long_json)
        self.assertEqual(category, 'JSON_OBJECT')
    
    def test_whitespace_handling(self):
        """Test patterns with various whitespace"""
        test_cases = [
            # Leading/trailing spaces
            ('  pattern  ', 'SUBSTRING', 'pattern'),
            ('  key:value  ', 'KEY_VALUE', 'key:value'),
            
            # Tabs and newlines
            ('key:\tvalue', 'KEY_VALUE', 'key:\tvalue'),
            ('line1\nline2', 'SUBSTRING', 'line1\nline2'),
            
            # Multiple spaces
            ('key  :  value', 'KEY_VALUE', 'key:value'),
            ('k1  :  v1  ,  k2  :  v2', 'MULTI_KEY_VALUE', 'k1:v1,k2:v2'),
            
            # Whitespace-only
            ('   ', 'GENERAL', ''),
            ('\t\n', 'GENERAL', ''),
        ]
        
        for pattern, expected_category, expected_standard in test_cases:
            with self.subTest(pattern=repr(pattern)):
                category, standardized = self.validator.categorize_pattern(pattern)
                self.assertEqual(category, expected_category)
                self.assertEqual(standardized, expected_standard)
    
    def test_special_separator_conflicts(self):
        """Test patterns with conflicting separators"""
        test_cases = [
            # URL-like patterns (contains : but not key-value)
            ('http://example.com', 'SUBSTRING', 'http://example.com'),
            ('https://api.example.com:8080/path', 'SUBSTRING', 'https://api.example.com:8080/path'),
            
            # File paths
            ('C:\\Users\\test.txt', 'SUBSTRING', 'C:\\Users\\test.txt'),
            ('/home/user/file:name.txt', 'SUBSTRING', '/home/user/file:name.txt'),
            
            # Time formats (multiple colons)
            ('12:30:45', 'SUBSTRING', '12:30:45'),
            ('2024-01-01T12:30:45Z', 'SUBSTRING', '2024-01-01T12:30:45Z'),
            
            # Math expressions
            ('x=y+z', 'KEY_VALUE', 'x:y+z'),  # Single = treated as key-value
            ('a=1,b=2+3', 'MULTI_KEY_VALUE', 'a:1,b:2+3'),
        ]
        
        for pattern, expected_category, expected_standard in test_cases:
            with self.subTest(pattern=pattern):
                category, standardized = self.validator.categorize_pattern(pattern)
                self.assertEqual(category, expected_category)
                self.assertEqual(standardized, expected_standard)
    
    def test_mixed_content_patterns(self):
        """Test patterns that mix different types"""
        test_cases = [
            # JSON-like but with regex
            ('{"pattern": ".*test.*"}', 'JSON_OBJECT', '{"pattern":".*test.*"}'),
            
            # Key-value with JSON value
            ('data:{"nested":"json"}', 'KEY_VALUE', 'data:{"nested":"json"}'),
            
            # JSONPath in a string
            ('Find $.users[*].name in response', 'SUBSTRING', 'Find $.users[*].name in response'),
            
            # Multiple patterns in one
            ('status:200 and body:{"success":true}', 'SUBSTRING', 
             'status:200 and body:{"success":true}'),
        ]
        
        for pattern, expected_category, expected_standard in test_cases:
            with self.subTest(pattern=pattern):
                category, standardized = self.validator.categorize_pattern(pattern)
                self.assertEqual(category, expected_category)
                self.assertEqual(standardized, expected_standard)
    
    def test_encoding_edge_cases(self):
        """Test patterns with various encodings"""
        test_cases = [
            # HTML entities
            ('&lt;tag&gt;', 'SUBSTRING', '&lt;tag&gt;'),
            
            # URL encoding
            ('key:value%20with%20spaces', 'KEY_VALUE', 'key:value%20with%20spaces'),
            
            # Escaped characters
            ('line1\\nline2', 'SUBSTRING', 'line1\\nline2'),
            ('key:\\"quoted\\"', 'KEY_VALUE', 'key:\\"quoted\\"'),
            
            # Mixed encodings
            ('{"html":"&lt;div&gt;","url":"test%20value"}', 'JSON_OBJECT',
             '{"html":"&lt;div&gt;","url":"test%20value"}'),
        ]
        
        for pattern, expected_category, expected_standard in test_cases:
            with self.subTest(pattern=pattern):
                category, standardized = self.validator.categorize_pattern(pattern)
                self.assertEqual(category, expected_category)
                self.assertEqual(standardized, expected_standard)
    
    def test_malformed_patterns_recovery(self):
        """Test recovery from malformed patterns"""
        test_cases = [
            # Almost valid patterns
            ('key:', 'KEY_VALUE', 'key:'),  # Missing value
            (':value', 'SUBSTRING', ':value'),  # Missing key
            ('key1:val1,', 'KEY_VALUE', 'key1:val1,'),  # Trailing comma but only one pair
            (',key:value', 'SUBSTRING', ',key:value'),  # Leading comma
            
            # Broken JSON attempts
            ('{]', 'SUBSTRING', '{]'),  # Mismatched brackets
            ('}{', 'SUBSTRING', '}{'),  # Reversed brackets
            
            # Partial patterns
            ('$.', 'JSONPATH', '$.'),  # Minimal JSONPath
            ('.*', 'SUBSTRING', '.*'),  # Could be regex but too simple
        ]
        
        for pattern, expected_category, expected_standard in test_cases:
            with self.subTest(pattern=pattern):
                category, standardized = self.validator.categorize_pattern(pattern)
                self.assertEqual(category, expected_category)
                self.assertEqual(standardized, expected_standard)


class TestJSONAutoCorrectionEdgeCases(unittest.TestCase):
    """Test edge cases for JSON auto-correction"""
    
    def setUp(self):
        self.validator = ExcelDataValidator()
    
    def test_complex_json_corrections(self):
        """Test correction of complex JSON issues"""
        test_cases = [
            # Nested single quotes
            (
                "{'outer': {'inner': 'value'}}",
                '{"outer": {"inner": "value"}}'
            ),
            
            # Multiple trailing commas
            (
                '{"a": 1, "b": {"c": 2,}, "d": 3,}',
                '{"a": 1, "b": {"c": 2}, "d": 3}'
            ),
            
            # Mixed quote styles
            (
                '{"key1": \'value1\', "key2": "value2"}',
                '{"key1": "value1", "key2": "value2"}'
            ),
            
            # Unquoted numeric keys
            (
                '{1: "one", 2: "two"}',
                '{"1": "one", "2": "two"}'
            ),
            
            # Boolean and null values with quotes
            (
                "{'bool': true, 'null': null}",
                '{"bool": true, "null": null}'
            ),
        ]
        
        for invalid_json, expected_json in test_cases:
            with self.subTest(invalid=invalid_json):
                is_valid, corrected, error = self.validator.validate_json_payload(invalid_json)
                self.assertTrue(is_valid)
                # Compare parsed objects to ignore formatting differences
                self.assertEqual(
                    json.loads(corrected),
                    json.loads(expected_json)
                )
    
    def test_uncorrectable_json(self):
        """Test JSON that cannot be auto-corrected"""
        test_cases = [
            # Syntax errors
            '{"key": "value" "key2": "value2"}',  # Missing comma
            '{"key": }',  # Missing value
            '{: "value"}',  # Missing key
            '{"key" "value"}',  # Missing colon
            
            # Invalid values
            '{"key": undefined}',
            '{"key": NaN}',
            '{"key": Infinity}',
            
            # Structural issues
            '{{{{',
            ']]]]',
            '{[}]',
        ]
        
        for pattern in test_cases:
            with self.subTest(pattern=pattern):
                is_valid, corrected, error = self.validator.validate_json_payload(pattern)
                self.assertFalse(is_valid)
                self.assertIn("Invalid JSON", error)


if __name__ == '__main__':
    unittest.main(verbosity=2)