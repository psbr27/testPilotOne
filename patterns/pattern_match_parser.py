import pandas as pd
import json
from typing import Dict, List, Any
from pathlib import Path

class PatternMatchParser:
    def __init__(self, excel_file_path: str):
        """
        Initialize the parser with the Excel file path.
        
        Args:
            excel_file_path (str): Path to the Excel file
        """
        self.excel_file_path = Path(excel_file_path)
        self.workbook_data = {}
        self.pattern_match_data = {}
        
    def load_workbook(self) -> None:
        """Load all sheets from the Excel workbook."""
        try:
            # Read all sheets at once
            self.workbook_data = pd.read_excel(
                self.excel_file_path, 
                sheet_name=None,  # Load all sheets
                engine='openpyxl'
            )
            print(f"Successfully loaded {len(self.workbook_data)} sheets")
        except Exception as e:
            print(f"Error loading workbook: {e}")
            raise
    
    def find_pattern_match_columns(self) -> Dict[str, int]:
        """
        Find the Pattern_Match column index in each sheet.
        
        Returns:
            Dict mapping sheet names to Pattern_Match column indices
        """
        pattern_match_columns = {}
        
        for sheet_name, df in self.workbook_data.items():
            # Look for Pattern_Match column (case-insensitive)
            for i, col in enumerate(df.columns):
                if isinstance(col, str) and 'pattern_match' in col.lower():
                    pattern_match_columns[sheet_name] = i
                    break
                # Check for unnamed columns that might contain pattern_match
                elif 'Unnamed' in str(col):
                    # Check if the first few cells contain pattern_match
                    first_cells = df.iloc[:3, i].astype(str).str.lower()
                    if any('pattern_match' in cell for cell in first_cells):
                        pattern_match_columns[sheet_name] = i
                        break
        
        return pattern_match_columns
    
    def extract_pattern_matches(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract all non-empty Pattern_Match values from all sheets.
        
        Returns:
            Dictionary with sheet names as keys and lists of pattern match data as values
        """
        if not self.workbook_data:
            self.load_workbook()
        
        pattern_columns = self.find_pattern_match_columns()
        
        for sheet_name, df in self.workbook_data.items():
            if sheet_name not in pattern_columns:
                print(f"No Pattern_Match column found in sheet: {sheet_name}")
                continue
            
            col_index = pattern_columns[sheet_name]
            sheet_patterns = []
            
            # Extract pattern matches (skip header row)
            for idx, row in df.iterrows():
                if idx == 0:  # Skip header row
                    continue
                
                # Get the pattern match value
                pattern_value = row.iloc[col_index] if col_index < len(row) else None
                
                # Only include non-empty, non-NaN values
                if (pd.notna(pattern_value) and 
                    str(pattern_value).strip() != '' and 
                    str(pattern_value).lower() != 'pattern_match'):
                    
                    # Get other relevant row data for context
                    row_data = {
                        'row_number': idx + 1,  # Excel row number (1-indexed)
                        'pattern_match': str(pattern_value).strip(),
                        'test_name': row.iloc[0] if len(row) > 0 else '',
                        'pod_exec': row.iloc[1] if len(row) > 1 else '',
                        'command': row.iloc[2] if len(row) > 2 else '',
                        'expected_status': row.iloc[4] if len(row) > 4 else '',
                    }
                    sheet_patterns.append(row_data)
            
            if sheet_patterns:
                self.pattern_match_data[sheet_name] = sheet_patterns
        
        return self.pattern_match_data
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """
        Get summary statistics about the pattern matches.
        
        Returns:
            Dictionary containing summary statistics
        """
        if not self.pattern_match_data:
            self.extract_pattern_matches()
        
        # Count total patterns
        total_patterns = sum(len(patterns) for patterns in self.pattern_match_data.values())
        
        # Get unique pattern values
        all_patterns = []
        for patterns in self.pattern_match_data.values():
            all_patterns.extend([p['pattern_match'] for p in patterns])
        
        unique_patterns = list(set(all_patterns))
        
        # Pattern frequency
        pattern_frequency = {}
        for pattern in all_patterns:
            pattern_frequency[pattern] = pattern_frequency.get(pattern, 0) + 1
        
        return {
            'total_sheets': len(self.workbook_data),
            'sheets_with_patterns': len(self.pattern_match_data),
            'total_pattern_entries': total_patterns,
            'unique_patterns': unique_patterns,
            'unique_pattern_count': len(unique_patterns),
            'pattern_frequency': pattern_frequency,
            'sheets_with_pattern_data': list(self.pattern_match_data.keys())
        }
    
    def export_enhanced_data(self, enhanced_data: Dict[str, Any], output_file: str = None) -> None:
        """
        Export enhanced pattern match data (with conversions) to JSON file.
        
        Args:
            enhanced_data (Dict): Enhanced data from pattern conversion
            output_file (str): Output JSON file path. If None, uses default name.
        """
        if output_file is None:
            output_file = self.excel_file_path.stem + '_enhanced_pattern_matches.json'
        
        export_data = {
            'summary': self.get_summary_stats(),
            'enhanced_pattern_matches': enhanced_data['enhanced_patterns'],
            'conversion_statistics': enhanced_data['conversion_statistics']
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"Enhanced pattern match data exported to: {output_file}")
    
    def export_to_json(self, output_file: str = None) -> None:
        """
        Export pattern match data to JSON file.
        
        Args:
            output_file (str): Output JSON file path. If None, uses default name.
        """
        if not self.pattern_match_data:
            self.extract_pattern_matches()
        
        if output_file is None:
            output_file = self.excel_file_path.stem + '_pattern_matches.json'
        
        export_data = {
            'summary': self.get_summary_stats(),
            'pattern_matches': self.pattern_match_data
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"Pattern match data exported to: {output_file}")
    
    def print_summary(self) -> None:
        """Print a summary of the pattern match data."""
        stats = self.get_summary_stats()
        
        print("\n" + "="*60)
        print("PATTERN MATCH SUMMARY")
        print("="*60)
        print(f"Total sheets in workbook: {stats['total_sheets']}")
        print(f"Sheets with pattern matches: {stats['sheets_with_patterns']}")
        print(f"Total pattern match entries: {stats['total_pattern_entries']}")
        print(f"Unique pattern values: {stats['unique_pattern_count']}")
        
        if stats['unique_patterns']:
            print(f"\nUnique patterns found:")
            for i, pattern in enumerate(stats['unique_patterns'], 1):
                frequency = stats['pattern_frequency'][pattern]
                print(f"  {i}. '{pattern}' (appears {frequency} times)")
        
        print(f"\nSheets containing pattern data:")
        for sheet in stats['sheets_with_pattern_data']:
            count = len(self.pattern_match_data[sheet])
            print(f"  - {sheet}: {count} patterns")

def main():
    """Example usage of the PatternMatchParser with pattern conversion."""
    
    # Initialize parser
    parser = PatternMatchParser('Oracle_VzW_OCSLF_25.1.1xx_Auto_OTP_v1.3.xlsx')
    
    # Extract pattern matches
    pattern_data = parser.extract_pattern_matches()
    
    # Convert patterns to dictionaries
    from pattern_to_dict_converter import PatternToDictConverter, integrate_with_excel_parser
    
    enhanced_data = integrate_with_excel_parser(pattern_data)
    
    # Print summary
    parser.print_summary()
    
    # Print conversion statistics
    print("\n" + "="*60)
    print("PATTERN CONVERSION STATISTICS")
    print("="*60)
    conv_stats = enhanced_data['conversion_statistics']
    print(f"Total patterns processed: {conv_stats['total_processed']}")
    print(f"Successful conversions: {conv_stats['successful_conversions']}")
    print(f"Failed conversions: {conv_stats['failed_conversions']}")
    print(f"Conversion types: {conv_stats['conversion_types']}")
    
    # Export enhanced data to JSON
    parser.export_enhanced_data(enhanced_data)
    
    # Return the enhanced data
    return enhanced_data

