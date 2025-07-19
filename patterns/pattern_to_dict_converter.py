import re
import json
from typing import Dict, Any, Union, List
from urllib.parse import unquote

class PatternToDictConverter:
    """
    Converts various pattern formats found in the Excel file to Python dictionaries.
    Handles JSON-like patterns, key-value pairs, headers, and other formats.
    """
    
    def __init__(self):
        self.conversion_stats = {
            'total_processed': 0,
            'successful_conversions': 0,
            'failed_conversions': 0,
            'conversion_types': {}
        }
    
    def convert_pattern(self, pattern: str) -> Dict[str, Any]:
        """
        Main method to convert any pattern to a dictionary.
        
        Args:
            pattern (str): The pattern string to convert
            
        Returns:
            Dict[str, Any]: Converted dictionary
        """
        self.conversion_stats['total_processed'] += 1
        
        if not pattern or not isinstance(pattern, str):
            return self._create_result('raw_value', pattern, 'empty_or_invalid')
        
        pattern = pattern.strip()
        
        try:
            # Try different conversion strategies
            result = None
            conversion_type = None
            
            # 1. Try JSON-like patterns
            if self._looks_like_json(pattern):
                result = self._convert_json_pattern(pattern)
                conversion_type = 'json_like'
            
            # 2. Try quoted key-value pairs
            elif self._looks_like_quoted_kv(pattern):
                result = self._convert_quoted_kv_pattern(pattern)
                conversion_type = 'quoted_key_value'
            
            # 3. Try HTTP header patterns
            elif self._looks_like_header(pattern):
                result = self._convert_header_pattern(pattern)
                conversion_type = 'http_header'
            
            # 4. Try colon-separated patterns
            elif ':' in pattern:
                result = self._convert_colon_pattern(pattern)
                conversion_type = 'colon_separated'
            
            # 5. Try boolean patterns
            elif self._looks_like_boolean(pattern):
                result = self._convert_boolean_pattern(pattern)
                conversion_type = 'boolean_value'
            
            # 6. Fallback to raw value
            else:
                result = self._convert_raw_pattern(pattern)
                conversion_type = 'raw_value'
            
            # Track conversion type
            self.conversion_stats['conversion_types'][conversion_type] = \
                self.conversion_stats['conversion_types'].get(conversion_type, 0) + 1
            
            self.conversion_stats['successful_conversions'] += 1
            return result
            
        except Exception as e:
            self.conversion_stats['failed_conversions'] += 1
            return self._create_result('error', pattern, 'conversion_failed', error=str(e))
    
    def _looks_like_json(self, pattern: str) -> bool:
        """Check if pattern looks like JSON."""
        return (pattern.startswith('{') and pattern.endswith('}')) or \
               (pattern.startswith('[') and pattern.endswith(']')) or \
               (pattern.count('"') >= 2 and ':' in pattern)
    
    def _looks_like_quoted_kv(self, pattern: str) -> bool:
        """Check if pattern looks like quoted key-value pairs."""
        return pattern.count('"') >= 2 and (':' in pattern or '=' in pattern)
    
    def _looks_like_header(self, pattern: str) -> bool:
        """Check if pattern looks like HTTP header."""
        header_patterns = ['3gpp-', 'server:', 'user-agent:', 'User-Agent:']
        return any(pattern.lower().startswith(hp.lower()) for hp in header_patterns)
    
    def _looks_like_boolean(self, pattern: str) -> bool:
        """Check if pattern represents a boolean value."""
        return pattern.lower() in ['true', 'false']
    
    def _convert_json_pattern(self, pattern: str) -> Dict[str, Any]:
        """Convert JSON-like patterns to dictionary."""
        try:
            # Handle incomplete JSON structures like {"title":,"status":,"details":,"cause":}
            if pattern.count(':,') > 0:
                # Fix incomplete JSON by adding null values
                fixed_pattern = re.sub(r':,', ':null,', pattern)
                fixed_pattern = re.sub(r':}', ':null}', fixed_pattern)
                pattern = fixed_pattern
            
            # Try direct JSON parsing
            try:
                parsed = json.loads(pattern)
                return self._create_result('json_object', parsed, 'direct_json_parse')
            except json.JSONDecodeError:
                pass
            
            # Extract key-value pairs from JSON-like strings
            kv_pairs = {}
            
            # Pattern: "key":"value" or "key":value
            json_kv_pattern = r'"([^"]+)"\s*:\s*(?:"([^"]*)"|([^,}\]]+))'
            matches = re.findall(json_kv_pattern, pattern)
            
            for match in matches:
                key = match[0]
                value = match[1] if match[1] else match[2]
                
                # Convert value types
                if value.lower() == 'true':
                    value = True
                elif value.lower() == 'false':
                    value = False
                elif value.lower() == 'null':
                    value = None
                elif value.isdigit():
                    value = int(value)
                elif self._is_float(value):
                    value = float(value)
                
                kv_pairs[key] = value
            
            return self._create_result('json_extracted', kv_pairs, 'json_key_value_extraction')
            
        except Exception as e:
            return self._create_result('partial_json', {'raw_content': pattern}, 'json_parse_failed', error=str(e))
    
    def _convert_quoted_kv_pattern(self, pattern: str) -> Dict[str, Any]:
        """Convert quoted key-value patterns."""
        kv_pairs = {}
        
        # Pattern: "key":"value"
        quoted_pattern = r'"([^"]+)"\s*:\s*"([^"]*)"'
        matches = re.findall(quoted_pattern, pattern)
        
        for key, value in matches:
            kv_pairs[key] = self._convert_value_type(value)
        
        # If no quoted pairs found, try other patterns
        if not kv_pairs:
            # Pattern: "key":value (unquoted value)
            mixed_pattern = r'"([^"]+)"\s*:\s*([^,\s]+)'
            matches = re.findall(mixed_pattern, pattern)
            
            for key, value in matches:
                kv_pairs[key] = self._convert_value_type(value)
        
        return self._create_result('quoted_kv', kv_pairs, 'quoted_key_value_parse')
    
    def _convert_header_pattern(self, pattern: str) -> Dict[str, Any]:
        """Convert HTTP header patterns."""
        result = {}
        
        # Handle different header formats
        if pattern.lower().startswith('server:'):
            # server: UDR-5a7bd676-ceeb-44bb-95e0-f6a55a328b03
            server_value = pattern[7:].strip()
            result = {
                'header_type': 'server',
                'server_value': server_value
            }
            
        elif pattern.lower().startswith('user-agent:'):
            # "User-Agent:"UDR-5a7bd676-ceeb-44bb-95e0-f6a55a328b03 udr001.oracle.com"
            ua_value = pattern[11:].strip().strip('"')
            result = {
                'header_type': 'user_agent',
                'user_agent': ua_value
            }
            
        elif '3gpp-sbi' in pattern.lower():
            # Handle 3GPP SBI headers
            if ':' in pattern:
                parts = pattern.split(':', 1)
                header_name = parts[0].strip()
                header_value = parts[1].strip() if len(parts) > 1 else None
                
                result = {
                    'header_type': '3gpp_sbi',
                    'header_name': header_name,
                    'header_value': header_value
                }
            else:
                result = {
                    'header_type': '3gpp_sbi',
                    'header_name': pattern,
                    'header_value': None
                }
        
        else:
            # Generic header parsing
            if ':' in pattern:
                parts = pattern.split(':', 1)
                result = {
                    'header_type': 'generic',
                    'header_name': parts[0].strip(),
                    'header_value': parts[1].strip() if len(parts) > 1 else None
                }
            else:
                result = {
                    'header_type': 'generic',
                    'header_name': pattern,
                    'header_value': None
                }
        
        return self._create_result('http_header', result, 'header_parse')
    
    def _convert_colon_pattern(self, pattern: str) -> Dict[str, Any]:
        """Convert colon-separated patterns."""
        parts = pattern.split(':', 1)
        key = parts[0].strip()
        value = parts[1].strip() if len(parts) > 1 else None
        
        # Clean up quotes
        key = key.strip('"\'')
        if value:
            value = value.strip('"\'')
            value = self._convert_value_type(value)
        
        result = {
            key: value
        }
        
        return self._create_result('colon_separated', result, 'colon_split')
    
    def _convert_boolean_pattern(self, pattern: str) -> Dict[str, Any]:
        """Convert boolean patterns."""
        bool_value = pattern.lower() == 'true'
        return self._create_result('boolean', {'value': bool_value}, 'boolean_conversion')
    
    def _convert_raw_pattern(self, pattern: str) -> Dict[str, Any]:
        """Convert raw patterns that don't match other formats."""
        return self._create_result('raw', {'raw_value': pattern}, 'raw_storage')
    
    def _convert_value_type(self, value: str) -> Any:
        """Convert string value to appropriate Python type."""
        if not isinstance(value, str):
            return value
            
        value = value.strip()
        
        if value.lower() == 'true':
            return True
        elif value.lower() == 'false':
            return False
        elif value.lower() == 'null':
            return None
        elif value.isdigit():
            return int(value)
        elif self._is_float(value):
            return float(value)
        else:
            return value
    
    def _is_float(self, value: str) -> bool:
        """Check if string represents a float."""
        try:
            float(value)
            return True
        except ValueError:
            return False
    
    def _create_result(self, pattern_type: str, data: Any, method: str, error: str = None) -> Dict[str, Any]:
        """Create standardized result dictionary."""
        result = {
            'pattern_type': pattern_type,
            'data': data,
            'conversion_method': method
        }
        
        if error:
            result['error'] = error
            
        return result
    
    def convert_all_patterns(self, patterns: List[str]) -> Dict[str, Any]:
        """
        Convert a list of patterns to dictionaries.
        
        Args:
            patterns (List[str]): List of pattern strings
            
        Returns:
            Dict containing converted patterns and statistics
        """
        converted_patterns = []
        
        for i, pattern in enumerate(patterns):
            converted = self.convert_pattern(pattern)
            converted['original_pattern'] = pattern
            converted['pattern_index'] = i
            converted_patterns.append(converted)
        
        return {
            'converted_patterns': converted_patterns,
            'statistics': self.conversion_stats,
            'summary': self._generate_summary()
        }
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate conversion summary."""
        total = self.conversion_stats['total_processed']
        successful = self.conversion_stats['successful_conversions']
        
        return {
            'total_patterns': total,
            'successful_conversions': successful,
            'success_rate': (successful / total * 100) if total > 0 else 0,
            'conversion_type_breakdown': self.conversion_stats['conversion_types']
        }

# Example usage and testing
def test_converter():
    """Test the converter with sample patterns."""
    
    # Sample patterns from your data
    test_patterns = [
        '"message":"is updated successfully"',
        '"nfStatus":"REGISTERED"',
        '{"title":,"status":,"details":,"cause":}',
        '"provLogsEnabled": true',
        '3gpp-Sbi-Oci',
        '"level": "DEBUG"',
        '"enabled":true',
        'server: UDR-5a7bd676-ceeb-44bb-95e0-f6a55a328b03',
        '3gpp-Sbi-Lci:Timestamp',
        '"User-Agent:"UDR-5a7bd676-ceeb-44bb-95e0-f6a55a328b03 udr001.oracle.com"',
        '"3gpp-sbi-correlation-info: msisdn-19195220001"'
    ]
    
    converter = PatternToDictConverter()
    results = converter.convert_all_patterns(test_patterns)
    
    print("=== PATTERN CONVERSION RESULTS ===")
    for result in results['converted_patterns']:
        print(f"\nOriginal: {result['original_pattern']}")
        print(f"Type: {result['pattern_type']}")
        print(f"Method: {result['conversion_method']}")
        print(f"Data: {result['data']}")
        if 'error' in result:
            print(f"Error: {result['error']}")
    
    print(f"\n=== CONVERSION STATISTICS ===")
    print(f"Total patterns: {results['summary']['total_patterns']}")
    print(f"Success rate: {results['summary']['success_rate']:.1f}%")
    print(f"Type breakdown: {results['summary']['conversion_type_breakdown']}")
    
    return results

def integrate_with_excel_parser(pattern_matches: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """
    Integrate pattern conversion with the Excel parser results.
    
    Args:
        pattern_matches: Output from PatternMatchParser.extract_pattern_matches()
        
    Returns:
        Enhanced data with converted patterns
    """
    converter = PatternToDictConverter()
    enhanced_data = {}
    
    for sheet_name, patterns in pattern_matches.items():
        enhanced_patterns = []
        
        for pattern_entry in patterns:
            # Convert the pattern_match field
            original_pattern = pattern_entry['pattern_match']
            converted = converter.convert_pattern(original_pattern)
            
            # Add converted data to the entry
            enhanced_entry = pattern_entry.copy()
            enhanced_entry['converted_pattern'] = converted
            enhanced_patterns.append(enhanced_entry)
        
        enhanced_data[sheet_name] = enhanced_patterns
    
    return {
        'enhanced_patterns': enhanced_data,
        'conversion_statistics': converter.conversion_stats
    }

