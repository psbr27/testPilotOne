"""
HTML Report Generator for Test Results
Provides functionality to generate interactive HTML reports for test results
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List

from .test_results_exporter import TestResultsExporter


class HTMLReportGenerator(TestResultsExporter):
    """Generate interactive HTML reports for test results"""

    def __init__(self, results_dir="test_results"):
        """Initialize with output directory"""
        super().__init__(results_dir)
        self.css_styles = self._get_css_styles()
        self.js_scripts = self._get_js_scripts()
        self.nf_css_styles = self._get_nf_css_styles()
        self.nf_js_scripts = self._get_nf_js_scripts()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from hosts.json"""
        config_paths = [
            "config/hosts.json",
            "hosts.json",
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "config",
                "hosts.json",
            ),
        ]

        for config_path in config_paths:
            try:
                if os.path.exists(config_path):
                    with open(config_path, "r") as f:
                        return json.load(f)
            except Exception as e:
                continue

        # Return default config if file not found
        return {
            "html_generator": {"use_nf_style": False},
            "system_under_test": {
                "nf_type": "Network Function",
                "version": "v1.0.0",
                "environment": "Test Environment",
                "deployment": "Test Deployment",
                "description": "Network Function Under Test",
            },
        }

    def _get_css_styles(self):
        """Return CSS styles for the HTML report"""
        return """
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: #fff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        h1 {
            color: #2c3e50;
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 10px;
            border-bottom: 2px solid #eee;
        }
        h2 {
            color: #34495e;
            margin-top: 30px;
            margin-bottom: 15px;
            padding-bottom: 5px;
            border-bottom: 1px solid #eee;
        }
        .summary {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            flex-wrap: wrap;
        }
        .summary-item {
            text-align: center;
            padding: 10px;
            flex: 1;
            min-width: 120px;
        }
        .summary-item h3 {
            margin: 0;
            font-size: 16px;
            color: #555;
        }
        .summary-item p {
            margin: 5px 0 0;
            font-size: 24px;
            font-weight: bold;
        }
        .total { color: #2c3e50; }
        .passed { color: #27ae60; }
        .failed { color: #e74c3c; }

        .sheet-tab {
            border: 1px solid #ddd;
            border-radius: 5px;
            margin-bottom: 10px;
            overflow: hidden;
        }
        .sheet-header {
            background-color: #f1f1f1;
            padding: 12px 15px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-weight: bold;
        }
        .sheet-summary {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        .chart-container {
            width: 120px;
            height: 120px;
            margin: 10px auto;
        }
        .sheet-stats {
            display: flex;
            gap: 20px;
            margin-bottom: 15px;
            padding: 10px;
            background-color: #f9f9f9;
            border-radius: 5px;
        }
        .sheet-header:hover {
            background-color: #e9e9e9;
        }
        .sheet-header .status-badge {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }
        .status-pass {
            background-color: #d4edda;
            color: #155724;
        }
        .status-fail {
            background-color: #f8d7da;
            color: #721c24;
        }
        .status-mixed {
            background-color: #fff3cd;
            color: #856404;
        }
        .sheet-content {
            display: none;
            padding: 0;
        }
        .test-table {
            width: 100%;
            border-collapse: collapse;
        }
        .test-table th, .test-table td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        .test-table th {
            background-color: #f8f9fa;
            font-weight: 600;
        }
        .test-table tr:hover {
            background-color: #f5f5f5;
        }
        .test-row {
            cursor: pointer;
        }
        .test-row.failed {
            background-color: rgba(231, 76, 60, 0.05);
        }
        .test-row.passed {
            background-color: rgba(39, 174, 96, 0.05);
        }
        .test-details {
            display: none;
            padding: 15px;
            background-color: #f8f9fa;
            border-top: 1px solid #ddd;
        }
        .details-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }
        .detail-item {
            margin-bottom: 10px;
        }
        .detail-item h4 {
            margin: 0 0 5px 0;
            font-size: 14px;
            color: #555;
        }
        .detail-item pre {
            margin: 0;
            padding: 10px;
            background-color: #f1f1f1;
            border-radius: 4px;
            overflow: auto;
            max-height: 200px;
            font-family: monospace;
            font-size: 13px;
            white-space: pre-wrap;
        }
        .filter-options {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .filter-btn {
            padding: 8px 15px;
            background-color: #f8f9fa;
            border: 1px solid #ddd;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        .filter-btn.active {
            background-color: #007bff;
            color: white;
            border-color: #007bff;
        }
        .timestamp {
            text-align: center;
            margin-top: 30px;
            color: #777;
            font-size: 12px;
        }
        .test-group {
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            margin-bottom: 10px;
            overflow: hidden;
        }
        .test-group-header {
            background-color: #f5f5f5;
            padding: 10px 15px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-weight: 600;
        }
        .test-group-header:hover {
            background-color: #e8e8e8;
        }
        .test-group-header.passed {
            border-left: 4px solid #27ae60;
        }
        .test-group-header.failed {
            border-left: 4px solid #e74c3c;
        }
        .test-group-name {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .test-group-name.passed {
            color: #27ae60;
        }
        .test-group-name.failed {
            color: #e74c3c;
        }
        .test-group-content {
            display: none;
            padding: 0;
        }
        .test-steps-count {
            color: #666;
            font-size: 14px;
            font-weight: normal;
        }
        """

    def _get_js_scripts(self):
        """Return JavaScript for the HTML report"""
        return """
        document.addEventListener('DOMContentLoaded', function() {
            // Create pie charts for overall summary and each sheet
            createOverallPieChart();
            createSheetPieCharts();

            // Toggle sheet content
            document.querySelectorAll('.sheet-header').forEach(header => {
                header.addEventListener('click', function() {
                    const content = this.nextElementSibling;
                    if (content.style.display === 'block') {
                        content.style.display = 'none';
                    } else {
                        content.style.display = 'block';
                    }
                });
            });

            // Toggle test details
            document.querySelectorAll('.test-row').forEach(row => {
                row.addEventListener('click', function() {
                    const detailsId = this.getAttribute('data-details');
                    const details = document.getElementById(detailsId);
                    if (details.style.display === 'block') {
                        details.style.display = 'none';
                    } else {
                        details.style.display = 'block';
                    }
                });
            });

            // Toggle test group content
            document.querySelectorAll('.test-group-header').forEach(header => {
                header.addEventListener('click', function() {
                    const content = this.nextElementSibling;
                    if (content.style.display === 'block') {
                        content.style.display = 'none';
                    } else {
                        content.style.display = 'block';
                    }
                });
            });

            // Filter buttons
            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    const filter = this.getAttribute('data-filter');

                    // Update active button
                    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                    this.classList.add('active');

                    // Filter rows
                    document.querySelectorAll('.test-row').forEach(row => {
                        if (filter === 'all') {
                            row.style.display = '';
                        } else if (filter === 'passed' && row.classList.contains('passed')) {
                            row.style.display = '';
                        } else if (filter === 'failed' && row.classList.contains('failed')) {
                            row.style.display = '';
                        } else {
                            row.style.display = 'none';
                        }
                    });
                });
            });
        });

        // Function to create the overall summary pie chart
        function createOverallPieChart() {
            const ctx = document.getElementById('overall-chart').getContext('2d');
            const passed = parseInt(document.getElementById('overall-passed').textContent);
            const failed = parseInt(document.getElementById('overall-failed').textContent);

            new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: ['Passed', 'Failed'],
                    datasets: [{
                        data: [passed, failed],
                        backgroundColor: ['#27ae60', '#e74c3c'],
                        borderColor: ['#2ecc71', '#c0392b'],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });

            // Create sheet comparison chart
            createSheetComparisonChart();
        }

        // Function to create pie charts for each sheet
        function createSheetPieCharts() {
            document.querySelectorAll('.sheet-chart').forEach(canvas => {
                const ctx = canvas.getContext('2d');
                const passed = parseInt(canvas.getAttribute('data-passed'));
                const failed = parseInt(canvas.getAttribute('data-failed'));

                new Chart(ctx, {
                    type: 'pie',
                    data: {
                        labels: ['Passed', 'Failed'],
                        datasets: [{
                            data: [passed, failed],
                            backgroundColor: ['#27ae60', '#e74c3c'],
                            borderColor: ['#2ecc71', '#c0392b'],
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                display: false
                            }
                        }
                    }
                });
            });
        }

        // Function to create sheet comparison chart
        function createSheetComparisonChart() {
            const ctx = document.getElementById('sheet-comparison-chart').getContext('2d');

            // Collect data from all sheet tabs
            const sheetNames = [];
            const passedCounts = [];
            const failedCounts = [];

            document.querySelectorAll('.sheet-chart').forEach(canvas => {
                // Get the sheet name from the closest sheet-tab
                const sheetTab = canvas.closest('.sheet-tab');
                const sheetName = sheetTab.querySelector('.sheet-header .sheet-summary span').textContent;

                const passed = parseInt(canvas.getAttribute('data-passed'));
                const failed = parseInt(canvas.getAttribute('data-failed'));

                sheetNames.push(sheetName);
                passedCounts.push(passed);
                failedCounts.push(failed);
            });

            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: sheetNames,
                    datasets: [
                        {
                            label: 'Passed',
                            data: passedCounts,
                            backgroundColor: '#27ae60',
                            borderColor: '#2ecc71',
                            borderWidth: 1
                        },
                        {
                            label: 'Failed',
                            data: failedCounts,
                            backgroundColor: '#e74c3c',
                            borderColor: '#c0392b',
                            borderWidth: 1
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            stacked: true,
                            title: {
                                display: true,
                                text: 'Sheet Name'
                            }
                        },
                        y: {
                            stacked: true,
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Number of Tests'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            position: 'top'
                        },
                        title: {
                            display: true,
                            text: 'Test Results by Sheet'
                        }
                    }
                }
            });
        }
        """

    def _get_nf_css_styles(self):
        """Return CSS styles for the NF-style HTML report"""
        return """
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: #fff;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        .report-header {
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #eee;
        }
        .report-title {
            font-size: 28px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 10px;
        }
        .timestamp {
            font-size: 14px;
            color: #777;
            margin-bottom: 20px;
        }
        .system-under-test {
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            border: 1px solid #dee2e6;
            border-left: 4px solid #007bff;
            height: 100%;
        }
        .system-under-test h3 {
            margin: 0 0 10px 0;
            color: #2c3e50;
            font-size: 18px;
        }
        .system-details {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            margin-top: 10px;
        }
        .system-detail {
            font-size: 14px;
        }
        .system-detail strong {
            color: #34495e;
        }
        .info-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }
        @media (max-width: 768px) {
            .info-container {
                grid-template-columns: 1fr;
            }
        }
        .overall-summary {
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            text-align: center;
            border: 1px solid #dee2e6;
            height: 100%;
        }
        .overall-summary > h3 {
            margin: 0 0 10px 0;
            color: #2c3e50;
            font-size: 18px;
        }
        .summary-stats {
            display: flex;
            justify-content: center;
            gap: 60px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .summary-item {
            text-align: center;
        }
        .summary-item h3 {
            margin: 0;
            font-size: 16px;
            color: #555;
        }
        .summary-item p {
            margin: 5px 0 0;
            font-size: 24px;
            font-weight: bold;
        }
        .passed { color: #27ae60; }
        .failed { color: #e74c3c; }
        .pass-rate { color: #2c3e50; }
        .main-chart {
            margin-bottom: 30px;
            height: 400px;
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            padding: 20px;
        }
        .sheet-results {
            margin-top: 0;
        }
        .sheet-results h2 {
            margin-bottom: 25px;
            color: #2c3e50;
            font-size: 22px;
            text-align: left;
        }
        .sheet-bars-container {
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            border: 1px solid #dee2e6;
        }
        .sheet-bar {
            margin-bottom: 15px;
            cursor: pointer;
            transition: all 0.2s ease;
            position: relative;
        }
        .sheet-bar:hover {
            transform: translateX(5px);
        }
        .sheet-bar:last-child {
            margin-bottom: 0;
        }
        .sheet-bar.active {
            transform: translateX(10px);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
        }
        .sheet-bar-content {
            position: relative;
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 15px 20px;
            color: #333;
            font-weight: 600;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
            min-height: 20px;
            border: 1px solid #ddd;
        }
        .sheet-bar.passed .sheet-bar-content {
            background-color: #d4edda;
            color: #155724;
            border-color: #c3e6cb;
        }
        .sheet-bar.failed .sheet-bar-content {
            background-color: #f8d7da;
            color: #721c24;
            border-color: #f5c6cb;
        }
        .sheet-bar.mixed .sheet-bar-content {
            background-color: #fff3cd;
            color: #856404;
            border-color: #ffeaa7;
        }
        .sheet-name {
            font-size: 16px;
            font-weight: bold;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .sheet-name::before {
            content: '▶';
            font-size: 12px;
            transition: transform 0.2s ease;
            display: inline-block;
        }
        .sheet-bar.active .sheet-name::before {
            transform: rotate(90deg);
        }
        .sheet-counts {
            display: flex;
            gap: 15px;
            font-size: 14px;
        }
        .count-item {
            background-color: rgba(255, 255, 255, 0.2);
            padding: 4px 12px;
            border-radius: 15px;
            font-weight: 600;
        }
        .sheet-content {
            display: none;
            padding: 20px;
            background-color: #f8f9fa;
            border: 1px solid #ddd;
            border-top: none;
            border-radius: 0 0 8px 8px;
            margin-top: -5px;
        }
        .test-details-section {
            margin-top: 30px;
        }
        .test-details-grid {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        .test-step .test-details-grid {
            padding: 15px;
            margin-bottom: 0;
        }
        .detail-box {
            background-color: #fff;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
        }
        .detail-box h4 {
            margin: 0 0 10px 0;
            font-size: 14px;
            color: #555;
            font-weight: 600;
        }
        .detail-box pre, .detail-box .detail-content {
            margin: 0;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 4px;
            font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
            font-size: 13px;
            white-space: pre-wrap;
            overflow: auto;
            max-height: 150px;
        }
        .validation-result {
            background-color: #d4edda !important;
            color: #155724;
            font-weight: bold;
        }
        .validation-result-fail {
            background-color: #f8d7da !important;
            color: #721c24;
            font-weight: bold;
        }
        .output-section {
            grid-column: span 2;
        }
        .output-section .detail-content {
            min-height: 200px;
            max-height: 400px;
        }
        .test-group {
            border: 1px solid #e0e0e0;
            border-radius: 5px;
            margin-bottom: 15px;
            overflow: hidden;
        }
        .test-group-header {
            background-color: #f5f5f5;
            padding: 15px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-weight: 600;
        }
        .test-group-header:hover {
            background-color: #e8e8e8;
        }
        .test-group-header.passed {
            border-left: 4px solid #27ae60;
        }
        .test-group-header.failed {
            border-left: 4px solid #e74c3c;
        }
        .test-group-content {
            display: block;
            padding: 20px;
            background-color: #fafafa;
        }
        .filter-controls {
            margin: 15px 0;
            padding: 10px;
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 5px;
        }
        .filter-btn {
            margin: 0 5px;
            padding: 8px 16px;
            border: 1px solid #007bff;
            background-color: #fff;
            color: #007bff;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        .filter-btn.active {
            background-color: #007bff;
            color: #fff;
        }
        .filter-btn:hover {
            background-color: #0056b3;
            color: #fff;
        }
        .test-step.hidden {
            display: none;
        }
        .test-step {
            margin-bottom: 15px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            overflow: hidden;
        }
        .test-step:last-child {
            margin-bottom: 0;
        }
        .step-header {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            margin: 0;
            padding: 12px 15px;
            font-size: 16px;
            font-weight: 600;
            color: #495057;
            border-bottom: 1px solid #dee2e6;
            cursor: pointer;
            user-select: none;
            transition: all 0.3s ease;
        }
        .step-header:hover {
            background: linear-gradient(135deg, #e9ecef 0%, #dee2e6 100%);
        }
        .step-header.passed {
            background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
            border-left: 4px solid #28a745;
            color: #155724;
        }
        .step-header.failed {
            background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
            border-left: 4px solid #dc3545;
            color: #721c24;
        }
        .step-header.passed:hover {
            background: linear-gradient(135deg, #c3e6cb 0%, #b5d5c0 100%);
        }
        .step-header.failed:hover {
            background: linear-gradient(135deg, #f5c6cb 0%, #f1b0b7 100%);
        }
        .step-content {
            display: none;
            padding: 0;
        }
        .step-content.active {
            display: block;
        }
        """

    def _get_nf_js_scripts(self):
        """Return JavaScript for the NF-style HTML report"""
        return """
        document.addEventListener('DOMContentLoaded', function() {
            // Create main bar chart
            createMainBarChart();

            // Toggle sheet content with auto-collapse
            document.querySelectorAll('.sheet-bar').forEach(bar => {
                bar.addEventListener('click', function() {
                    const sheetName = this.getAttribute('data-sheet');
                    const content = document.getElementById('sheet-content-' + sheetName);

                    if (content) {
                        // Check if this sheet is currently open
                        const isCurrentlyOpen = content.style.display === 'block';

                        // First, close all open sheets and remove active class
                        document.querySelectorAll('.sheet-content').forEach(sheetContent => {
                            sheetContent.style.display = 'none';
                        });
                        document.querySelectorAll('.sheet-bar').forEach(bar => {
                            bar.classList.remove('active');
                        });

                        // If the clicked sheet was closed, open it
                        // If it was open, it stays closed (toggle behavior)
                        if (!isCurrentlyOpen) {
                            content.style.display = 'block';
                            this.classList.add('active');

                            // Optionally scroll to the opened section
                            content.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                        }
                    }
                });
            });

            // Test step tab functionality with auto-collapse
            document.querySelectorAll('.step-header').forEach(header => {
                header.addEventListener('click', function() {
                    const stepId = this.getAttribute('data-step');
                    const stepContent = document.getElementById('step-content-' + stepId);

                    if (stepContent) {
                        // Check if this step is currently open
                        const isCurrentlyOpen = stepContent.classList.contains('active');

                        // First, close all open step contents in the same sheet
                        const sheetContent = this.closest('.sheet-content');
                        sheetContent.querySelectorAll('.step-content').forEach(content => {
                            content.classList.remove('active');
                        });

                        // If the clicked step was closed, open it
                        // If it was open, it stays closed (toggle behavior)
                        if (!isCurrentlyOpen) {
                            stepContent.classList.add('active');

                            // Optionally scroll to the opened section
                            stepContent.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                        }
                    }
                });
            });

            // Filter functionality for test steps
            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    const filter = this.getAttribute('data-filter');
                    const sheetName = this.getAttribute('data-sheet');

                    // Update active button
                    const sheetContent = document.getElementById('sheet-content-' + sheetName);
                    sheetContent.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                    this.classList.add('active');

                    // Filter test steps
                    const testSteps = sheetContent.querySelectorAll('.test-step');
                    testSteps.forEach(step => {
                        const stepStatus = step.getAttribute('data-status');

                        if (filter === 'all') {
                            step.classList.remove('hidden');
                        } else if (filter === 'pass' && stepStatus === 'pass') {
                            step.classList.remove('hidden');
                        } else if (filter === 'fail' && stepStatus === 'fail') {
                            step.classList.remove('hidden');
                        } else {
                            step.classList.add('hidden');
                        }
                    });

                    // Close all step contents when filtering
                    sheetContent.querySelectorAll('.step-content').forEach(content => {
                        content.classList.remove('active');
                    });
                });
            });
        });

        // Function to create the main bar chart
        function createMainBarChart() {
            const ctx = document.getElementById('main-chart').getContext('2d');

            // Collect data from sheet rows
            const sheetNames = [];
            const passedCounts = [];
            const failedCounts = [];

            document.querySelectorAll('.sheet-bar').forEach(bar => {
                const sheetName = bar.getAttribute('data-sheet');
                const passed = parseInt(bar.getAttribute('data-passed') || '0');
                const failed = parseInt(bar.getAttribute('data-failed') || '0');

                sheetNames.push(sheetName);
                passedCounts.push(passed);
                failedCounts.push(failed);
            });

            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: sheetNames,
                    datasets: [
                        {
                            label: 'Passed',
                            data: passedCounts,
                            backgroundColor: '#27ae60',
                            borderColor: '#2ecc71',
                            borderWidth: 1
                        },
                        {
                            label: 'Failed',
                            data: failedCounts,
                            backgroundColor: '#e74c3c',
                            borderColor: '#c0392b',
                            borderWidth: 1
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            title: {
                                display: true,
                                text: 'Sheet Name',
                                font: {
                                    size: 14,
                                    weight: 'bold'
                                }
                            }
                        },
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Number of Tests',
                                font: {
                                    size: 14,
                                    weight: 'bold'
                                }
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            position: 'top',
                            labels: {
                                font: {
                                    size: 12,
                                    weight: 'bold'
                                }
                            }
                        },
                        title: {
                            display: true,
                            text: 'Test Results by Sheet - Pass and Failed',
                            font: {
                                size: 16,
                                weight: 'bold'
                            }
                        }
                    }
                }
            });
        }
        """

    def _extract_test_name(self, test_name: str) -> str:
        """Extract base test name by removing _<digits> suffix"""
        import re

        return re.sub(r"_\d+$", "", test_name)

    def export_to_html(
        self, test_results: List[Any], filename: str = None
    ) -> str:
        """Export test results to an interactive HTML report"""
        if not filename:
            filename = self._generate_filename("html")

        # Group results by sheet
        results_by_sheet = {}
        for result in test_results:
            sheet = getattr(result, "sheet", "Unknown")
            if sheet not in results_by_sheet:
                results_by_sheet[sheet] = []
            results_by_sheet[sheet].append(result)

        # Calculate summary statistics
        total_tests = len(test_results)
        passed_tests = sum(
            1 for r in test_results if getattr(r, "passed", False)
        )
        failed_tests = total_tests - passed_tests
        pass_rate = (
            (passed_tests / total_tests * 100) if total_tests > 0 else 0
        )

        # Generate timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Generate HTML content
        html_content = f"""<!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Test Results Report</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
            {self.css_styles}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Test Results Report</h1>
                <p style="text-align: center; color: #777; margin-top: -20px; margin-bottom: 30px; font-size: 14px;">
                    Generated on {timestamp}
                </p>

                <div class="summary">
                    <div class="summary-item">
                        <h3>Total Tests</h3>
                        <p class="total">{total_tests}</p>
                    </div>
                    <div class="summary-item">
                        <h3>Passed</h3>
                        <p class="passed" id="overall-passed">{passed_tests}</p>
                    </div>
                    <div class="summary-item">
                        <h3>Failed</h3>
                        <p class="failed" id="overall-failed">{failed_tests}</p>
                    </div>
                    <div class="summary-item">
                        <h3>Pass Rate</h3>
                        <p>{pass_rate:.1f}%</p>
                    </div>
                </div>

                <div class="chart-container" style="width: 200px; height: 200px; margin: 0 auto;">
                    <canvas id="overall-chart"></canvas>
                </div>

                <h2>Tests by Sheet</h2>
                <div class="chart-container" style="width: 100%; height: 300px; margin: 20px auto;">
                    <canvas id="sheet-comparison-chart"></canvas>
                </div>

                <div class="filter-options">
                    <button class="filter-btn active" data-filter="all">All Tests</button>
                    <button class="filter-btn" data-filter="passed">Passed Only</button>
                    <button class="filter-btn" data-filter="failed">Failed Only</button>
                </div>

                <h2>Results by Sheet</h2>
        """

        # Add sheet tabs
        for sheet_name, sheet_results in results_by_sheet.items():
            sheet_passed = sum(
                1 for r in sheet_results if getattr(r, "passed", False)
            )
            sheet_failed = len(sheet_results) - sheet_passed
            sheet_pass_rate = (
                (sheet_passed / len(sheet_results) * 100)
                if len(sheet_results) > 0
                else 0
            )

            # Group tests by test name (without _<digits>)
            tests_by_name = {}
            for result in sheet_results:
                test_name = getattr(result, "test_name", "Unknown")
                base_test_name = self._extract_test_name(test_name)
                if base_test_name not in tests_by_name:
                    tests_by_name[base_test_name] = []
                tests_by_name[base_test_name].append(result)

            # Determine sheet status
            if sheet_failed == 0:
                status_class = "status-pass"
                status_text = "PASS"
            elif sheet_passed == 0:
                status_class = "status-fail"
                status_text = "FAIL"
            else:
                status_class = "status-mixed"
                status_text = f"MIXED ({sheet_passed}/{len(sheet_results)})"

            html_content += f"""
                <div class="sheet-tab">
                    <div class="sheet-header">
                        <div class="sheet-summary">
                            <span>{sheet_name}</span>
                            <span class="status-badge {status_class}">{status_text}</span>
                        </div>
                    </div>
                    <div class="sheet-content">
                        <div class="sheet-stats">
                            <div class="chart-container">
                                <canvas class="sheet-chart" data-passed="{sheet_passed}" data-failed="{sheet_failed}"></canvas>
                            </div>
                            <div>
                                <p><strong>Total Tests:</strong> {len(sheet_results)}</p>
                                <p><strong>Passed:</strong> <span class="passed">{sheet_passed}</span></p>
                                <p><strong>Failed:</strong> <span class="failed">{sheet_failed}</span></p>
                                <p><strong>Pass Rate:</strong> {sheet_pass_rate:.1f}%</p>
                            </div>
                        </div>
                        <div class="test-groups">
            """

            # Add test groups for this sheet
            for test_name, test_results in tests_by_name.items():
                # Determine if all tests in this group passed
                all_passed = all(
                    getattr(r, "passed", False) for r in test_results
                )
                group_status = "passed" if all_passed else "failed"
                status_text = "PASS" if all_passed else "FAIL"

                html_content += f"""
                            <div class="test-group">
                                <div class="test-group-header {group_status}">
                                    <div class="test-group-name {group_status}">
                                        <span>{test_name}</span>
                                        <span class="test-steps-count">({len(test_results)} steps)</span>
                                    </div>
                                    <span class="status-badge {'status-pass' if all_passed else 'status-fail'}">{status_text}</span>
                                </div>
                                <div class="test-group-content">
                                    <table class="test-table">
                                        <thead>
                                            <tr>
                                                <th>Step</th>
                                                <th>Method</th>
                                                <th>Host</th>
                                                <th>Status</th>
                                                <th>Duration (s)</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                """

                # Add test rows for this group
                for i, result in enumerate(test_results):
                    step_name = getattr(result, "test_name", "Unknown")
                    method = getattr(result, "method", "GET")
                    host = getattr(result, "host", "Unknown")
                    passed = getattr(result, "passed", False)
                    duration = getattr(result, "duration", 0.0)
                    status = "PASS" if passed else "FAIL"
                    row_class = "passed" if passed else "failed"
                    details_id = f"details-{sheet_name.replace(' ', '-')}-{test_name.replace(' ', '-')}-{i}"

                    html_content += f"""
                                            <tr class="test-row {row_class}" data-details="{details_id}">
                                                <td class="test-name">{step_name}</td>
                                                <td class="method">{method}</td>
                                                <td class="host">{host}</td>
                                                <td><span class="status-badge {'status-pass' if passed else 'status-fail'}">{status}</span></td>
                                                <td>{duration:.2f}s</td>
                                            </tr>
                    """

                    # Add collapsible details section for this test
                    command = getattr(result, "command", "")
                    error = getattr(result, "error", "")
                    output = getattr(result, "output", "")
                    fail_reason = getattr(result, "fail_reason", "")
                    expected_status = getattr(result, "expected_status", "N/A")
                    actual_status = getattr(result, "actual_status", "N/A")
                    pattern_match = getattr(result, "pattern_match", "")
                    pattern_found = getattr(result, "pattern_found", "")

                    html_content += f"""
                                            <tr>
                                                <td colspan="5" class="test-details" id="{details_id}">
                                                    <div class="details-grid">
                                                        <div class="detail-item">
                                                            <h4>Command</h4>
                                                            <pre>{command}</pre>
                                                        </div>
                    """

                    if error:
                        html_content += f"""
                                                        <div class="detail-item">
                                                            <h4>Error</h4>
                                                            <pre>{error}</pre>
                                                        </div>
                        """

                    if fail_reason:
                        html_content += f"""
                                                        <div class="detail-item">
                                                            <h4>Failure Reason</h4>
                                                            <pre>{fail_reason}</pre>
                                                        </div>
                        """

                    # Add detailed comparison information if available
                    details = getattr(result, "details", None)
                    if details and not result.passed:
                        # Convert details to JSON-serializable format
                        def make_json_serializable(obj):
                            """Convert DeepDiff objects to JSON-serializable format"""
                            if hasattr(obj, "__dict__"):
                                # For objects with __dict__, convert to dict
                                return {
                                    k: make_json_serializable(v)
                                    for k, v in obj.__dict__.items()
                                }
                            elif hasattr(obj, "__iter__") and not isinstance(
                                obj, (str, bytes)
                            ):
                                # For iterables (including SetOrdered), convert to list
                                try:
                                    return [
                                        make_json_serializable(item)
                                        for item in obj
                                    ]
                                except (TypeError, RuntimeError):
                                    # If iteration fails, convert to string
                                    return str(obj)
                            elif isinstance(obj, dict):
                                return {
                                    k: make_json_serializable(v)
                                    for k, v in obj.items()
                                }
                            else:
                                # For basic types, return as-is
                                try:
                                    json.dumps(
                                        obj
                                    )  # Test if it's JSON serializable
                                    return obj
                                except (TypeError, ValueError):
                                    return str(obj)

                        try:
                            serializable_details = make_json_serializable(
                                details
                            )
                            details_json = json.dumps(
                                serializable_details, indent=2
                            )
                        except Exception as e:
                            # Fallback to string representation if JSON serialization fails
                            details_json = f"Error serializing details: {str(e)}\n\nDetails (string representation):\n{str(details)}"

                        html_content += f"""
                                                        <div class="detail-item" style="grid-column: span 2;">
                                                            <h4>Detailed Comparison</h4>
                                                            <pre>{details_json}</pre>
                                                        </div>
                        """

                    html_content += f"""
                                                        <div class="detail-item">
                                                            <h4>Expected Status</h4>
                                                            <pre>{expected_status}</pre>
                                                        </div>
                                                        <div class="detail-item">
                                                            <h4>Actual Status</h4>
                                                            <pre>{actual_status}</pre>
                                                        </div>
                    """

                    if pattern_match:
                        html_content += f"""
                                                        <div class="detail-item">
                                                            <h4>Pattern Match</h4>
                                                            <pre>{pattern_match}</pre>
                                                        </div>
                        """

                    if pattern_found:
                        html_content += f"""
                                                        <div class="detail-item">
                                                            <h4>Pattern Found</h4>
                                                            <pre>{pattern_found}</pre>
                                                        </div>
                        """

                    if output:
                        html_content += f"""
                                                        <div class="detail-item" style="grid-column: span 2;">
                                                            <h4>Output</h4>
                                                            <pre>{output}</pre>
                                                        </div>
                        """

                    html_content += """
                                                    </div>
                                                </td>
                                            </tr>
                    """

                html_content += """
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                """

            html_content += """
                        </div>
                    </div>
                </div>
            """

        # Close HTML document
        html_content += f"""
            </div>
            <script>
            {self.js_scripts}
            </script>
        </body>
        </html>
        """

        # Write HTML to file
        with open(filename, "w") as f:
            f.write(html_content)

        return filename

    def export_to_nf_html(
        self,
        test_results: List[Any],
        filename: str = None,
        config: Dict[str, Any] = None,
        test_mode: str = "OTP",
    ) -> str:
        """Export test results to NF-style HTML report

        Args:
            test_results: List of test results
            filename: Output filename
            config: Configuration dictionary
            test_mode: Test mode - 'OTP', 'AUDIT', or 'CONFIG'
        """
        if not filename:
            filename = self._generate_filename("html")

        if not config:
            config = self._load_config()

        # Validate and normalize test mode
        test_mode = test_mode.upper() if test_mode else "OTP"
        if test_mode not in ["OTP", "AUDIT", "CONFIG"]:
            test_mode = "OTP"

        # Get system under test details
        system_info = config.get("system_under_test", {})

        # Group results by sheet
        results_by_sheet = {}
        for result in test_results:
            sheet = getattr(result, "sheet", "Unknown")
            if sheet not in results_by_sheet:
                results_by_sheet[sheet] = []
            results_by_sheet[sheet].append(result)

        # Calculate summary statistics
        total_tests = len(test_results)
        passed_tests = sum(
            1 for r in test_results if getattr(r, "passed", False)
        )
        failed_tests = total_tests - passed_tests
        pass_rate = (
            (passed_tests / total_tests * 100) if total_tests > 0 else 0
        )

        # Generate timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Get NF name from config for proper header
        nf_name = config.get("nf_name", "NF")
        if "AMF" in nf_name.upper():
            report_title = f"AMF {test_mode} Test Report"
        elif "SMF" in nf_name.upper():
            report_title = f"SMF {test_mode} Test Report"
        elif "NRF" in nf_name.upper():
            report_title = f"NRF {test_mode} Test Report"
        elif "SLF" in nf_name.upper():
            report_title = f"SLF {test_mode} Test Report"
        else:
            # Extract prefix from nf_name if available
            if "_" in nf_name:
                nf_prefix = nf_name.split("_")[0]
                report_title = f"{nf_prefix} {test_mode} Test Report"
            else:
                report_title = f"{nf_name} {test_mode} Test Report"

        # Generate HTML content
        html_content = f"""<!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{report_title}</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
            {self.nf_css_styles}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="report-header">
                    <div class="report-title">{report_title}</div>
                    <div class="timestamp">Timestamp: {timestamp}</div>
                </div>

                <div class="info-container">
                    <div class="system-under-test">
                        <h3>System Under Test</h3>
                        <div class="system-details">
                            <div class="system-detail"><strong>NF Type:</strong> {system_info.get('nf_type', 'Network Function')}</div>
                            <div class="system-detail"><strong>Version:</strong> {system_info.get('version', 'v1.0.0')}</div>
                            <div class="system-detail"><strong>Environment:</strong> {system_info.get('environment', 'Test Environment')}</div>
                            <div class="system-detail"><strong>Deployment:</strong> {system_info.get('deployment', 'Test Deployment')}</div>
                        </div>
                        <div style="margin-top: 10px;">
                            <div class="system-detail"><strong>Description:</strong> {system_info.get('description', 'Network Function Under Test')}</div>
                        </div>
                    </div>

                    <div class="overall-summary">
                        <h3>Overall Test Summary</h3>
                        <div class="summary-stats">
                            <div class="summary-item">
                                <h3>Pass</h3>
                                <p class="passed">{passed_tests}</p>
                            </div>
                            <div class="summary-item">
                                <h3>Fail</h3>
                                <p class="failed">{failed_tests}</p>
                            </div>
                            <div class="summary-item">
                                <h3>Pass Rate</h3>
                                <p class="pass-rate">{pass_rate:.1f}%</p>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="main-chart">
                    <canvas id="main-chart"></canvas>
                </div>

                                <div class="sheet-results">
                    <h2>Test Results by Sheet</h2>
                    <div class="sheet-bars-container">
        """

        # Add sheet rows and detailed content
        for sheet_name, sheet_results in results_by_sheet.items():
            sheet_passed = sum(
                1 for r in sheet_results if getattr(r, "passed", False)
            )
            sheet_failed = len(sheet_results) - sheet_passed

            # Determine sheet status and class
            if sheet_failed == 0:
                sheet_status = "PASSED"
                sheet_class = "passed"
            elif sheet_passed == 0:
                sheet_status = "FAILED"
                sheet_class = "failed"
            else:
                sheet_status = "MIXED"
                sheet_class = "mixed"

            safe_sheet_name = sheet_name.replace(" ", "-").replace("/", "-")

            html_content += f"""
                            <div class="sheet-bar {sheet_class}" data-sheet="{safe_sheet_name}" data-passed="{sheet_passed}" data-failed="{sheet_failed}">
                                <div class="sheet-bar-content">
                                    <span class="sheet-name">{sheet_name}</span>
                                    <div class="sheet-counts">
                                        <span class="count-item">Passed: {sheet_passed}</span>
                                        <span class="count-item">Failed: {sheet_failed}</span>
                                    </div>
                                </div>
                            </div>
            """

            # Add detailed content immediately after each sheet bar
            safe_sheet_name = sheet_name.replace(" ", "-").replace("/", "-")

            # Group tests by test name (without _<digits>)
            tests_by_name = {}
            for result in sheet_results:
                test_name = getattr(result, "test_name", "Unknown")
                base_test_name = self._extract_test_name(test_name)
                if base_test_name not in tests_by_name:
                    tests_by_name[base_test_name] = []
                tests_by_name[base_test_name].append(result)

            html_content += f"""
                            <div class="sheet-content" id="sheet-content-{safe_sheet_name}">
                                <h3>{sheet_name} - Detailed Results</h3>
                                <div class="filter-controls">
                                    <button class="filter-btn active" data-filter="all" data-sheet="{safe_sheet_name}">All Steps</button>
                                    <button class="filter-btn" data-filter="pass" data-sheet="{safe_sheet_name}">Passed Only</button>
                                    <button class="filter-btn" data-filter="fail" data-sheet="{safe_sheet_name}">Failed Only</button>
                                </div>
            """

            # Add test groups for this sheet
            for test_name, test_results in tests_by_name.items():
                # Determine if all tests in this group passed
                all_passed = all(
                    getattr(r, "passed", False) for r in test_results
                )
                group_status = "passed" if all_passed else "failed"
                status_text = "PASS" if all_passed else "FAIL"

                html_content += f"""
                                <div class="test-group">
                                    <div class="test-group-header {group_status}">
                                        <span>{test_name} ({len(test_results)} steps)</span>
                                        <span class="status-pass">{status_text}</span>
                                    </div>
                                    <div class="test-group-content">
                """

                # Show details for all test steps
                for step_index, result in enumerate(test_results, 1):
                    command = getattr(result, "command", "")
                    output = getattr(result, "output", "")
                    pattern_match = getattr(result, "pattern_match", "")
                    expected_status = getattr(result, "expected_status", "N/A")
                    actual_status = getattr(result, "actual_status", "N/A")
                    passed = getattr(result, "passed", False)
                    step_name = getattr(
                        result, "test_name", f"Step {step_index}"
                    )

                    # Get actual HTTP response from Response_Payload field instead of error output
                    response_payload = getattr(
                        result, "Response_Payload", None
                    ) or getattr(result, "response_payload", "")
                    actual_response = (
                        response_payload if response_payload else output
                    )

                    # Extract response headers if available - check multiple possible field names
                    response_headers = (
                        getattr(result, "response_headers", None)
                        or getattr(result, "Response_Headers", None)
                        or getattr(result, "headers", None)
                        or getattr(result, "Headers", None)
                        or {}
                    )

                    if isinstance(response_headers, dict) and response_headers:
                        headers_display = json.dumps(
                            response_headers, indent=2
                        )
                    elif response_headers and isinstance(
                        response_headers, str
                    ):
                        # Handle case where headers might be stored as string
                        headers_display = response_headers
                    else:
                        headers_display = "No headers available"

                    # Extract request payload if available
                    request_payload = getattr(result, "request_payload", None)
                    if request_payload:
                        if isinstance(request_payload, dict):
                            request_display = json.dumps(
                                request_payload, indent=2
                            )
                        else:
                            request_display = str(request_payload)
                    else:
                        request_display = None

                    validation_result_class = (
                        "validation-result"
                        if passed
                        else "validation-result-fail"
                    )

                    # Build HTML with conditional request payload section
                    step_status_class = (
                        "test-step-pass" if passed else "test-step-fail"
                    )
                    header_status_class = "passed" if passed else "failed"
                    status_text = "PASS" if passed else "FAIL"
                    safe_step_id = f"{safe_sheet_name}-step-{step_index}"

                    html_content += f"""
                                        <div class="test-step {step_status_class}" data-status="{'pass' if passed else 'fail'}">
                                            <h4 class="step-header {header_status_class}" data-step="{safe_step_id}">
                                                <span>Step {step_index}: {step_name}</span>
                                                <span class="status-indicator" style="float: right; font-weight: bold;">{status_text}</span>
                                            </h4>
                                            <div class="step-content" id="step-content-{safe_step_id}">
                                                <div class="test-details-grid">
                                                <div class="detail-box">
                                                    <h4>Command</h4>
                                                    <pre>{command}</pre>
                                                </div>
                                                <div class="detail-box">
                                                    <h4>Pattern to match</h4>
                                                    <pre>{pattern_match}</pre>
                                                </div>
                                                <div class="detail-box">
                                                    <h4>HTTP status Validation result</h4>
                                                    <div class="detail-content {validation_result_class}">{'PASS' if passed else 'FAIL'}</div>
                                                </div>
                                                <div class="detail-box">
                                                    <h4>Expected HTTP status</h4>
                                                    <pre>{expected_status}</pre>
                                                </div>
                                                <div class="detail-box">
                                                    <h4>HTTP status from server</h4>
                                                    <pre>{actual_status}</pre>
                                                </div>
                                                <div class="detail-box">
                                                    <h4>Headers</h4>
                                                    <div class="detail-content">{headers_display}</div>
                                                </div>
                    """

                    # Add request payload if available
                    if request_display:
                        html_content += f"""
                                                <div class="detail-box output-section" style="grid-column: span 3;">
                                                    <h4>Request Payload</h4>
                                                    <div class="detail-content">{request_display}</div>
                                                </div>
                        """

                    # Always add response section
                    html_content += f"""
                                                <div class="detail-box output-section" style="grid-column: span 3;">
                                                    <h4>HTTP Response From Server</h4>
                                                    <div class="detail-content">{actual_response}</div>
                                                </div>
                                                </div>
                                            </div>
                                        </div>
                    """

                html_content += """
                                    </div>
                                </div>
                """

            html_content += """
                            </div>
            """

        html_content += """
                    </div>
        """

        # Close HTML document
        html_content += f"""
                </div>
            </div>
            <script>
            {self.nf_js_scripts}
            </script>
        </body>
        </html>
        """

        # Write HTML to file
        with open(filename, "w") as f:
            f.write(html_content)

        return filename
