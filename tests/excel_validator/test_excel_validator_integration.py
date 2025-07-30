"""
Unit tests for Excel Validator Integration module
"""

import unittest
import os
import sys
import tempfile
import pandas as pd
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.testpilot.utils.excel_validator_integration import (
    validate_excel_input,
    add_validation_args,
    get_validation_status_summary
)
from src.testpilot.core.excel_data_validator import ExcelDataValidator


class TestExcelValidatorIntegration(unittest.TestCase):
    """Test cases for Excel Validator Integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_excel = os.path.join(self.temp_dir, 'test.xlsx')
        
        # Create a test Excel file
        test_data = {
            'Test Name': ['Test1', 'Test2'],
            'Response Payload': ['{"valid": "json"}', '{"also": "valid"}'],
            'Pattern Match': ['pattern1', 'pattern2']
        }
        pd.DataFrame(test_data).to_excel(self.test_excel, index=False)
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    # ========== validate_excel_input Tests ==========
    
    def test_validate_excel_input_success(self):
        """Test successful Excel validation"""
        result = validate_excel_input(self.test_excel)
        
        # Should return path to validated file
        self.assertTrue(result.endswith('_validated.xlsx'))
        self.assertTrue(os.path.exists(result))
        
        # Check summary file was created
        summary_file = result.replace('_validated.xlsx', '_validation_summary.txt')
        self.assertTrue(os.path.exists(summary_file))
    
    def test_validate_excel_input_skip_validation(self):
        """Test skipping validation"""
        result = validate_excel_input(self.test_excel, validate_input=False)
        
        # Should return original file path
        self.assertEqual(result, self.test_excel)
        
        # No validated file should be created
        validated_file = self.test_excel.replace('.xlsx', '_validated.xlsx')
        self.assertFalse(os.path.exists(validated_file))
    
    def test_validate_excel_input_file_not_found(self):
        """Test validation with non-existent file"""
        non_existent = os.path.join(self.temp_dir, 'does_not_exist.xlsx')
        
        with self.assertRaises(FileNotFoundError):
            validate_excel_input(non_existent)
    
    def test_validate_excel_input_cached_file(self):
        """Test using cached validated file"""
        # First validation
        result1 = validate_excel_input(self.test_excel)
        self.assertTrue(os.path.exists(result1))
        
        # Get modification time
        mtime1 = os.path.getmtime(result1)
        
        # Second validation should use cache
        with patch('src.testpilot.utils.excel_validator_integration.logger') as mock_logger:
            result2 = validate_excel_input(self.test_excel)
            
            # Should return same file
            self.assertEqual(result1, result2)
            
            # Should not modify the file
            mtime2 = os.path.getmtime(result2)
            self.assertEqual(mtime1, mtime2)
            
            # Check log message about using existing file
            mock_logger.info.assert_any_call(f"Using existing validated file: {result1}")
    
    def test_validate_excel_input_force_validation(self):
        """Test force validation even with cached file"""
        # First validation
        result1 = validate_excel_input(self.test_excel)
        mtime1 = os.path.getmtime(result1)
        
        # Force re-validation
        import time
        time.sleep(0.1)  # Ensure different timestamp
        
        result2 = validate_excel_input(self.test_excel, force_validation=True)
        mtime2 = os.path.getmtime(result2)
        
        # File should be updated
        self.assertGreater(mtime2, mtime1)
    
    @patch('src.testpilot.utils.excel_validator_integration.ExcelDataValidator')
    def test_validate_excel_input_low_validation_rate(self, mock_validator_class):
        """Test handling of low validation rate"""
        # Mock validator to return low validation rate
        mock_validator = MagicMock()
        mock_validator_class.return_value = mock_validator
        
        expected_output_file = self.test_excel.replace('.xlsx', '_validated.xlsx')
        mock_validator.validate_excel_file.return_value = {
            'total_rows': 100,
            'valid_rows': 70,
            'invalid_rows': 30,
            'validation_rate': 70.0,  # Below default threshold of 80%
            'output_file': expected_output_file,
            'summary_file': 'test_summary.txt',
            'accepted_tests': [],
            'rejected_tests': []
        }
        
        with patch('src.testpilot.utils.excel_validator_integration.logger') as mock_logger:
            result = validate_excel_input(self.test_excel)
            
            # Should still return validated file
            self.assertEqual(result, expected_output_file)
            
            # Should log warning about low validation rate
            warning_calls = [call[0][0] for call in mock_logger.warning.call_args_list]
            self.assertTrue(any('Low validation rate' in str(call) for call in warning_calls))
    
    @patch('src.testpilot.utils.excel_validator_integration.ExcelDataValidator')
    def test_validate_excel_input_validation_failure(self, mock_validator_class):
        """Test handling of validation failure"""
        # Mock validator to raise exception
        mock_validator = MagicMock()
        mock_validator_class.return_value = mock_validator
        mock_validator.validate_excel_file.side_effect = Exception("Validation error")
        
        with patch('src.testpilot.utils.excel_validator_integration.logger') as mock_logger:
            result = validate_excel_input(self.test_excel)
            
            # Should fall back to original file
            self.assertEqual(result, self.test_excel)
            
            # Should log error
            mock_logger.error.assert_any_call("Excel validation failed: Validation error")
            mock_logger.error.assert_any_call("Falling back to original file")
    
    # ========== add_validation_args Tests ==========
    
    def test_add_validation_args(self):
        """Test adding validation arguments to parser"""
        parser = argparse.ArgumentParser()
        add_validation_args(parser)
        
        # Parse with all validation arguments
        args = parser.parse_args([
            '--skip-validation',
            '--force-validation',
            '--validation-threshold', '90.0'
        ])
        
        self.assertTrue(args.skip_validation)
        self.assertTrue(args.force_validation)
        self.assertEqual(args.validation_threshold, 90.0)
    
    def test_add_validation_args_defaults(self):
        """Test default values for validation arguments"""
        parser = argparse.ArgumentParser()
        add_validation_args(parser)
        
        # Parse without any validation arguments
        args = parser.parse_args([])
        
        self.assertFalse(args.skip_validation)
        self.assertFalse(args.force_validation)
        self.assertEqual(args.validation_threshold, 80.0)
    
    def test_add_validation_args_help_text(self):
        """Test help text for validation arguments"""
        parser = argparse.ArgumentParser()
        add_validation_args(parser)
        
        help_text = parser.format_help()
        
        # Check that all arguments are in help
        self.assertIn('--skip-validation', help_text)
        self.assertIn('--force-validation', help_text)
        self.assertIn('--validation-threshold', help_text)
        
        # Check group name
        self.assertIn('Excel Validation Options', help_text)
    
    # ========== get_validation_status_summary Tests ==========
    
    def test_get_validation_status_summary_no_validation(self):
        """Test status summary when no validation has been done"""
        status = get_validation_status_summary(self.test_excel)
        
        self.assertEqual(status['input_file'], self.test_excel)
        self.assertFalse(status['validated_file_exists'])
        self.assertFalse(status['summary_file_exists'])
        self.assertTrue(status['needs_validation'])
        
        # Check paths are correct
        self.assertTrue(status['validated_file_path'].endswith('_validated.xlsx'))
        self.assertTrue(status['summary_file_path'].endswith('_validation_summary.txt'))
    
    def test_get_validation_status_summary_after_validation(self):
        """Test status summary after validation"""
        # Run validation first
        validated_file = validate_excel_input(self.test_excel)
        
        # Get status
        status = get_validation_status_summary(self.test_excel)
        
        self.assertTrue(status['validated_file_exists'])
        self.assertTrue(status['summary_file_exists'])
        self.assertFalse(status['needs_validation'])
        self.assertLess(status['validation_age_seconds'], 0)  # Validated is newer
    
    def test_get_validation_status_summary_outdated_validation(self):
        """Test status when validated file is outdated"""
        # Run validation
        validated_file = validate_excel_input(self.test_excel)
        
        # Touch the original file to make it newer
        import time
        time.sleep(0.1)
        Path(self.test_excel).touch()
        
        # Get status
        status = get_validation_status_summary(self.test_excel)
        
        self.assertTrue(status['validated_file_exists'])
        self.assertTrue(status['needs_validation'])
        self.assertGreater(status['validation_age_seconds'], 0)  # Original is newer
    
    # ========== Integration Tests ==========
    
    def test_integration_with_invalid_data(self):
        """Test integration with Excel containing invalid data"""
        # Create Excel with invalid JSON
        test_data = {
            'Test Name': ['Valid', 'Invalid1', 'Invalid2'],
            'Response Payload': [
                '{"valid": "json"}',
                '{invalid json',
                '{another: invalid}'
            ],
            'Pattern Match': ['pattern1', 'pattern2', 'pattern3']
        }
        
        invalid_excel = os.path.join(self.temp_dir, 'invalid.xlsx')
        pd.DataFrame(test_data).to_excel(invalid_excel, index=False)
        
        # Validate
        result = validate_excel_input(invalid_excel)
        
        # Should create validated file
        self.assertTrue(os.path.exists(result))
        
        # Read validated file to check corrections
        df_validated = pd.read_excel(result)
        
        # First row should remain valid
        self.assertEqual(df_validated.iloc[0]['Response Payload'], '{"valid": "json"}')
        
        # Invalid rows should be preserved (not corrected if unfixable)
        self.assertEqual(df_validated.iloc[1]['Response Payload'], '{invalid json')
    
    def test_integration_with_multiple_sheets(self):
        """Test integration with multi-sheet Excel"""
        # Create multi-sheet Excel
        multi_excel = os.path.join(self.temp_dir, 'multi_sheet.xlsx')
        
        with pd.ExcelWriter(multi_excel) as writer:
            pd.DataFrame({
                'Test Name': ['Sheet1_Test1'],
                'Response Payload': ['{"sheet1": "data"}'],
                'Pattern Match': ['pattern1']
            }).to_excel(writer, sheet_name='Sheet1', index=False)
            
            pd.DataFrame({
                'Test Name': ['Sheet2_Test1'],
                'Response Payload': ['{"sheet2": "data"}'],
                'Pattern Match': ['pattern2']
            }).to_excel(writer, sheet_name='Sheet2', index=False)
        
        # Validate
        result = validate_excel_input(multi_excel)
        
        # Check validated file has both sheets
        xl_file = pd.ExcelFile(result)
        self.assertIn('Sheet1', xl_file.sheet_names)
        self.assertIn('Sheet2', xl_file.sheet_names)
    
    def test_integration_error_handling(self):
        """Test error handling in integration"""
        # Test with corrupted Excel file
        corrupted_file = os.path.join(self.temp_dir, 'corrupted.xlsx')
        with open(corrupted_file, 'w') as f:
            f.write('This is not an Excel file')
        
        # Should fall back to original file
        with patch('src.testpilot.utils.excel_validator_integration.logger'):
            result = validate_excel_input(corrupted_file)
            self.assertEqual(result, corrupted_file)


class TestValidationThreshold(unittest.TestCase):
    """Test validation threshold functionality"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @patch('src.testpilot.utils.excel_validator_integration.ExcelDataValidator')
    def test_threshold_warning(self, mock_validator_class):
        """Test warning when validation rate below threshold"""
        mock_validator = MagicMock()
        mock_validator_class.return_value = mock_validator
        
        # Set validation rate to 75% (below default 80%)
        mock_validator.validate_excel_file.return_value = {
            'total_rows': 100,
            'valid_rows': 75,
            'invalid_rows': 25,
            'validation_rate': 75.0,
            'output_file': 'output.xlsx',
            'summary_file': 'summary.txt',
            'accepted_tests': [],
            'rejected_tests': []
        }
        
        test_file = os.path.join(self.temp_dir, 'test.xlsx')
        pd.DataFrame({'A': [1]}).to_excel(test_file, index=False)
        
        with patch('src.testpilot.utils.excel_validator_integration.logger') as mock_logger:
            validate_excel_input(test_file)
            
            # Should warn about low validation rate
            warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
            self.assertTrue(any('75.0%' in call and 'below threshold' in call for call in warning_calls))


if __name__ == '__main__':
    unittest.main(verbosity=2)