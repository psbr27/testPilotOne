#!/usr/bin/env python3
"""
TestPilot CLI Entry Point
========================

This module provides the main entry point for the testpilot command line interface.
It imports and executes the main function from the root test_pilot.py file.
"""

import os
import sys


def main():
    """Main entry point for the testpilot CLI command."""
    # Add the project root to Python path so we can import test_pilot
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.join(current_dir, "..", "..")
    project_root = os.path.abspath(project_root)

    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    try:
        # Import and run the main function from test_pilot.py
        from test_pilot import main as test_pilot_main

        test_pilot_main()
    except ImportError as e:
        print(f"Error importing test_pilot module: {e}")
        print(
            "Please make sure you're running from the TestPilot project directory."
        )
        sys.exit(1)
    except Exception as e:
        print(f"Error running TestPilot: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
