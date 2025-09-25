.PHONY: setup install test run clean help

# Variables
PYTHON := python3
VENV := venv
VENV_BIN := $(VENV)/bin

# Default target
all: setup

# Setup virtual environment and install dependencies
setup:
	$(PYTHON) setup.py

# Install dependencies only
install:
	pip install -r requirements.txt

# Run tests
test:
	$(PYTHON) test_server.py

# Run the server
run:
	$(PYTHON) -m src.server

# Clean up generated files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf .pytest_cache/

# Clean everything including virtual environment
clean-all: clean
	rm -rf $(VENV)
	rm -rf data/

# Show help
help:
	@echo "Available commands:"
	@echo "  make setup     - Create virtual environment and install dependencies"
	@echo "  make install   - Install dependencies only"
	@echo "  make test      - Run tests"
	@echo "  make run       - Run the MCP server"
	@echo "  make clean     - Remove generated files"
	@echo "  make clean-all - Remove all generated files and virtual environment"
	@echo "  make help      - Show this help message"
