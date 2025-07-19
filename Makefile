.PHONY: format lint check install-dev test clean help

# Default target
help:
	@echo "Available targets:"
	@echo "  format      - Run Black and isort to format code"
	@echo "  lint        - Run pre-commit checks on all files"
	@echo "  check       - Check code formatting without making changes"
	@echo "  install-dev - Install development dependencies and pre-commit hooks"
	@echo "  test        - Run tests (if test suite exists)"
	@echo "  clean       - Clean up temporary files and caches"
	@echo "  help        - Show this help message"

# Install development dependencies
install-dev:
	python3 -m pip install -r requirements.txt
	pre-commit install
	@echo "✅ Development environment set up!"

# Format code with Black and isort
format:
	python3 -m black --line-length=79 .
	python3 -m isort --profile=black --line-length=79 .
	@echo "✅ Code formatted!"

# Check formatting without making changes
check:
	python3 -m black --check --line-length=79 .
	python3 -m isort --check-only --profile=black --line-length=79 .
	@echo "✅ Code formatting is correct!"

# Run all pre-commit hooks
lint:
	pre-commit run --all-files
	@echo "✅ Pre-commit checks passed!"

# Run tests (placeholder for when tests are added)
test:
	@echo "⚠️  No test suite configured yet"
	# python3 -m pytest tests/

# Clean up temporary files
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .mypy_cache/
	rm -rf .pytest_cache/
	rm -rf dist/
	rm -rf build/
	@echo "✅ Cleaned up temporary files!"
