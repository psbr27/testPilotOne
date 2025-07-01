#!/usr/bin/env python3
"""
Setup script for TestPilot
Test automation framework compatible with Python 3.8+
"""

import sys

from setuptools import find_packages, setup

# Check Python version
if sys.version_info < (3, 8):
    sys.exit("TestPilot requires Python 3.8 or higher")

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [
        line.strip() for line in fh if line.strip() and not line.startswith("#")
    ]

setup(
    name="testpilot",
    version="1.0.0",
    author="TestPilot Team",
    description="Test automation framework for API testing with Excel-based test definitions",
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires=">=3.8",
    install_requires=requirements,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    entry_points={
        "console_scripts": [
            "testpilot=test_pilot:main",
        ],
    },
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
)
