# AI Task Tracker – Developer Makefile
# Usage: make <target>

.PHONY: help install dev test lint format migrate seed clean run

PYTHON := python
PIP := pip
APP := main:app

help:
	@echo "╔════════════════════════════════════════╗"
	@echo "║     AI Task Tracker – Make Commands     ║"
	@echo "╚════════════════════════════════════════╝"
	@echo ""
	@echo "  make install     Install all dependencies"
	@echo "  make dev         Start dev server (hot-reload)"
	@echo "  make run         Start production server"
	@echo "  make test        Run test suite"
	@echo "  make lint        Run linters (flake8 + mypy)"
	@echo "  make format      Auto-format code (black + isort)"
	@echo "  make migrate     Run pending Alembic migrations"
	@echo "  make migration   Generate a new migration (MSG='...')"
	@echo "  make seed        Seed the database with demo data"
	@echo "  make admin       Create/promote the admin user"
	@echo "  make clean       Remove cache and build artefacts"
	@echo ""

install:
	$(PIP) install -r requirements.txt

dev:
	uvicorn $(APP) --reload --host 0.0.0.0 --port 8000

run:
	uvicorn $(APP) --host 0.0.0.0 --port 8000 --workers 4

test:
	pytest

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

lint:
	flake8 app/ --max-line-length=100 --ignore=E501,W503
	mypy app/ --ignore-missing-imports

format:
	black app/ tests/ main.py --line-length=100
	isort app/ tests/ main.py --profile=black

migrate:
	alembic upgrade head

migration:
	alembic revision --autogenerate -m "$(MSG)"

seed:
	$(PYTHON) scripts/seed_data.py

admin:
	$(PYTHON) scripts/create_admin.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache htmlcov .coverage dist build
