#!/usr/bin/env python3
"""
Log Analyzer for TestPilot
Analyzes structured failure logs and provides insights
"""

import argparse
import os
import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd


class TestPilotLogAnalyzer:
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        self.failures = []
        
    def parse_structured_log_line(self, line: str) -> Dict[str, Any]:
        """Parse a structured failure log line."""
        # Expected format: timestamp|ERROR|SHEET=value|ROW=value|...
        parts = line.strip().split('|')
        if len(parts) < 3:
            return {}
            
        timestamp = parts[0]
        level = parts[1] 
        
        failure_data = {'timestamp': timestamp, 'level': level}
        
        for part in parts[2:]:
            if '=' in part:
                key, value = part.split('=', 1)
                failure_data[key] = value
                
        return failure_data
    
    def load_failure_logs(self) -> None:
        """Load all failure logs from the logs directory."""
        if not os.path.exists(self.log_dir):
            print(f"Log directory '{self.log_dir}' not found.")
            return
            
        failure_files = [f for f in os.listdir(self.log_dir) if f.startswith('test_failures_')]
        
        if not failure_files:
            print("No failure log files found.")
            return
            
        for failure_file in failure_files:
            file_path = os.path.join(self.log_dir, failure_file)
            print(f"Loading failures from: {failure_file}")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        if line.strip():
                            failure_data = self.parse_structured_log_line(line)
                            if failure_data:
                                failure_data['file'] = failure_file
                                failure_data['line_num'] = line_num
                                self.failures.append(failure_data)
            except Exception as e:
                print(f"Error reading {failure_file}: {e}")
    
    def analyze_failure_patterns(self) -> Dict[str, Any]:
        """Analyze patterns in test failures."""
        if not self.failures:
            return {}
            
        analysis = {
            'total_failures': len(self.failures),
            'failure_by_sheet': Counter(f.get('SHEET', 'Unknown') for f in self.failures),
            'failure_by_host': Counter(f.get('HOST', 'Unknown') for f in self.failures),
            'failure_by_reason': Counter(f.get('REASON', 'Unknown')[:100] for f in self.failures),  # Truncate long reasons
            'status_code_issues': Counter(f.get('ACTUAL_STATUS', 'Unknown') for f in self.failures),
            'pattern_match_failures': sum(1 for f in self.failures if f.get('PATTERN_FOUND') == 'False'),
            'command_failures': Counter(f.get('COMMAND', 'Unknown')[:50] for f in self.failures),  # Truncate long commands
        }
        
        return analysis
    
    def generate_report(self) -> str:
        """Generate a comprehensive failure analysis report."""
        if not self.failures:
            return "No failure data available for analysis."
            
        analysis = self.analyze_failure_patterns()
        
        report = [
            "=" * 80,
            "TESTPILOT FAILURE ANALYSIS REPORT",
            "=" * 80,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Failures Analyzed: {analysis['total_failures']}",
            "",
            "TOP FAILURE PATTERNS:",
            "-" * 40,
        ]
        
        # Failure by sheet
        report.append("Failures by Sheet:")
        for sheet, count in analysis['failure_by_sheet'].most_common(10):
            report.append(f"  {sheet}: {count}")
        report.append("")
        
        # Failure by host
        report.append("Failures by Host:")
        for host, count in analysis['failure_by_host'].most_common(10):
            report.append(f"  {host}: {count}")
        report.append("")
        
        # Top failure reasons
        report.append("Top Failure Reasons:")
        for reason, count in analysis['failure_by_reason'].most_common(10):
            report.append(f"  {reason}...: {count}")
        report.append("")
        
        # Status code issues
        report.append("Status Code Issues:")
        for status, count in analysis['status_code_issues'].most_common(10):
            report.append(f"  Status {status}: {count}")
        report.append("")
        
        # Pattern matching failures
        pattern_failures = analysis['pattern_match_failures']
        report.append(f"Pattern Match Failures: {pattern_failures}")
        report.append("")
        
        # Most problematic commands
        report.append("Most Problematic Commands:")
        for cmd, count in analysis['command_failures'].most_common(10):
            report.append(f"  {cmd}...: {count}")
        
        return "\n".join(report)
    
    def export_to_excel(self, output_file: str = None) -> str:
        """Export failure data to Excel for detailed analysis."""
        if not self.failures:
            return "No failure data to export."
            
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"failure_analysis_{timestamp}.xlsx"
        
        try:
            df = pd.DataFrame(self.failures)
            df.to_excel(output_file, index=False)
            return f"Failure data exported to: {output_file}"
        except Exception as e:
            return f"Failed to export to Excel: {e}"

def main():
    parser = argparse.ArgumentParser(description="Analyze TestPilot failure logs")
    parser.add_argument("--log-dir", default="logs", help="Directory containing log files")
    parser.add_argument("--export", action="store_true", help="Export analysis to Excel")
    parser.add_argument("--output", help="Output file for Excel export")
    
    args = parser.parse_args()
    
    analyzer = TestPilotLogAnalyzer(args.log_dir)
    
    print("Loading failure logs...")
    analyzer.load_failure_logs()
    
    print("\nGenerating analysis report...")
    report = analyzer.generate_report()
    print(report)
    
    if args.export:
        print("\nExporting to Excel...")
        result = analyzer.export_to_excel(args.output)
        print(result)

if __name__ == "__main__":
    main()