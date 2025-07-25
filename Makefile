.PHONY: format lint check install-dev test clean build build-spec help

# Default target
help:
	@echo "Available targets:"
	@echo "  format      - Run Black and isort to format code"
	@echo "  lint        - Run pre-commit checks on all files"
	@echo "  check       - Check code formatting without making changes"
	@echo "  install-dev - Install development dependencies and pre-commit hooks"
	@echo "  test        - Run tests (if test suite exists)"
	@echo "  build       - Build executable with PyInstaller"
	@echo "  build-spec  - Build executable with spec file for better module detection"
	@echo "  clean       - Clean up temporary files and caches"
	@echo "  help        - Show this help message"

# Install development dependencies
install-dev:
	python3 -m pip install -r requirements.txt
	python3 -m pip install pyinstaller
	pre-commit install
	@echo "✅ Development environment set up!"

# Format code with Black and isort (via pre-commit)
format:
	pre-commit run black --all-files || true
	pre-commit run isort --all-files || true
	@echo "✅ Code formatted!"

# Check formatting without making changes
check:
	pre-commit run black --all-files
	pre-commit run isort --all-files
	@echo "✅ Code formatting is correct!"

# Run all pre-commit hooks
lint:
	pre-commit run --all-files
	@echo "✅ Pre-commit checks passed!"

# Run tests
test:
	@echo "Running tests..."
	python3 -m pytest tests/
	@echo "✅ Tests completed!"

# Build executable with PyInstaller
build:
	@echo "Building executable with PyInstaller..."
	pyinstaller --clean --onedir --name testPilot test_pilot.py
	@echo "✅ Build completed! Executable is in dist/testPilot/"

# Build executable with spec file for better module detection
build-spec:
	@echo "Building with spec file for better module detection..."
	bash build_with_spec.sh
	@echo "✅ Build with spec completed!"

# Clean up temporary files
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .mypy_cache/
	rm -rf .pytest_cache/
	rm -rf dist/
	rm -rf build/
	rm -f *.spec
	@echo "✅ Cleaned up temporary files and build artifacts!"
	@echo "✅ Cleaned up temporary files!"
