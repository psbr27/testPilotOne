#!/usr/bin/env python3
"""
Complete usage example for parsing Excel patterns and converting them to dictionaries.
"""

import json
from pattern_match_parser import PatternMatchParser
from pattern_to_dict_converter import PatternToDictConverter, integrate_with_excel_parser

def main():
    """Main execution function."""
    
    print("🚀 Starting Excel Pattern Analysis...")
    
    # Step 1: Parse Excel file for pattern matches
    print("\n📊 Step 1: Parsing Excel file...")
    parser = PatternMatchParser('Oracle_VzW_OCSLF_25.1.1xx_Auto_OTP_v1.3.xlsx')
    raw_pattern_data = parser.extract_pattern_matches()
    
    # Step 2: Convert patterns to dictionaries
    print("\n🔄 Step 2: Converting patterns to dictionaries...")
    enhanced_data = integrate_with_excel_parser(raw_pattern_data)
    
    # Step 3: Display results
    print("\n📋 Step 3: Analysis Results")
    print("=" * 60)
    
    parser.print_summary()
    
    # Show conversion statistics
    conv_stats = enhanced_data['conversion_statistics']
    print(f"\n🔍 Conversion Analysis:")
    print(f"  • Total patterns processed: {conv_stats['total_processed']}")
    print(f"  • Successful conversions: {conv_stats['successful_conversions']}")
    print(f"  • Success rate: {conv_stats['successful_conversions']/conv_stats['total_processed']*100:.1f}%")
    
    print(f"\n📊 Conversion Types:")
    for conv_type, count in conv_stats['conversion_types'].items():
        print(f"  • {conv_type}: {count}")
    
    # Step 4: Show example conversions
    print("\n💡 Step 4: Example Pattern Conversions")
    print("=" * 60)
    
    example_count = 0
    for sheet_name, patterns in enhanced_data['enhanced_patterns'].items():
        if example_count >= 5:  # Show only first 5 examples
            break
            
        for pattern_entry in patterns:
            if example_count >= 5:
                break
                
            original = pattern_entry['pattern_match']
            converted = pattern_entry['converted_pattern']
            
            print(f"\n📝 Example {example_count + 1} (Sheet: {sheet_name}):")
            print(f"   Original: {original}")
            print(f"   Converted Type: {converted['pattern_type']}")
            print(f"   Converted Data: {converted['data']}")
            
            example_count += 1
    
    # Step 5: Export results
    print(f"\n💾 Step 5: Exporting Results...")
    parser.export_enhanced_data(enhanced_data)
    
    # Step 6: Demonstrate accessing specific data
    print(f"\n🎯 Step 6: Data Access Examples")
    print("=" * 60)
    
    demonstrate_data_access(enhanced_data)
    
    return enhanced_data

def demonstrate_data_access(enhanced_data):
    """Demonstrate how to access and use the converted data."""
    
    enhanced_patterns = enhanced_data['enhanced_patterns']
    
    # Example 1: Find all JSON-like patterns
    json_patterns = []
    for sheet_name, patterns in enhanced_patterns.items():
        for pattern_entry in patterns:
            converted = pattern_entry['converted_pattern']
            if converted['pattern_type'] in ['json_object', 'json_extracted']:
                json_patterns.append({
                    'sheet': sheet_name,
                    'test_name': pattern_entry['test_name'],
                    'data': converted['data']
                })
    
    print(f"🔍 Found {len(json_patterns)} JSON-like patterns:")
    for jp in json_patterns[:3]:  # Show first 3
        print(f"   • Sheet: {jp['sheet']}, Test: {jp['test_name']}")
        print(f"     Data: {jp['data']}")
    
    # Example 2: Find all header patterns
    header_patterns = []
    for sheet_name, patterns in enhanced_patterns.items():
        for pattern_entry in patterns:
            converted = pattern_entry['converted_pattern']
            if converted['pattern_type'] == 'http_header':
                header_patterns.append({
                    'sheet': sheet_name,
                    'header_type': converted['data'].get('header_type'),
                    'header_name': converted['data'].get('header_name'),
                    'header_value': converted['data'].get('header_value')
                })
    
    print(f"\n🌐 Found {len(header_patterns)} header patterns:")
    for hp in header_patterns[:3]:  # Show first 3
        print(f"   • Type: {hp['header_type']}, Name: {hp['header_name']}")
    
    # Example 3: Find all boolean patterns
    boolean_patterns = []
    for sheet_name, patterns in enhanced_patterns.items():
        for pattern_entry in patterns:
            converted = pattern_entry['converted_pattern']
            if 'enabled' in converted.get('data', {}) or converted['pattern_type'] == 'boolean':
                boolean_patterns.append({
                    'sheet': sheet_name,
                    'original': pattern_entry['pattern_match'],
                    'value': converted['data']
                })
    
    print(f"\n✅ Found {len(boolean_patterns)} boolean-related patterns:")
    for bp in boolean_patterns[:3]:  # Show first 3
        print(f"   • {bp['original']} → {bp['value']}")

def create_pattern_summary(enhanced_data):
    """Create a summary of all unique pattern types and their frequencies."""
    
    pattern_type_summary = {}
    enhanced_patterns = enhanced_data['enhanced_patterns']
    
    for sheet_name, patterns in enhanced_patterns.items():
        for pattern_entry in patterns:
            converted = pattern_entry['converted_pattern']
            pattern_type = converted['pattern_type']
            
            if pattern_type not in pattern_type_summary:
                pattern_type_summary[pattern_type] = {
                    'count': 0,
                    'examples': [],
                    'sheets': set()
                }
            
            pattern_type_summary[pattern_type]['count'] += 1
            pattern_type_summary[pattern_type]['sheets'].add(sheet_name)
            
            # Keep first 3 examples
            if len(pattern_type_summary[pattern_type]['examples']) < 3:
                pattern_type_summary[pattern_type]['examples'].append({
                    'original': pattern_entry['pattern_match'],
                    'converted': converted['data']
                })
    
    # Convert sets to lists for JSON serialization
    for pattern_type in pattern_type_summary:
        pattern_type_summary[pattern_type]['sheets'] = list(pattern_type_summary[pattern_type]['sheets'])
    
    return pattern_type_summary

if __name__ == "__main__":
    try:
        results = main()
        
        # Create additional summary
        summary = create_pattern_summary(results)
        
        # Save summary
        with open('pattern_type_summary.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n✅ Analysis complete! Check the generated JSON files for detailed results.")
        
    except Exception as e:
        print(f"❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()
