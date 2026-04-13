.PHONY: test test-integration test-all lint

# Tests unitarios (sin BD real)
test:
	pytest tests/ --ignore=tests/integration -v

# Tests de integración (requieren PostgreSQL + Redis corriendo vía Docker Compose)
test-integration:
	pytest tests/integration/ -v -m integration

# Toda la suite
test-all:
	pytest tests/ -v

# Lint con ruff
lint:
	ruff check app/ tests/
