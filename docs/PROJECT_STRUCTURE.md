# TestPilot Project Structure

## Proposed Directory Organization

```
testPilotOne/
├── src/
│   └── testpilot/
│       ├── __init__.py
│       ├── core/                    # Core test execution functionality
│       │   ├── __init__.py
│       │   ├── test_pilot_core.py
│       │   ├── validation_engine.py
│       │   └── test_result.py
│       ├── mock/                    # Mock server components
│       │   ├── __init__.py
│       │   ├── enhanced_mock_server.py
│       │   ├── enhanced_mock_exporter.py
│       │   ├── mock_integration.py
│       │   └── generic_mock_server.py
│       ├── exporters/               # Export functionality
│       │   ├── __init__.py
│       │   ├── test_results_exporter.py
│       │   └── html_report_generator.py
│       ├── utils/                   # Utility functions
│       │   ├── __init__.py
│       │   ├── excel_parser.py
│       │   ├── response_parser.py
│       │   ├── pattern_match.py
│       │   ├── curl_builder.py
│       │   ├── ssh_connector.py
│       │   ├── parse_utils.py
│       │   └── logger.py
│       └── ui/                      # User interface components
│           ├── __init__.py
│           ├── blessed_dashboard.py
│           ├── rich_dashboard.py
│           └── console_table_fmt.py
├── tests/                           # Test files
│   ├── __init__.py
│   ├── test_enhanced_exporter.py
│   ├── test_mock_integration.py
│   └── test_validation_engine.py
├── examples/                        # Example data and scripts
│   ├── data/
│   │   ├── example_enhanced_data.json
│   │   ├── sample_test_results.json
│   │   └── enhanced_test_export.json
│   └── scripts/
│       ├── quick_mock_test.py
│       └── run_mock_tests.py
├── data/                           # Runtime data storage
│   ├── test_results/
│   ├── logs/
│   └── kubectl_logs/
├── scripts/                        # Build and utility scripts
│   ├── build_with_spec.sh
│   ├── clean_up.sh
│   └── update_build_info.py
├── docs/                           # Documentation
├── config/                         # Configuration files
├── requirements.txt
├── setup.py
├── README.md
└── .gitignore
```

## Benefits of This Structure

1. **Clear Separation**: Each module has a specific purpose
2. **Import Organization**: Easy to understand import paths
3. **Scalability**: Easy to add new components
4. **Testing**: Dedicated test directory
5. **Documentation**: Centralized docs
6. **Examples**: Clear examples for users

## Import Changes Required

After reorganization, imports will change from:
```python
from enhanced_mock_server import EnhancedMockServer
```

To:
```python
from testpilot.mock.enhanced_mock_server import EnhancedMockServer
```

## Migration Steps

1. Create directory structure
2. Move files to appropriate locations
3. Update all import statements
4. Update setup.py for package installation
5. Test all functionality
6. Update documentation
