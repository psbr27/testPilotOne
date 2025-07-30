"""
Excel Data Validator for TestPilot
Validates and auto-corrects Response Payload and Pattern Match columns in Excel files.
"""

import json
import re
import os
from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd
from pathlib import Path


class ExcelDataValidator:
    """
    Validates and auto-corrects Excel test data for TestPilot.
    
    Handles two main columns:
    1. Response Payload - JSON validation and auto-correction
    2. Pattern Match - Pattern categorization and standardization
    """
    
    def __init__(self):
        self.accepted_tests = []
        self.rejected_tests = []
        
        # Pattern categories based on enhanced_response_validator.py analysis
        self.pattern_categories = {
            'SUBSTRING': 'Simple substring pattern',
            'KEY_VALUE': 'Key-value pattern (key:value or key=value)',
            'JSON_OBJECT': 'JSON object pattern',
            'JSON_ARRAY': 'JSON array pattern', 
            'REGEX': 'Regular expression pattern',
            'JSONPATH': 'JSONPath expression pattern',
            'MULTI_KEY_VALUE': 'Multiple key-value pairs',
            'GENERAL': 'General text pattern'
        }
    
    def load_excel_file(self, file_path: str) -> Dict[str, pd.DataFrame]:
        """Load Excel file and return dictionary of sheet DataFrames."""
        try:
            excel_data = pd.read_excel(file_path, sheet_name=None, dtype=str)
            print(f"Loaded Excel file with {len(excel_data)} sheets")
            return excel_data
        except Exception as e:
            raise ValueError(f"Failed to load Excel file: {e}")
    
    def validate_json_payload(self, payload: Any) -> Tuple[bool, str, Optional[str]]:
        """
        Validate and auto-correct JSON payload.
        
        Returns:
            (is_valid, corrected_payload, error_message)
        """
        if pd.isna(payload) or payload == '':
            return True, '', None
            
        payload_str = str(payload).strip()
        
        # If already valid JSON, return as-is
        try:
            json.loads(payload_str)
            return True, payload_str, None
        except json.JSONDecodeError:
            pass
        
        # Try auto-corrections
        corrected = self._apply_json_corrections(payload_str)
        
        # Test if corrections worked
        try:
            json.loads(corrected)
            return True, corrected, None
        except json.JSONDecodeError as e:
            return False, payload_str, f"Invalid JSON: {str(e)}"
    
    def _apply_json_corrections(self, payload: str) -> str:
        """Apply common JSON auto-corrections."""
        corrected = payload
        
        # Fix single quotes to double quotes
        corrected = re.sub(r"'([^']*)':", r'"\1":', corrected)
        corrected = re.sub(r":\s*'([^']*)'", r': "\1"', corrected)
        
        # Remove trailing commas
        corrected = re.sub(r',\s*}', '}', corrected)
        corrected = re.sub(r',\s*]', ']', corrected)
        
        # Fix unquoted keys
        corrected = re.sub(r'(\w+):', r'"\1":', corrected)
        
        # Fix Excel line break encoding
        corrected = corrected.replace('_x000D_', '')
        
        return corrected
    
    def categorize_pattern(self, pattern: Any) -> Tuple[str, str]:
        """
        Categorize and standardize pattern match string.
        
        Returns:
            (category, standardized_pattern)
        """
        if pd.isna(pattern) or pattern == '':
            return 'GENERAL', ''
            
        pattern_str = str(pattern).strip()
        
        # Clean Excel artifacts
        pattern_str = pattern_str.replace('_x000D_', '').strip()
        
        # 1. Check for JSON Object pattern
        if self._is_json_object_pattern(pattern_str):
            return 'JSON_OBJECT', self._standardize_json_object(pattern_str)
        
        # 2. Check for JSON Array pattern
        if self._is_json_array_pattern(pattern_str):
            return 'JSON_ARRAY', self._standardize_json_array(pattern_str)
        
        # 3. Check for Multi Key-Value pattern (comma-separated)
        if self._is_multi_key_value_pattern(pattern_str):
            return 'MULTI_KEY_VALUE', self._standardize_multi_key_value(pattern_str)
        
        # 4. Check for Single Key-Value pattern
        if self._is_key_value_pattern(pattern_str):
            return 'KEY_VALUE', self._standardize_key_value(pattern_str)
        
        # 5. Check for JSONPath pattern
        if self._is_jsonpath_pattern(pattern_str):
            return 'JSONPATH', pattern_str
        
        # 6. Check for Regex pattern (heuristic)
        if self._is_regex_pattern(pattern_str):
            return 'REGEX', pattern_str
        
        # 7. Default to substring/general pattern
        return 'SUBSTRING', pattern_str
    
    def _is_json_object_pattern(self, pattern: str) -> bool:
        """Check if pattern is a JSON object."""
        pattern = pattern.strip()
        if pattern.startswith('{') and pattern.endswith('}'):
            try:
                json.loads(pattern)
                return True
            except json.JSONDecodeError:
                pass
        return False
    
    def _is_json_array_pattern(self, pattern: str) -> bool:
        """Check if pattern is a JSON array."""
        pattern = pattern.strip()
        if pattern.startswith('[') and pattern.endswith(']'):
            try:
                json.loads(pattern)
                return True
            except json.JSONDecodeError:
                pass
        return False
    
    def _is_multi_key_value_pattern(self, pattern: str) -> bool:
        """Check if pattern contains multiple key-value pairs."""
        # Look for comma-separated key-value pairs
        if ',' in pattern and (':' in pattern or '=' in pattern):
            parts = pattern.split(',')
            valid_pairs = 0
            for part in parts:
                part = part.strip()
                if ':' in part or '=' in part:
                    valid_pairs += 1
            return valid_pairs >= 2
        return False
    
    def _is_key_value_pattern(self, pattern: str) -> bool:
        """Check if pattern is a single key-value pair."""
        return (':' in pattern or '=' in pattern) and not self._is_multi_key_value_pattern(pattern)
    
    def _is_jsonpath_pattern(self, pattern: str) -> bool:
        """Check if pattern looks like JSONPath."""
        jsonpath_indicators = ['$', '..', '[*]', '[?', '@']
        return any(indicator in pattern for indicator in jsonpath_indicators)
    
    def _is_regex_pattern(self, pattern: str) -> bool:
        """Heuristic check for regex patterns."""
        regex_indicators = ['.*', '.+', '[', ']', '(', ')', '|', '^', '$', '\\d', '\\w', '\\s']
        indicator_count = sum(1 for indicator in regex_indicators if indicator in pattern)
        return indicator_count >= 2
    
    def _standardize_json_object(self, pattern: str) -> str:
        """Standardize JSON object pattern."""
        try:
            parsed = json.loads(pattern)
            return json.dumps(parsed, separators=(',', ':'), ensure_ascii=False)
        except json.JSONDecodeError:
            return pattern
    
    def _standardize_json_array(self, pattern: str) -> str:
        """Standardize JSON array pattern."""
        try:
            parsed = json.loads(pattern)
            return json.dumps(parsed, separators=(',', ':'), ensure_ascii=False)
        except json.JSONDecodeError:
            return pattern
    
    def _standardize_multi_key_value(self, pattern: str) -> str:
        """Standardize multi key-value pattern."""
        # Parse and normalize comma-separated key-value pairs
        pairs = []
        parts = pattern.split(',')
        for part in parts:
            part = part.strip()
            if ':' in part:
                key, val = part.split(':', 1)
                pairs.append(f'{key.strip()}:{val.strip()}')
            elif '=' in part:
                key, val = part.split('=', 1)
                pairs.append(f'{key.strip()}:{val.strip()}')  # Normalize to colon
        return ','.join(pairs)
    
    def _standardize_key_value(self, pattern: str) -> str:
        """Standardize single key-value pattern."""
        if ':' in pattern:
            key, val = pattern.split(':', 1)
            return f'{key.strip()}:{val.strip()}'
        elif '=' in pattern:
            key, val = pattern.split('=', 1)
            return f'{key.strip()}:{val.strip()}'  # Normalize to colon
        return pattern
    
    def validate_row(self, row: pd.Series, sheet_name: str, row_idx: int, 
                    response_payload_col: str = 'Response Payload',
                    pattern_match_col: str = 'Pattern Match',
                    test_name_col: str = 'Test Name') -> Tuple[bool, pd.Series]:
        """
        Validate and correct a single row.
        
        Returns:
            (is_valid, corrected_row)
        """
        corrected_row = row.copy()
        is_valid = True
        
        # Validate Response Payload
        if response_payload_col in row:
            payload_valid, corrected_payload, payload_error = self.validate_json_payload(
                row[response_payload_col]
            )
            if payload_valid:
                corrected_row[response_payload_col] = corrected_payload
            else:
                is_valid = False
                print(f"Row {row_idx} in {sheet_name}: {payload_error}")
        
        # Validate and categorize Pattern Match
        if pattern_match_col in row:
            category, standardized_pattern = self.categorize_pattern(row[pattern_match_col])
            corrected_row[pattern_match_col] = standardized_pattern
        
        return is_valid, corrected_row
    
    def validate_excel_file(self, input_file: str, output_file: str = None, 
                           summary_file: str = None) -> Dict[str, Any]:
        """
        Validate entire Excel file and create corrected version.
        
        Args:
            input_file: Path to input Excel file
            output_file: Path for validated output file (default: input_validated.xlsx)
            summary_file: Path for summary text file (default: validation_summary.txt)
        
        Returns:
            Dictionary with validation results
        """
        if output_file is None:
            base_path = Path(input_file).parent
            stem = Path(input_file).stem
            output_file = base_path / f"{stem}_validated.xlsx"
        
        if summary_file is None:
            base_path = Path(input_file).parent
            stem = Path(input_file).stem
            summary_file = base_path / f"{stem}_validation_summary.txt"
        
        # Load Excel data
        excel_data = self.load_excel_file(input_file)
        validated_data = {}
        
        total_rows = 0
        valid_rows = 0
        
        # Process each sheet
        for sheet_name, df in excel_data.items():
            print(f"Processing sheet: {sheet_name}")
            validated_df = df.copy()
            sheet_valid_rows = 0
            
            for idx, row in df.iterrows():
                total_rows += 1
                is_valid, corrected_row = self.validate_row(row, sheet_name, idx)
                
                # Update the row in the DataFrame
                for col in corrected_row.index:
                    validated_df.at[idx, col] = corrected_row[col]
                
                if is_valid:
                    valid_rows += 1
                    sheet_valid_rows += 1
                    test_name = row.get('Test Name', f'Row_{idx}')
                    self.accepted_tests.append({
                        'sheet': sheet_name,
                        'test_name': test_name,
                        'row_index': idx
                    })
                else:
                    test_name = row.get('Test Name', f'Row_{idx}')
                    self.rejected_tests.append({
                        'sheet': sheet_name,
                        'test_name': test_name,
                        'row_index': idx
                    })
            
            validated_data[sheet_name] = validated_df
            print(f"Sheet {sheet_name}: {sheet_valid_rows}/{len(df)} rows valid")
        
        # Save validated Excel file with formatting
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            for sheet_name, df in validated_data.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Apply wrap text formatting to all columns
                worksheet = writer.sheets[sheet_name]
                self._apply_wrap_text_formatting(worksheet, df)
        
        # Create summary report
        self._create_summary_report(summary_file, total_rows, valid_rows)
        
        results = {
            'total_rows': total_rows,
            'valid_rows': valid_rows,
            'invalid_rows': total_rows - valid_rows,
            'validation_rate': (valid_rows / total_rows) * 100 if total_rows > 0 else 0,
            'output_file': str(output_file),
            'summary_file': str(summary_file),
            'accepted_tests': self.accepted_tests.copy(),
            'rejected_tests': self.rejected_tests.copy()
        }
        
        print(f"Validation complete: {valid_rows}/{total_rows} rows valid ({results['validation_rate']:.1f}%)")
        print(f"Validated file saved: {output_file}")
        print(f"Summary saved: {summary_file}")
        
        return results
    
    def _create_summary_report(self, summary_file: str, total_rows: int, valid_rows: int):
        """Create summary text file with validation results."""
        with open(summary_file, 'w') as f:
            f.write("Excel Data Validation Summary\n")
            f.write("=" * 40 + "\n\n")
            
            f.write(f"Total rows processed: {total_rows}\n")
            f.write(f"Valid rows: {valid_rows}\n")
            f.write(f"Invalid rows: {total_rows - valid_rows}\n")
            f.write(f"Validation rate: {(valid_rows/total_rows)*100 if total_rows > 0 else 0:.1f}%\n\n")
            
            f.write("ACCEPTED TEST CASES:\n")
            f.write("-" * 20 + "\n")
            for test in self.accepted_tests:
                f.write(f"Sheet: {test['sheet']}, Test: {test['test_name']}, Row: {test['row_index']}\n")
            
            if self.rejected_tests:
                f.write(f"\nREJECTED TEST CASES ({len(self.rejected_tests)}):\n")
                f.write("-" * 20 + "\n")
                for test in self.rejected_tests:
                    f.write(f"Sheet: {test['sheet']}, Test: {test['test_name']}, Row: {test['row_index']}\n")
            
            f.write(f"\nPattern Categories Identified:\n")
            f.write("-" * 30 + "\n")
            for category, description in self.pattern_categories.items():
                f.write(f"{category}: {description}\n")
    
    def _apply_wrap_text_formatting(self, worksheet, df):
        """Apply wrap text formatting to all columns in the worksheet."""
        from openpyxl.styles import Alignment
        
        # Apply wrap text to all cells
        for row in worksheet.iter_rows(min_row=1, max_row=len(df) + 1, 
                                     min_col=1, max_col=len(df.columns)):
            for cell in row:
                cell.alignment = Alignment(wrap_text=True, vertical='top')
        
        # Auto-adjust column widths (with reasonable limits)
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            
            for cell in column:
                if cell.value:
                    # Calculate approximate width needed
                    cell_length = len(str(cell.value))
                    if cell_length > max_length:
                        max_length = cell_length
            
            # Set column width with reasonable limits
            adjusted_width = min(max(max_length + 2, 15), 50)  # Min 15, Max 50
            worksheet.column_dimensions[column_letter].width = adjusted_width