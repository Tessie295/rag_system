.PHONY: help test test-verbose coverage clean

help:
	@echo "Available commands:"
	@echo "  make test           Run tests"
	@echo "  make test-verbose   Run tests with verbose output"
	@echo "  make coverage       Run tests with coverage report"
	@echo "  make clean          Remove test artifacts"

test:
	python -m pytest

test-verbose:
	python -m pytest -v

coverage:
	python -m pytest --cov=app --cov-report=term --cov-report=html

clean:
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -f .coverage